"""
Reference data service: keeps ref-data in sync with the OpenDominion source repository.

The files in ref-data are a mirror of app/data in the game's own repository. This service
downloads the current version of those files, archives what we have before replacing it,
and reports what changed in terms the tool cares about.

The changes that matter are perk changes. Game entities (spells, wonders, techs, races,
units, heroes) carry a `perks` block, and perk names are global: the same name means the
same effect wherever it shows up. That makes the perk, not the entity carrying it, the
thing to compare:

- A perk name that doesn't occur anywhere in the current ref-data is a new game mechanic,
  and the tool either has to implement it or consciously ignore it. Same for a perk name
  that disappears. Those need a human look.
- A known perk landing on another entity, leaving one, or changing its numbers is not a
  problem: the code reads that from the yaml files at runtime. Informational only.

Perks judged irrelevant for this tool (economy ones, mostly) are kept in ignored-perks.yml
so they don't get flagged again.
"""

import hashlib
import json
import logging
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from datetime import datetime

import requests
import yaml

from odinfo.config import (REF_DATA_DIR, REF_DATA_OVERRIDE_DIR, REF_DATA_ARCHIVE_DIR,
                           REF_DATA_STAMP_FILE, IGNORED_PERKS_FILE,
                           OD_SOURCE_BRANCH, OD_SOURCE_DATA_PATH,
                           OD_SOURCE_TREE_URL, OD_SOURCE_RAW_URL)
from odinfo.exceptions import ODInfoException

logger = logging.getLogger('od-info.refdata_service')

PERKS_KEY = 'perks'
NAME_KEY = 'name'
PARSEABLE_SUFFIXES = ('.yml', '.yaml', '.json')
ARCHIVE_PREFIX = 'ref-data-'
DOWNLOAD_TIMEOUT = 30


@dataclass(frozen=True)
class PerkRecord:
    """One perk applied to one entity."""
    entity: str  # What carries the perk, e.g. "races/orc.yml:units.Voyeur"
    perk: str
    value: str | int | float | bool | None


@dataclass
class Perk:
    """A game mechanic, seen through everywhere the reference data applies it."""
    name: str
    records: list[PerkRecord]
    ignored_because: str | None = None  # Filled in when it's on the reviewed-as-irrelevant list

    @property
    def reviewed(self) -> bool:
        """Whether this perk was looked at and judged irrelevant for the tool."""
        return self.ignored_because is not None

    @property
    def entities(self) -> list[str]:
        return sorted(record.entity for record in self.records)


@dataclass
class PerkChange:
    """A perk the tool already knows, applied differently than before."""
    name: str
    added: list[PerkRecord] = field(default_factory=list)
    removed: list[PerkRecord] = field(default_factory=list)
    changed_values: list[tuple[PerkRecord, PerkRecord]] = field(default_factory=list)


@dataclass
class PerkDiff:
    """Perk changes between the current reference data and the downloaded version."""
    new_perks: list[Perk] = field(default_factory=list)
    retired_perks: list[Perk] = field(default_factory=list)
    changed_perks: list[PerkChange] = field(default_factory=list)
    new_entities: list[str] = field(default_factory=list)
    removed_entities: list[str] = field(default_factory=list)

    @property
    def unreviewed(self) -> list[Perk]:
        """Perks that appeared or disappeared and haven't been judged irrelevant yet."""
        return [perk for perk in self.new_perks + self.retired_perks if not perk.reviewed]

    @property
    def needs_attention(self) -> bool:
        """Perks coming or going is what may need code changes, the rest is bookkeeping."""
        return bool(self.unreviewed)


@dataclass
class RefDataUpdate:
    """The result of checking the reference data against the source repository."""
    branch: str
    tree: str = ''  # Hash of the source repository tree the check ran against
    added: list[str] = field(default_factory=list)
    changed: list[str] = field(default_factory=list)
    local_only: list[str] = field(default_factory=list)
    unparsed: list[str] = field(default_factory=list)
    contents: dict[str, bytes] = field(default_factory=dict)
    perks: PerkDiff = field(default_factory=PerkDiff)

    @property
    def has_file_changes(self) -> bool:
        return bool(self.added or self.changed)


