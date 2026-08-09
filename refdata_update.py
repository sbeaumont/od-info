"""
Command line tool to update the game reference data from the OpenDominion source repository.

    uv run python refdata_update.py                 # what would change, downloads nothing
    uv run python refdata_update.py --details       # ... including every changed number
    uv run python refdata_update.py update          # archive the current data and replace it
    uv run python refdata_update.py update --canonical --no-archive   # maintaining the app
    uv run python refdata_update.py archives        # the archived versions
    uv run python refdata_update.py restore         # put the newest archive back

Perks coming or going are the changes worth reading: they are game mechanics the tool may
have to implement. Perks you've reviewed and found irrelevant go into data/ignored-perks.yml.

An update normally lands in instance/ref-data, where it overrides the data that ships with
the application without getting in the way of a new release. Use --canonical to write the
copy in data/ref-data instead, which is what you want when maintaining the application
itself: that copy is under version control, so --no-archive fits with it.
"""

import argparse
import logging

from odinfo.config import REF_DATA_BASELINE_DIR, REF_DATA_OVERRIDE_DIR
from odinfo.exceptions import ODInfoException
from odinfo.services.refdata_service import RefDataService, PerkDiff, RefDataUpdate

logging.basicConfig(level=logging.INFO, format='%(message)s')


def report(update: RefDataUpdate, service: RefDataService, details: bool):
    print(f"\nReference data in {service.read_dir} against {update.branch}:")
    if not update.has_file_changes:
        print("  Up to date, nothing to download.")
    else:
        print(f"  {len(update.added)} new, {len(update.changed)} changed files.")
        for path in update.added:
            print(f"    new      {path}")
        for path in update.changed:
            print(f"    changed  {path}")
    for path in update.local_only:
        print(f"    ours     {path} (not in the source repository, left alone)")
    for path in update.unparsed:
        print(f"    unread   {path} (not checked for perks)")

    report_perks(update.perks, details)


def report_perks(perks: PerkDiff, details: bool):
    if perks.needs_attention:
        print("\nPerks that need a look, they may be mechanics to implement:")
        for perk in [p for p in perks.new_perks if not p.reviewed]:
            print(f"    NEW  {perk.name}, applied to:")
            for entity in perk.entities:
                print(f"           {entity}")
        for perk in [p for p in perks.retired_perks if not p.reviewed]:
            print(f"    GONE {perk.name}, was applied to:")
            for entity in perk.entities:
                print(f"           {entity}")
        print("\n  Not relevant for the tool? Add them to data/ignored-perks.yml with the reason.")

    for perk in [p for p in perks.new_perks if p.reviewed]:
        print(f"\nNew perk {perk.name}, reviewed as irrelevant: {perk.ignored_because}")
    for perk in [p for p in perks.retired_perks if p.reviewed]:
        print(f"\nPerk {perk.name} is gone, was reviewed as irrelevant: {perk.ignored_because}")

    if perks.changed_perks:
        print("\nKnown perks applied differently, the tool reads those from the files itself:")
        for change in perks.changed_perks:
            counts = [f"+{len(change.added)}" if change.added else '',
                      f"-{len(change.removed)}" if change.removed else '',
                      f"{len(change.changed_values)} value(s)" if change.changed_values else '']
            print(f"    {change.name}: {' '.join(part for part in counts if part)}")
            if details:
                for record in change.added:
                    print(f"         + {record.entity} = {record.value}")
                for record in change.removed:
                    print(f"         - {record.entity} (was {record.value})")
                for old, new in change.changed_values:
                    print(f"         ~ {new.entity}: {old.value} -> {new.value}")

    if perks.new_entities or perks.removed_entities:
        print(f"\nEntities with perks: {len(perks.new_entities)} new, {len(perks.removed_entities)} gone.")
        if details:
            for entity in perks.new_entities:
                print(f"    new   {entity}")
            for entity in perks.removed_entities:
                print(f"    gone  {entity}")

    if not (perks.new_perks or perks.retired_perks or perks.changed_perks):
        print("\nNo perk changes.")


def service_for(args) -> RefDataService:
    """The maintainer writes the copy that ships with the application, everyone else the
    override that sits with their own data."""
    if args.canonical:
        return RefDataService(write_dir=REF_DATA_BASELINE_DIR)
    return RefDataService(write_dir=REF_DATA_OVERRIDE_DIR)


def check(service: RefDataService, args):
    update = service.check()
    report(update, service, args.details)


def update(service: RefDataService, args):
    pending = service.check()
    report(pending, service, args.details)
    if not pending.has_file_changes:
        return

    if pending.perks.needs_attention and not args.yes:
        print(f"\n{len(pending.perks.unreviewed)} perk(s) need a look before the tool can use "
              f"this data properly.")
        if input("Update anyway? The current data is archived first. [y/N] ").strip().lower() != 'y':
            print("Nothing changed.")
            return

    archive = service.apply(pending, archive_first=not args.no_archive)
    print(f"\nWrote the new reference data to {service.write_dir}, in use after a restart.")
    if archive:
        print(f"The version it replaces is archived as {archive}")
        print("Undo with: uv run python refdata_update.py restore")


def archives(service: RefDataService, args):
    found = service.archives()
    if not found:
        print("No archived reference data yet, they are made whenever an update is applied.")
    for archive in found:
        print(archive)


def restore(service: RefDataService, args):
    available = service.archives()
    if not args.archive and not available:
        raise ODInfoException("No archived reference data to restore from.")

    archive = args.archive if args.archive else available[-1]
    replaced = service.restore(archive)
    print(f"Restored reference data from {archive}")
    print(f"What was there is archived as {replaced}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--details', action='store_true',
                        help="list every changed value instead of counts")
    parser.set_defaults(handler=check, yes=False, no_archive=False, canonical=False, archive=None)
    commands = parser.add_subparsers()

    commands.add_parser('check', help="report what a new version of the data would change"
                        ).set_defaults(handler=check)
    updating = commands.add_parser('update', help="archive the current data and download the new version")
    updating.set_defaults(handler=update)
    updating.add_argument('--yes', action='store_true', help="don't ask when perks need a look")
    updating.add_argument('--no-archive', action='store_true',
                          help="don't archive the current data, for when it's in version control")
    updating.add_argument('--canonical', action='store_true',
                          help=f"write {REF_DATA_BASELINE_DIR}, the copy that ships with the application")
    commands.add_parser('archives', help="list archived versions of the reference data"
                        ).set_defaults(handler=archives)
    restoring = commands.add_parser('restore', help="put an archived version back")
    restoring.set_defaults(handler=restore)
    restoring.add_argument('archive', nargs='?', help="archive to restore, newest by default")

    arguments = parser.parse_args()
    arguments.handler(service_for(arguments), arguments)