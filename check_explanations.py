"""
Checks that the explanation pages still describe the code they explain.

    uv run python check_explanations.py            # are the pages still current?
    uv run python check_explanations.py --stamp    # they are now, record that

An explanation page carries its own stamp: the date somebody last read it against the
code, and a fingerprint per file it depends on. The page itself says which files those
are, so a page decides what would make it go stale. This script recomputes the
fingerprints and reports what moved since. The pre-push hook in .githooks runs it, so a
change to the code an explanation covers stops the push until the page has been looked at.

Re-stamping is a claim that you have read the page, not a formality. Name one or more
pages to limit the run to those:

    uv run python check_explanations.py --stamp odinfoweb/templates/philosophy.html
"""

import argparse
import glob
import hashlib
import re
import sys
from datetime import date

TEMPLATE_GLOB = 'odinfoweb/templates/*.html'

REVIEWED_PATTERN = re.compile(r"\{%\s*set\s+reviewed_on\s*=\s*'(?P<date>[^']*)'\s*%\}")
STAMP_PATTERN = re.compile(r"\{#-\s*doc-sources\n(?P<body>.*?)\n-#\}", re.DOTALL)


def fingerprint(path: str) -> str:
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()[:16]


def read(path: str) -> str:
    with open(path, encoding='utf-8') as f:
        return f.read()


def explanation_pages() -> list[str]:
    """The templates that carry a doc-sources block, so claim to explain something."""
    return sorted(path for path in glob.glob(TEMPLATE_GLOB) if STAMP_PATTERN.search(read(path)))


def stamped_sources(page: str) -> dict[str, str]:
    body = STAMP_PATTERN.search(read(page)).group('body')
    sources = dict()
    for line in body.strip().splitlines():
        path, _, digest = line.strip().partition(' ')
        sources[path] = digest.strip()
    return sources


def reviewed_on(page: str) -> str:
    match = REVIEWED_PATTERN.search(read(page))
    if not match:
        raise SystemExit(f"{page} has no reviewed_on date to show its readers.")
    return match.group('date')


def outdated(page: str) -> list[str]:
    """The files this page depends on that changed since it was last read."""
    return [path for path, digest in stamped_sources(page).items() if digest != fingerprint(path)]


def write_stamp(page: str) -> None:
    text = read(page)
    body = '\n'.join(f"{path} {fingerprint(path)}" for path in sorted(stamped_sources(page)))
    text = STAMP_PATTERN.sub(lambda _: f"{{#- doc-sources\n{body}\n-#}}", text)
    text = REVIEWED_PATTERN.sub(lambda _: f"{{% set reviewed_on = '{date.today():%Y-%m-%d}' %}}", text)
    with open(page, 'w', encoding='utf-8') as f:
        f.write(text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('pages', nargs='*',
                        help="the pages to act on, all explanation pages by default")
    parser.add_argument('--stamp', action='store_true',
                        help="record that the pages have been read against the code as it is now")
    args = parser.parse_args()

    pages = args.pages or explanation_pages()
    if not pages:
        raise SystemExit(f"No page under {TEMPLATE_GLOB} carries a doc-sources block.")

    if args.stamp:
        for page in pages:
            write_stamp(page)
            print(f"{page} stamped as read on {reviewed_on(page)}.")
        return 0

    stale = {page: outdated(page) for page in pages}
    stale = {page: changed for page, changed in stale.items() if changed}
    if not stale:
        for page in pages:
            print(f"{page} was read against the code it explains on {reviewed_on(page)}.")
        return 0

    for page, changed in stale.items():
        print(f"{page} was last read on {reviewed_on(page)}. These have changed since:")
        for path in changed:
            print(f"    {path}")
    print("\nRead those pages against the changes. Then record it with:")
    print(f"    uv run python check_explanations.py --stamp {' '.join(stale)}")
    return 1


if __name__ == '__main__':
    sys.exit(main())