class RefDataService:
    """Downloads, archives and compares the ref-data mirror of the game's data files."""

    def __init__(self,
                 read_dir: str = REF_DATA_DIR,
                 write_dir: str = REF_DATA_OVERRIDE_DIR,
                 archive_dir: str = REF_DATA_ARCHIVE_DIR,
                 ignored_perks_file: str = IGNORED_PERKS_FILE,
                 branch: str = OD_SOURCE_BRANCH):
        """
        Create the reference data service.

        Args:
            read_dir: Which copy of the reference data the application currently reads.
            write_dir: Where the downloaded reference data is written. The override copy by
                default, or the baseline that ships with the application when maintaining it.
            archive_dir: Where copies of replaced reference data are kept.
            ignored_perks_file: List of perks reviewed and judged irrelevant for the tool.
            branch: Branch of the source repository to mirror.
        """
        self._read_dir = read_dir
        self._write_dir = write_dir
        self._archive_dir = archive_dir
        self._ignored_perks_file = ignored_perks_file
        self._branch = branch

    def check(self) -> RefDataUpdate:
        """Compares the current reference data with the source repository.

        Downloads the files that differ so their perks can be compared, but changes
        nothing on disk.
        """
        upstream, tree = self._upstream_index()
        local = self._local_index()
        update = RefDataUpdate(
            branch=self._branch,
            tree=tree,
            added=sorted(set(upstream) - set(local)),
            changed=sorted(path for path in set(upstream) & set(local) if upstream[path] != local[path]),
            local_only=sorted(set(local) - set(upstream)))
        logger.info("%d new, %d changed, %d local-only files",
                    len(update.added), len(update.changed), len(update.local_only))

        update.contents = self._download(update.added + update.changed)
        current_documents, unparsed_current = self._read_current()
        new_documents, unparsed_new = self._read_new(current_documents, update.contents)
        update.unparsed = sorted(set(unparsed_current) | set(unparsed_new))
        update.perks = diff_perks(current_documents, new_documents, self.ignored_perks())
        return update

    def apply(self, update: RefDataUpdate, archive_first: bool = True) -> str | None:
        """Archives the current reference data, then writes the downloaded files.

        Files that exist here but not in the source repository are left alone: nothing is
        ever deleted, so a mirror that runs ahead of the game's own repo stays usable.

        Returns the archive that was made, to restore from when things go wrong. Archiving
        can be skipped when the reference data is under version control anyway.
        """
        if not update.has_file_changes:
            raise ODInfoException("Nothing to apply: reference data is already up to date.")

        archive = self.archive_current() if archive_first else None
        self._prepare_write_dir()
        for path in update.added + update.changed:
            target = os.path.join(self._write_dir, *path.split('/'))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'wb') as f:
                f.write(update.contents[path])
        self._write_stamp(update)
        logger.info("Wrote %d reference data files to %s",
                    len(update.added) + len(update.changed), self._write_dir)
        return archive

    def archive_current(self) -> str:
        """Zips the reference data currently in use into the archive directory.

        The stamp saying when this copy was synced goes along, so that restoring an archive
        also restores its place in the baseline versus override pecking order.
        """
        os.makedirs(self._archive_dir, exist_ok=True)
        moment = datetime.now().strftime('%Y%m%d-%H%M%S')
        archive = os.path.join(self._archive_dir, f'{ARCHIVE_PREFIX}{moment}.zip')
        paths = list(self._local_index())
        if os.path.exists(os.path.join(self._read_dir, REF_DATA_STAMP_FILE)):
            paths.append(REF_DATA_STAMP_FILE)
        with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as zipped:
            for path in paths:
                zipped.write(os.path.join(self._read_dir, *path.split('/')), path)
        logger.info("Archived current reference data to %s", archive)
        return archive

    def archives(self) -> list[str]:
        """Archived reference data versions, newest last."""
        if not os.path.exists(self._archive_dir):
            return []
        return sorted(os.path.join(self._archive_dir, name)
                      for name in os.listdir(self._archive_dir)
                      if name.startswith(ARCHIVE_PREFIX) and name.endswith('.zip'))

    def restore(self, archive: str) -> str:
        """Puts an archived version back, after archiving what is there now.

        Returns the archive of what was replaced, so a restore can be undone as well.
        """
        if not os.path.exists(archive):
            raise ODInfoException(f"No such reference data archive: {archive}")

        replaced = self.archive_current()
        self._prepare_write_dir()
        shutil.rmtree(self._write_dir)
        os.makedirs(self._write_dir)
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(self._write_dir)
        logger.info("Restored reference data from %s", archive)
        return replaced

    def perks(self) -> list[Perk]:
        """Every perk in the reference data currently in use, with where it is applied."""
        documents, _ = self._read_current()
        return sorted(_perks_by_name(_all_records(documents), self.ignored_perks()).values(),
                      key=lambda perk: perk.name)

    def ignored_perks(self) -> dict[str, str]:
        """Perks reviewed and judged irrelevant for the tool, mapped to the reason why."""
        with open(self._ignored_perks_file) as f:
            reviewed = yaml.safe_load(f)
        return reviewed if reviewed else dict()

    @property
    def read_dir(self) -> str:
        return self._read_dir

    @property
    def write_dir(self) -> str:
        return self._write_dir

    def _upstream_index(self) -> tuple[dict[str, str], str]:
        """The data files in the source repository by git blob hash, and the tree they're in."""
        url = OD_SOURCE_TREE_URL.format(ref=self._branch)
        logger.info("Reading source repository tree %s", url)
        response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
        response.raise_for_status()
        tree = response.json()
        if tree['truncated']:
            raise ODInfoException(f"Source repository tree from {url} was truncated by GitHub, "
                                  f"so we can't tell which data files changed.")

        prefix = f'{OD_SOURCE_DATA_PATH}/'
        index = {entry['path'][len(prefix):]: entry['sha'] for entry in tree['tree']
                 if entry['type'] == 'blob' and entry['path'].startswith(prefix)}
        if not index:
            raise ODInfoException(f"No data files found under {prefix} in branch {self._branch}.")
        return index, tree['sha']

    def _write_stamp(self, update: RefDataUpdate):
        """Records when this copy was synced, which is what decides whether it is the copy
        the application reads. See config.refdata_read_path."""
        stamp = {'synced_at': datetime.now().isoformat(timespec='seconds'),
                 'branch': update.branch,
                 'tree': update.tree}
        with open(os.path.join(self._write_dir, REF_DATA_STAMP_FILE), 'w') as f:
            json.dump(stamp, f, indent=2)

    def _local_index(self) -> dict[str, str]:
        """Maps the reference data files in use to their git blob hash.

        Dot files are skipped: those are the operating system's business (.DS_Store), not
        the game's, and they only make the comparison noisy.
        """
        index = {}
        for root, dirs, files in os.walk(self._read_dir):
            dirs[:] = [d for d in dirs if not d.startswith('.')]
            for filename in files:
                if filename.startswith('.'):
                    continue
                full_path = os.path.join(root, filename)
                path = os.path.relpath(full_path, self._read_dir).replace(os.sep, '/')
                with open(full_path, 'rb') as f:
                    index[path] = _blob_hash(f.read())
        return index

    def _download(self, paths: list[str]) -> dict[str, bytes]:
        contents = {}
        for path in paths:
            url = OD_SOURCE_RAW_URL.format(ref=self._branch, path=f'{OD_SOURCE_DATA_PATH}/{path}')
            logger.debug("Downloading %s", url)
            response = requests.get(url, timeout=DOWNLOAD_TIMEOUT)
            response.raise_for_status()
            contents[path] = response.content
        logger.info("Downloaded %d files", len(contents))
        return contents

    def _read_current(self) -> tuple[dict, list[str]]:
        """Parses the reference data in use. Files we can't read for perks are reported."""
        documents = {}
        unparsed = []
        for path in self._local_index():
            if not path.endswith(PARSEABLE_SUFFIXES):
                unparsed.append(path)
                continue
            with open(os.path.join(self._read_dir, *path.split('/')), 'rb') as f:
                documents[path] = load_document(path, f.read())
        return documents, unparsed

    def _read_new(self, current_documents: dict, contents: dict[str, bytes]) -> tuple[dict, list[str]]:
        """The new situation is the current documents with the downloaded ones on top."""
        documents = dict(current_documents)
        unparsed = []
        for path, content in contents.items():
            if path.endswith(PARSEABLE_SUFFIXES):
                documents[path] = load_document(path, content)
            else:
                unparsed.append(path)
        return documents, unparsed

    def _prepare_write_dir(self):
        """In a pyinstaller build the first update starts from the bundled reference data,
        so that files we keep ourselves (config.json) end up in the writable copy too."""
        if not os.path.exists(self._write_dir):
            logger.info("Seeding writable reference data at %s from %s", self._write_dir, self._read_dir)
            shutil.copytree(self._read_dir, self._write_dir)


