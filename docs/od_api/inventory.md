# What OD Info pulls in today

Everything below is scraped from opendominion.net over an authenticated session, except
the last two sections, which come from GitHub and from a file we maintain by hand.

## 1. Session

| Step | Request | What we need from it |
| --- | --- | --- |
| Load login page | `GET /auth/login` | the CSRF token out of `<meta name="csrf-token">` |
| Log in | `POST /auth/login` | session cookie |
| Select dominion | `POST /dominion/{id}/select` | switches the session to the round we are playing |

`{id}` is the player's own dominion id, which the user has to look up by hovering over
their own name in the search page and then type into a configuration file by hand. The
session has no way to tell us who we are.

## 2. Search page — the dominion index

`GET /dominion/search`, one HTML table with every dominion in the round.

| Field | Source | Stored as |
| --- | --- | --- |
| name | cell 0 link text | `Dominions.name` |
| dominion id | cell 0 href tail | `Dominions.code` |
| realm | cell 1 href tail | `Dominions.realm` |
| race | cell 2 | `Dominions.race` (display name, e.g. `Dark Elf`) |
| land | cell 3, comma-separated integer | `DominionHistory.land` |
| networth | cell 4, comma-separated integer | `DominionHistory.networth` |
| in range | cell 5 | read but not stored |
| server time | page footer, `title` attribute of a `<span>` | timestamp of the history row |

The footer also carries the round day and tick, in two `<strong>` tags inside that same
span. That is the only clock we have: `read_tick_time` in `odinfo/opsdata/scrapetools.py`
parses `day`, `tick`, `hh`, `mm` out of it. When a round ends the footer changes and both
readings disappear, so the tool cannot tell "round over" from "scraper broken".

Every poll of this page appends a `DominionHistory` row per dominion. That series is the
whole basis of the Networth Tracker, which reports deltas over 12, 24, 36 and 48 ticks.

## 3. OP Center index

`GET /dominion/op-center`, a table of dominions with the timestamp of the newest scan the
realm holds. We read only the timestamp, and use it to decide which dominions are worth
fetching in full. It is a poor man's change feed: it says *something* is newer, not what.

## 4. OP Center detail — the copy-ops JSON

`GET /dominion/op-center/{dominion}`, and `GET /dominion/advisors/op-center` for our own
dominion. Both carry a `<textarea id="ops_json">` holding the JSON behind the site's
"Copy Ops" button. This is the one place the game already speaks JSON, and it is the
single most valuable thing on the site for a tool.

Six sections, each with its own `created_at`, each stored as an immutable timestamped row.

### `status` → ClearSight

`status.name`, `status.race_name`, `status.realm`, `status.land`, `status.networth`,
`status.peasants`, `status.prestige`, `status.created_at`,
`status.resource_{platinum,food,lumber,mana,ore,gems,boats}`,
`status.military_{draftees,unit1,unit2,unit3,unit4}`,
`status.military_{spies,assassins,wizards,archmages}` (optional),
`status.wpa`, `status.spa` (optional).

We keep a `clear_sight_accuracy` column and have no way to fill it: the payload does not
say whether this reading was fuzzed by a Spire of Illusion.

### `barracks` → BarracksSpy

`barracks.units.home.{draftees,unit1..unit4}`, plus two optional maps:

```json
"training":  {"unit2": {"1": 100, "8": 241}, "spies": {"7": 40}}
"returning": {"unit2": {"5": 70, "6": 69, "9": 67}}
```

Keys are ticks until arrival, values are amounts. Every number in this section is fuzzed:
the game shows a value somewhere in `[true * 0.85, true / 0.85]`, and nothing in the
payload says so — we hardcode the 0.85.

### `castle` → CastleSpy

`castle.{science,keep,spires,forges,walls,harbor}.{points,rating}`.

### `land` → LandSpy

`land.totalLand`, `land.totalBarrenLand`, `land.totalConstructedLand`,
`land.explored.{plain,mountain,swamp,cavern,forest,hill,water}.{amount,constructed}`, and
optional `land.incoming` shaped like `{"cavern": {"11": 20}, "plain": {"11": 22}}`
(ticks → acres).

### `survey` → SurveyDominion

`survey.constructed.{home,alchemy,farm,smithy,masonry,ore_mine,gryphon_nest,tower,
wizard_guild,temple,diamond_mine,school,lumberyard,factory,guard_tower,shrine,barracks,
dock}`, `survey.barren_land`, `survey.total_land`, and optional `survey.constructing`
shaped like `{"unit1": {"11": 877}}` — building type → ticks → amount.

