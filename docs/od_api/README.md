# An OpenDominion API, seen from a tool

These documents describe what OD Info takes from opendominion.net today, and what a REST
API would have to offer for a tool like it to stop scraping HTML. They are written as
input for the game's own API design, not as a demand: OD Info is one consumer, and the
shape that suits it is only evidence, not a requirement.

The game now has an API: https://www.opendominion.net/api-docs.
[api-migration.md](api-migration.md) maps each scraper in OD Info to the API call that
replaces it.

| Document | What it holds |
| --- | --- |
| [api-migration.md](api-migration.md) | Each scraper and the API call that replaces it |
| [responses/](responses/) | One real response of each API endpoint. `uv run python -m docs.od_api.capture_api` makes them again |
| [inventory.md](inventory.md) | Every field OD Info pulls in today, where it comes from, and what it costs |
| [api-spec.md](api-spec.md) | The proposed API: resources, conventions, and the rules that keep it cheap |
| [gaps.md](gaps.md) | What the site does not expose at all today, ranked by how much it distorts our estimates |

## The short version

OD Info logs in as the player, scrapes seven kinds of page, and reassembles them into a
local SQLite database. An hourly run costs `5 + N + R` HTTP page loads, where N is the
number of dominions with a fresh scan and R is the realm size — up to 270 full HTML pages
for a round of 264 dominions. Refreshing the Town Crier costs one request per page of the
*entire round's* event list, every time, because there is no way to ask for only what is
new.

The same information as JSON, measured against real round-49 data:

| Payload | Rows | JSON | gzipped |
| --- | ---: | ---: | ---: |
| Whole dominion index | 264 | 55 KB | 10 KB |
| All intel on one dominion (six op types, latest of each) | 6 | 2.4 KB | 0.9 KB |
| Every Town Crier event of the round | 1722 | 529 KB | 56 KB |

In round 49 the realm gathered 2252 intel observations in total, arriving at about seven
per hour in the hours anything happened at all, and the Town Crier produced about 2.4
events per hour. A tool polling once per tick with a cursor would
move a few kilobytes an hour and could not go stale by more than one tick. That is the
whole argument for the API: not that scraping is hard, but that it forces every tool to
move three orders of magnitude more bytes than the data is worth, and to re-read history
it already has.

## Principles we would design to

1. **Same visibility, no more.** The API returns exactly what that dominion can already
   see on the site, with the same fuzz. A tool that can see further than the player is a
   cheat, and no efficiency gain is worth that.
2. **Read-only.** No endpoint performs a game action. OD Info never automates play, and an
   API without a write side keeps that guarantee structural rather than a promise.
3. **Immutable observations, monotonic cursors.** Intel and events are append-only records
   that never change after they appear, so a client stores them by id and never asks twice.
4. **Bulk by default.** One request answers "what is new for my realm", not one request
   per dominion.
5. **Say what is unknown.** `null` for unknown, `0` for zero, and per-observation accuracy
   metadata instead of constants each tool hardcodes for itself.
6. **Stable machine keys.** The same slug for a race, unit, building, tech, spell and
   wonder in reference data and in dominion payloads. Never a display name as a key.