def load_document(path: str, content: bytes):
    """Parses one reference data file."""
    if path.endswith(('.yml', '.yaml')):
        return yaml.safe_load(content)
    elif path.endswith('.json'):
        return json.loads(content)
    else:
        raise ODInfoException(f"Don't know how to read reference data file {path}.")


def extract_perks(path: str, document) -> list[PerkRecord]:
    """All perks in one reference data document, with where they sit in it."""
    records = []
    _walk(document, [], records, path)
    return records


def diff_perks(current_documents: dict, new_documents: dict, ignored_perks: dict[str, str]) -> PerkDiff:
    """Compares the perks in two complete sets of {path: parsed document}."""
    old_records = _all_records(current_documents)
    new_records = _all_records(new_documents)
    old_perks = _perks_by_name(old_records, ignored_perks)
    new_perks = _perks_by_name(new_records, ignored_perks)

    diff = PerkDiff()
    diff.new_perks = [new_perks[name] for name in sorted(set(new_perks) - set(old_perks))]
    diff.retired_perks = [old_perks[name] for name in sorted(set(old_perks) - set(new_perks))]
    for name in sorted(set(old_perks) & set(new_perks)):
        change = _compare_perk(old_perks[name], new_perks[name])
        if change:
            diff.changed_perks.append(change)

    old_entities = {record.entity for record in old_records}
    new_entities = {record.entity for record in new_records}
    diff.new_entities = sorted(new_entities - old_entities)
    diff.removed_entities = sorted(old_entities - new_entities)
    return diff