Our mapping is a hand-written dict with one line per building type, so a building added to
the game is invisible to us until someone edits the code and the database schema. There is
already one commented-out line (`forest_haven`) proving the point.

### `vision` → Vision

`vision.techs`, a map of tech key to display name: `{"tech_1_1": "Granaries"}`.

### `revelation` → Revelation

`revelation.spells`, a list of `{spell, duration}`, stored one row per spell. Duration is
in ticks from the observation.

## 5. Barracks spy archive

`GET /dominion/op-center/{dominion}/barracks_spy?page=N`, plain HTML, paginated, scraped
box by box. It holds every barracks spy the realm ever ran on that dominion, which is what
lets us combine several observations of the same tick and narrow the ±15% fuzz.

Parsing it means: finding `div.box-primary` blocks by their `<h3>` title text, reading the
timestamp out of the prose `Revealed 2026-07-14 09:00:00 by SomePlayer`, walking tick
columns 1..12 by position, and turning cell text like `~3,227`, `-` and `???` into
integers. `???` currently becomes `0`, because HTML has no way to say "unknown" that is
distinguishable from "none".

This is also where the ordering problem lives: a realmie's spy from tick 300 can become
visible to us at tick 340. Anything keyed on observation time alone will miss it.

## 6. Town Crier

`GET /dominion/town-crier?page=N`. We fetch page 1 to learn the page count, then every
page, then delete the whole local table and re-insert it. There is no way to ask for what
is new, so a refresh re-reads the entire round.

The events themselves are English prose that we reverse-engineer with regular expressions
into nine types: `invasion`, `bounce`, `wonder_attack`, `wonder_destruction`,
`raid_attack`, `war_declare`, `war_cancel`, `abandon`, `other`. Amounts (`conquered 143
land`, `captured 87`) come out of the same regexes. Dominion names are stripped from the
text first, because a player is free to name their dominion "has attacked" and poison the
matching.

Round 49 held 1722 events. The parser is the most fragile code in the project by a wide
margin: any rewording upstream silently reclassifies events as `other`, and the two most
recent commits to this repository are both Town Crier fixes.

## 7. Reference data — not from the game server at all

`data/ref-data/` mirrors `app/data` from the `develop` branch of the OpenDominion GitHub
repository: `races/*.yml`, `techs/v2.yml`, `spells.yml`, `wonders.yml`, `heroes.yml`.
`refdata_update.py` downloads it, archives what it replaces and reports which perks
appeared or disappeared.

This is a guess at what the live server is running. Nothing tells us whether the branch we
pull matches the round we are playing.

It also forces us to bridge naming ourselves: the search page says `Dark Elf`, the race
file is `darkelf.yml`, and `spells.yml` keys the same race as `dark-elf`.

## 8. Constants we maintain by hand

`data/game-constants.json` holds the numbers the game does not publish anywhere:
`jobs_per_building: 20`, `pop_per_home: 30`, `pop_per_non_home: 15`, `pop_per_barren: 5`,
`build_ticks: 12`, `masonry_multiplier: 2.6`, `gt_defense_factor: 1.6`,
`max_guard_tower_bonus: 0.32`, `gn_offense_bonus: 1.6`, `max_gryphon_nest_bonus: 0.32`,
`temple_bonus_per_perc: 1.35`, `max_temple_bonus: 0.27`, `ares_bonus: 0.1`,
`midas_touch_bonus: 0.1`, `barracks_spy_fuzz: 0.85`, `plat_per_alchemy_per_tick: 45`,
`plat_per_peasant_per_tick: 2.7`, `units_per_boat: 30`, `boats_per_dock: 2.25`,
`boats_per_dock_per_day: 0.05`, the six improvement curves (`max`, `factor`, `plus` each),
and the four networth weights.

Every one of these is a number we read out of the game's source or worked out from
observation, and every one of them drifts silently when the game is balanced.

## What it costs

Per hourly run of `cron.py`:

| Requests | What |
| --- | --- |
| 3 | login, CSRF, dominion select |
| 1 | search page (264-row HTML table) |
| 1 | OP Center index |
| N | OP Center detail, for dominions whose scan is newer than ours |
| R | OP Center detail for every realm member, unconditionally (R ≈ 13) |

`N` is bounded by the number of dominions in the round, 264 in round 49. Every one of
those is a full HTML page carrying, in the round-49 data, about 2.4 KB of JSON we
actually want.

On top of that, a Town Crier refresh costs one request per page of the whole round's
history and rewrites 1722 rows to learn about, on average, 2.4 new events per hour.
However, the Town Crier query is not part of a timed update because if this "replace all"
inefficiency: it is manually triggered every once in a while, and currently mainly used
in the "Awards" page.
