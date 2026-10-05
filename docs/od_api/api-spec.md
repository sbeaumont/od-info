# Proposed REST API

A sketch of what OD Info would consume. Written concretely so it can be argued with:
every endpoint below replaces something the [inventory](inventory.md) says we scrape.

## Ground rules

**Visibility.** Every response is bounded by what the authenticated dominion can already
see on the site, with the same fuzz applied. The API is a different transport for the same
information, never a wider view.

**Read-only.** `GET` only. No endpoint queues, trains, casts, invades or selects. A tool
that can act is a bot problem; a tool that can only read is not.

**Immutable records.** An intel observation or an event, once returned, never changes.
Clients store them by id and never ask for them again. Only the dominion index and the
player's own dominion are mutable snapshots.

## Conventions

| Concern | Choice |
| --- | --- |
| Base | `https://www.opendominion.net/api/v1` |
| Versioning | in the path; additive changes (new fields) are not a new version |
| Auth | `Authorization: Bearer <token>`, token issued from the account page, scoped to one account |
| Identification | `User-Agent: <tool>/<version>` required, so load can be attributed |
| Format | JSON only, UTF-8 |
| Numbers | JSON numbers, never formatted strings — no `~3,227` |
| Time | ISO-8601 UTC (`2026-07-14T09:00:00Z`) **and** the tick number it belongs to |
| Unknown | `null` means unknown, `0` means zero, and they are never interchangeable |
| Keys | stable slugs (`dark_elf`, `gryphon_nest`, `tech_1_1`, `ares_call`, `obelisk_of_power`), identical in reference data and in dominion payloads |
| Errors | `application/problem+json` per RFC 9457 |
| Compression | gzip on every response |

### List envelope

```json
{
  "data": [ ... ],
  "meta": {
    "server_time": "2026-07-14T09:00:00Z",
    "round": 49,
    "day": 14,
    "tick": 9,
    "next_cursor": "c_8f21a0",
    "has_more": false
  }
}
```

`next_cursor` is opaque and always present, including when `data` is empty, so an idle
client keeps a valid cursor without special-casing.

## The efficiency rules

This is the part that matters most, and the part a tool can hold up its end of.

### 1. Feeds are cursors, not timestamps

Intel and events are append-only. Each record carries two times:

- `observed_at` — when the thing happened in the game, which is what the client reasons with.
- `recorded_at` / `seq` — when the record became visible to *this* realm, which is what
  the cursor orders by.

They differ, and the difference is not theoretical: a realm member's barracks spy from
tick 300 can first become visible to us at tick 340 when someone opens the archive page.
A feed ordered by `observed_at` silently loses that record for any client that has already
read past tick 300. So:

> `since` takes a cursor from a previous `meta.next_cursor`. An ISO timestamp is accepted
> as a convenience and is interpreted against `recorded_at`, never `observed_at`.

### 2. `since` is required, with a bounded default

`GET /intel` and `GET /events` without `since` return the last 24 ticks and set
`next_cursor`, rather than the round. Full history is reachable, but only by paging
explicitly from `since=0`, which is the one expensive call a client makes once per round
and can be rate-limited harder than the rest.

### 3. One poll per tick is enough, and the response says so

The game state changes on the tick. Every response carries

```
Cache-Control: max-age=<seconds until the next tick>
ETag: "..."
```

so a client that respects caching physically cannot poll faster than the game changes, and
a client that polls anyway gets a `304` for free. Recommend not counting `304` against the
rate limit — it rewards the correct behaviour.

### 4. Bulk by default

Nothing in this API needs one request per dominion. The realm's whole intel position is
one feed; the whole round's dominion index is one page. That is the 264-requests-to-1
collapse, and it is worth more than every other rule here combined.

### 5. Sections are opt-in

`include=status,barracks` on the intel feed, `fields=code,land,networth` on the dominion
index. A tool that only draws military tables should not have to move surveys.

### 6. Cache keys the server can share

Reference data and the dominion index are identical for every player, so they cache once
for everyone. Intel is shared by a realm, not by a player, so it caches per realm. Only
`/me` is per-player. Worth designing for from the start.

### 7. Limits

`limit` defaults to 200 and caps at 1000. Rate limit per token, advertised in
`RateLimit-Limit` / `RateLimit-Remaining` / `RateLimit-Reset`, `429` with `Retry-After`
when exceeded. A well-behaved tool needs three requests per tick.

## Endpoints

### Meta

#### `GET /me`

Replaces the player id the user copies into a config file by hand, and the manual clock
offset.

```json
{
  "account": {"id": 4711, "display_name": "AgFx"},
  "dominion": {"id": 16271, "name": "Chuck Norris", "realm": 6, "race": "dwarf", "round": 49},
  "scopes": ["read"],
  "server_time": "2026-07-14T09:00:00Z"
}
```

#### `GET /rounds/current`, `GET /rounds`, `GET /rounds/{id}`

