# Moving OD Info from scraping to the OpenDominion API

OpenDominion has a read-only JSON API at `https://www.opendominion.net/api/v1`. The
documentation is at https://www.opendominion.net/api-docs. This document maps each scraper in
OD Info to the API call that replaces it.

## API rules that shape the client

- **Key.** Send the key in the `X-API-Key` header. One key belongs to one dominion in one
  round, and it keeps working after the round ends. The player makes it on the Settings page
  of the dominion. The `/rounds` endpoints need no key.
- **Rate limit.** 60 requests per minute for each IP address. A 429 response carries a
  `Retry-After` header.
- **Errors.** The body is `{"error": code, "message": ...}`. The codes OD Info must handle:
  `under_protection`, `round_not_started`, `same_realm`, `not_found`, `invalid_api_key`,
  `rate_limited`.
- **Time.** Every timestamp is ISO 8601 UTC with a `Z` suffix.
- **Op payloads.** Each op has the fields of the Copy Ops export, under the in-game keys:
  `clear_sight`, `revelation`, `castle_spy`, `barracks_spy`, `survey_dominion`, `land_spy`,
  `vision`, `disclosure`. Copy Ops used `status`, `castle`, `barracks`, `survey` and `land`.

## Scraper to API

| Today | Code | API | What changes |
|---|---|---|---|
| Login, CSRF token, select dominion | `odinfo/services/od_session.py` | `X-API-Key` header | `username`, `password` and `current_player_id` leave `secret.txt`. `api_key` takes their place |
| Own dominion id, typed by hand | `Config.current_player_id` | `GET /dominions/me` → `id`, `realm` | The player does not look up their id |
| Server time, day and tick from the page footer | `scrapetools.read_server_time`, `read_tick_time`, `ODInfoFacade.current_tick` | `GET /dominions/me` → `server_time`, `round.day`, `round.hour` | `LOCAL_TIME_SHIFT` goes away. `GET /rounds` → `has_ended` tells that the round is over |
| Search page → `Dominion`, `DominionHistory` | `ops.grab_search`, `updater.update_dom_index` | `GET /rounds/{round}/dominions` | Adds `in_protection`, `guard`, `locked`, `abandoned`. A realm change updates `Dominion.realm` |
| OP Center index, then one page for each changed dominion | `ops.get_last_scans`, `ops.grab_ops`, `UpdateService.update_all` | `GET /dominions/me/op-center?max_age_hours=0` | 1 + N requests become 1 request |
| One page for each realmie | `ops.grab_my_ops`, `update_realmies` | `GET /dominions/me/advisors` | 1 request with exact data. Also gives modifiers, resources, buildings and statistics. Realmies who do not share their advisors are absent |
| Barracks spy archive, paged HTML | `ops.BarracksArchive` (no callers) | `GET /dominions/me/op-center/{id}/barracks_spy?limit=500` | Gives the history that the barracks spy refinement needs |
| Town Crier: every page, regex on prose, replace all rows | `facade/towncrier.py`, `updater.update_town_crier` | `GET /rounds/{round}/events?since=…&limit=500` | Typed events with a stable id. Only new events move. The hourly cron can include it |
| No wonder or war data | — | `GET /rounds/{round}/realms` | Wonder ownership makes the wonder perks possible |

## Town Crier event types

| API `type` | OD Info `event_type` | `amount` |
|---|---|---|
| `invasion`, `data.success` true | `invasion` | `data.land_lost` |
| `invasion`, `data.success` false | `bounce` | 0 |
| `war_declared` | `war_declare` | — |
| `war_canceled` | `war_cancel` | — |
| `wonder_spawned` | `wonder_spawn` | — |
| `wonder_attacked` | `wonder_attack` | — |
| `wonder_destroyed` | `wonder_destruction` | — |
| `raid_attacked` | `raid_attack` | — |
| `abandoned` | `abandon` | — |

`origin` is always the attacker, also for a bounce. The scraper gives the defender first for a
bounce, so `reload_town_crier` swaps the two.

## Outside the API

- Reference data: the `develop` branch on GitHub.
- Game constants: `data/game-constants.json`.
- Heroes, and accuracy or fuzz for each op: not available.
- Race: a display name, for example `"Nomad"`. `odinfo/domain/refdata.py` bridges it to the
  race files and to `spells.yml`.

## Order of work

1. Connector `odinfo/services/od_api.py` and real responses as test fixtures.
2. Identity, game clock and dominion index.
3. Ops from the op center and the realm advisors.
4. Town Crier.
5. New data, one item at a time: barracks spy archive, wonders, realmie modifiers, database
   name from the round number.

Each step deletes the scraper that it replaces, except the Town Crier scraper. The events
endpoint returns at most the newest 500 events and has no paging. The "Full reload" link on
`/stats` scrapes every Town Crier page, so the awards at round end see the whole round. That
keeps `ODSession`, `username` and `password` in use.