def _blob_hash(content: bytes) -> str:
    """The hash git uses for a file, so we can compare with the source repository tree."""
    return hashlib.sha1(b'blob %d\0' % len(content) + content).hexdigest()


def _all_records(documents: dict) -> list[PerkRecord]:
    records = []
    for path, document in documents.items():
        records.extend(extract_perks(path, document))
    return records


def _perks_by_name(records: list[PerkRecord], ignored_perks: dict[str, str]) -> dict[str, Perk]:
    """Turns the individual applications into the perks they belong to."""
    perks = {}
    for record in records:
        if record.perk not in perks:
            perks[record.perk] = Perk(record.perk, [], ignored_perks.get(record.perk))
        perks[record.perk].records.append(record)
    return perks


def _compare_perk(old: Perk, new: Perk) -> PerkChange | None:
    """How a perk that exists in both versions moved around. None when it didn't."""
    old_records = {record.entity: record for record in old.records}
    new_records = {record.entity: record for record in new.records}
    change = PerkChange(
        name=new.name,
        added=[new_records[entity] for entity in sorted(set(new_records) - set(old_records))],
        removed=[old_records[entity] for entity in sorted(set(old_records) - set(new_records))],
        changed_values=[(old_records[entity], new_records[entity])
                        for entity in sorted(set(old_records) & set(new_records))
                        if old_records[entity].value != new_records[entity].value])
    if change.added or change.removed or change.changed_values:
        return change
    return None


def _walk(node, labels: list[str], records: list[PerkRecord], file_path: str):
    if isinstance(node, dict):
        perks = node.get(PERKS_KEY)
        if isinstance(perks, dict):
            entity = f"{file_path}:{'.'.join(labels)}" if labels else file_path
            for perk, value in perks.items():
                records.append(PerkRecord(entity, perk, _comparable(value)))
        for key, value in node.items():
            if key != PERKS_KEY:
                _walk(value, labels + [str(key)], records, file_path)
    elif isinstance(node, list):
        for index, item in enumerate(node):
            _walk(item, labels + [_list_label(item, index)], records, file_path)


def _list_label(item, index: int) -> str:
    """Units and the like read better by name than by their position in the list."""
    if isinstance(item, dict) and NAME_KEY in item:
        return str(item[NAME_KEY])
    return str(index)


def _comparable(value):
    """Perk values are scalars, but this keeps anything else comparable and hashable too."""
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return json.dumps(value, sort_keys=True)