```json
{
  "number": 49,
  "league": "standard",
  "status": "active",
  "started_at": "2026-06-01T00:00:00Z",
  "day": 14,
  "tick": 9,
  "server_time": "2026-07-14T09:00:00Z"
}
```

`status` is the one field here that a tool cannot fake: today, when a round ends, the day
and tick simply vanish from the page footer and a tool cannot tell that from its own
scraper breaking.

`{id}` may be `current` everywhere a round id appears below.

### Reference data

#### `GET /reference`

An index with a version stamp, so a client fetches the bodies once per round and then
revalidates with `If-None-Match`.

```json
{
  "version": "r49-2026-06-01",
  "collections": {
    "races":     {"url": "/api/v1/reference/races",     "etag": "\"a1b2\""},
    "buildings": {"url": "/api/v1/reference/buildings", "etag": "\"c3d4\""},
    "techs":     {"url": "/api/v1/reference/techs",     "etag": "\"e5f6\""},
    "spells":    {"url": "/api/v1/reference/spells",    "etag": "\"7a8b\""},
    "wonders":   {"url": "/api/v1/reference/wonders",   "etag": "\"9c0d\""},
    "heroes":    {"url": "/api/v1/reference/heroes",    "etag": "\"1e2f\""},
    "constants": {"url": "/api/v1/reference/constants", "etag": "\"3a4b\""}
  }
}
```

Two things make this worth more than the YAML we mirror from GitHub today:

- It is the data **the running server actually uses**, not the tip of a branch that may or
  may not match the round.
- `constants` publishes the numbers that are currently in nobody's data files: jobs per
  building, population per home, build ticks, the masonry multiplier, the guard tower /
  gryphon nest / temple factors and their caps, the improvement curves, the networth
  weights, boats per dock, units per boat, and the barracks spy fuzz factor. Every tool
  rederives these by hand and every tool is wrong for a while after a balance change.

Units belong inside their race, keyed by slug rather than by position, with the slot
number alongside for the payloads that use it:

```json
{
  "slug": "dwarf",
  "name": "Dwarf",
  "perks": {"defense": 5},
  "units": [
    {"slot": 1, "slug": "dwarf_warrior", "name": "Warrior",
     "power": {"offense": 5, "defense": 0},
     "cost": {"platinum": 1000, "ore": 50},
     "perks": {}}
  ]
}
```

### Round state

#### `GET /rounds/{id}/dominions`

The search page. Query: `since`, `fields`, `realm`, `in_range`.

```json
{
  "data": [
    {
      "id": 16271, "name": "Chuck Norris", "realm": 6, "race": "dwarf",
      "land": 1420, "networth": 184300,
      "status": "active",
      "in_range": {"land_ratio": 1.02, "networth_ratio": 0.98, "attackable": true},
      "as_of_tick": 9
    }
  ],
  "meta": {"...": "..."}
}
```

With `since`, only rows that changed since that cursor. `status` distinguishes active from
locked, abandoned and deleted, which today we can only infer.

#### `GET /rounds/{id}/dominions/history?since=<cursor>`

Land and networth per tick, which is what the Networth Tracker measures deltas over. If
this does not exist, a client rebuilds it by polling the index every tick and storing the
result — which works, but means the series is only as complete as the client's uptime, and
a tool started mid-round can never recover the earlier ticks that the server already has.

#### `GET /rounds/{id}/realms`, `GET /rounds/{id}/realms/{number}`

Members, name, and the war state — declared, mutual, cancelled, with the tick it changed.
Today war state exists only as a Town Crier sentence.

#### `GET /rounds/{id}/wonders`

Active wonders, which realm holds each one, current power, and damage taken. Public
knowledge in the game and completely invisible to a tool; see [gaps.md](gaps.md) for why
that matters even while the combat wonders are switched off.

### Intel

#### `GET /rounds/{id}/intel`

One feed for everything the realm has gathered. Query: `since` (cursor), `type`,
`dominion`, `include`, `limit`.

```json
{
  "data": [
    {
      "id": "int_9f3c21",
      "seq": 88213,
      "type": "barracks_spy",
      "dominion": 16271,
      "observed_at": "2026-07-14T09:00:00Z",
      "observed_tick": {"day": 14, "tick": 9},
      "recorded_at": "2026-07-14T09:04:11Z",
      "revealed_by": {"dominion": 16299, "name": "Someone Else"},
      "accuracy": {"kind": "range", "factor": 0.85},
      "payload": {
        "home": {"draftees": 2100, "dwarf_warrior": 12400, "dwarf_cleric": null},
        "training":  {"dwarf_cleric": {"1": 100, "8": 241}},
        "returning": {"dwarf_cleric": {"5": 70, "6": 69}}
      }
    }
  ]
}
```

Points worth arguing over:

- **`accuracy` per observation, not per game.** `{"kind": "exact"}` where the game shows a
  true number, `{"kind": "range", "factor": 0.85}` for a barracks spy,
  `{"kind": "range", "factor": 0.85, "reason": "spire_of_illusion"}` for a clear sight
  fuzzed by a wonder. Today we hardcode 0.85 and cannot see the wonder case at all, so we
  present fuzzed numbers as exact.
- **`null` for a value the op did not reveal.** The HTML shows `???` and we currently turn
  that into `0`, which is a wrong answer rather than a missing one.
- **`revealed_by` and `recorded_at`** are what make combining several observations of the
  same tick sound, which is how a tool narrows the fuzz range honestly.
- **Unit keys by slug.** `unit1..unit4` works but forces every payload to be joined
  through the race before it means anything. Both is fine: slug as the key, slot as a
  field in reference data.

Types: `clear_sight`, `barracks_spy`, `castle_spy`, `survey_dominion`, `land_spy`,
`vision`, `revelation`. The payload of each is the corresponding section of today's
copy-ops JSON, which is already close to right — see the inventory for the field lists.

Two shapes that should change on the way over:

- `survey.constructed` as a slug-keyed map rather than a fixed set of fields, so a new
  building type does not need a client code change to be visible.
- `revelation` as one record listing all active spells with their remaining ticks, rather
  than a row per spell.

#### `GET /rounds/{id}/dominions/{dominion}/intel`

The latest observation of each type for one dominion — the "open a dominion's page" call.
`?history=true` returns everything, cursor-paged, which is the barracks spy archive.

### Events

#### `GET /rounds/{id}/events`

Town Crier, structured. Query: `since` (cursor), `type`, `dominion`, `realm`, `limit`.

```json
{
  "data": [
    {
      "id": "ev_44a1",
      "seq": 88220,
      "type": "invasion",
      "occurred_at": "2026-07-14T08:31:02Z",
      "tick": {"day": 14, "tick": 8},
      "actor":  {"dominion": 16271, "name": "Chuck Norris", "realm": 6},
      "target": {"dominion": 16333, "name": "Some Target", "realm": 9},
      "result": "success",
      "payload": {"land_conquered": 143, "land_generated": 21},
      "text": "Chuck Norris (#6) invaded Some Target (#9) and conquered 143 land."
    }
  ]
}
```

The `text` stays, for display. What matters is that `type`, the participants and the
amounts arrive as fields instead of being recovered from prose with regular expressions.
Nine event types, all parsed out of English sentences, is the single most brittle thing in
this codebase — a rewording upstream reclassifies events as `other` and nothing complains.

Types we parse today, as a starting list: `invasion`, `bounce`, `wonder_attack`,
`wonder_destroyed`, `raid_attack`, `war_declared`, `war_cancelled`, `abandoned`. The
target of a wonder event is a wonder, and of a war event a realm, so `target` needs a
`kind` discriminator rather than always being a dominion.

### Own dominion

#### `GET /rounds/{id}/me/dominion`

Exact private state: resources, military by unit slug, the training / returning /
construction / exploration queues per tick, buildings, land by type, researched techs,
active spells with remaining ticks, hero and level, prestige, draft rate, boats, spy and
wizard ratios.

Today we read our own dominion through the same op-center JSON as anyone else's, which
means a tool works with a fuzzed view of numbers the player is looking at exactly, on
their own status page, in another browser tab.

#### `GET /rounds/{id}/me/realm`

Members, war state, wonders held, and realm-wide bonuses in effect.

## What an hour costs a well-behaved client

| Request | Typical response |
| --- | --- |
| `GET /rounds/current` | 300 B |
| `GET /rounds/49/dominions?since=…` | 10 KB gzipped for a full index, far less for a delta |
| `GET /rounds/49/intel?since=…` | a handful of records, ~1 KB |
| `GET /rounds/49/events?since=…` | 2 or 3 events, ~1 KB |

Four requests and roughly 12 KB per tick, against today's `5 + N + R` HTML page loads plus
a full re-read of the round's Town Crier. Reference data is fetched once per round and
revalidated with a `304`.

## Open questions

1. **Token scope.** One token per account, or one per tool? Per tool is better for
   attributing load and revoking a misbehaving client, and costs the game an extra table.
2. **Backfill.** Is `since=0` allowed at all, or does a tool that starts mid-round simply
   accept that it has no history? Our preference is allowed but paged and rate-limited.
3. **Expiry.** Does intel ever stop being visible? If so the feed needs a
   `intel.removed` record type, otherwise clients keep a copy of something the game
   considers gone.
4. **A tick pulse.** An SSE stream or webhook that fires on the tick would let clients
   drop polling entirely. Nice, not necessary, and only worth it if it is cheaper for the
   server than the four cached requests above.
5. **Realm-shared intel.** Confirming that intel visibility is a realm property and not a
   player property matters for both correctness and cacheability.
