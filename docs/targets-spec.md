# Targets Spec

*Created: 2026-10-28*
*Status: Phases 1, 3 and 4 done*

## Problem

The attackers in my realm need targets. Spy and wizard strength is limited, so we cannot scan every
dominion. The Targets tab ranks dominions from data that costs no strength. The top of the list is
where to send ops next.

The tab selects candidates for a scan. A real hit starts with a full scan of the target, so rough
bounds are good enough here.

## Data that costs no strength

| Source | Gives |
|--------|-------|
| Dominion index (`/rounds/{round}/dominions`) | land, NW, race, realm, guard, status flags |
| `DominionHistory` | land and NW for each cron run |
| Town Crier | invasions and bounces with time, attacker, target, land lost and gained |
| Old ops | CS, BS, survey, land spy, castle, revelation, vision, of any age |
| Realm advisors | exact data of my realmies |

## Game rules

From the upstream source on `develop` (`NetworthCalculator.php`, `PopulationCalculator.php`,
`MilitaryCalculator.php`) and the wiki (Guards page).

### Networth

| Part | NW |
|------|----|
| Land | 20 per acre |
| Constructed building | 5 |
| Spy, assassin, wizard, archmage | 5 |
| Unit 1 and 2 (specs) | 5 |
| Unit 3 and 4 (elites) | 2 × max(OP, DP), with perks |

- Units at home and returning count (`getTotalUnitsForSlot`).
- Draftees, units in training, incoming land and buildings, resources and castle do not count.
- So a send does not change the NW. Only the Town Crier shows that units are away.

### Range and guards

Range is target land ÷ attacker land. A hit is possible only if the ratio is in the range of the
attacker and in the range of the target.

| Guard | Range |
|-------|-------|
| None | 40% to 250% |
| Royal | 60% to 166% |
| Elite | 75% to 133% |

### Population and draftees

- Draft per tick = 1% of peasants, only while military % < the draft rate of the player.
- Military uses population space: draftees, units at home and returning, units in training, spies,
  assassins, wizards, archmages.
- Max pop = raw housing × multiplier + barracks housing.
- Raw housing: home 30, other building 15, constructing building 15, barren acre 5, barracks 0.
- Each barracks houses 36 troops, plus race, tech and wonder perks. Draftees do not get this housing.
- Homes are always on the home land of the race (`home_land_type` in the race file).

## Phases

The phases go from easy to hard. Each phase gives a working tab. Stop after any phase if the tab
is good enough.

### Phase 1: public signals (easy)

All data is in the database now. No estimates.

Page `/targets`, DataTables, `dominions_in_play()`, the same realm checkboxes as Military.

At the top: a dropdown with my realmies to select the attacker. The default is my own dominion.

| Column | Content | Source |
|--------|---------|--------|
| Dominion, Realm, Race | | `Dominion` |
| Land, NW | | `DominionHistory` |
| NW/acre | NW ÷ land | |
| NW/acre (race) | ± % against the median of the same race | |
| Range | target land ÷ attacker land, rows out of 75%–250% hidden | |
| Sent | hours since the last invasion by this dominion, and land gained | `TownCrier.origin` |
| Hit by | hours since the last hit on this dominion, success or bounce | `TownCrier.target` |
| Explored | land growth in the last 24 hours minus land gained by invasions | `DominionHistory`, `TownCrier` |
| DP, DP/acre | paid DP from our ops | `MilitaryCalculator.paid_dp` |
| Draftees | last CS value | `ClearSight` |
| Ops age | age of the newest op, empty if none | |

Default sort: NW/acre (race), low first.

Highlights:
- "Sent" under 12 hours: units are away.
- "Ops age" empty or old with a low NW/acre: send ops here.

### Phase 2: guards (easy, needs a live round)

- Store `guard` from the dominion index in `DominionStatus`.
- Use the range of both guards for the Range column.
- Before the code: find the strings that the API gives for royal and elite guard. The capture in
  `docs/od_api/responses/dominions.json` has `guard: null` on all rows, because nobody can join a
  guard in the first 2 days.

### Phase 3 and 4: estimated DP (done)

`MilitaryCalculator.estimated_dp`, in the "Est DP" column. Default sort: Est DP.

```
with ops:     raw DP of the ops + max(0, NW growth − 25·land growth) × best DP/NW of the race
without ops:  (NW − 25·land) × best DP/NW of the race
both:         × (1 + DP bonus)
```

- Best DP/NW: the highest DP ÷ `Unit.networth` over the 4 units of the race. A 0/3 spec gives 0.6.
- 25 per acre: 20 for the land and 5 for a building on it.
- NW growth: from the `DominionHistory` row at the time of the ops to the newest row.
- DP bonus: what `MilitaryCalculator.defense_bonus` knows from the ops, with Ares.

Open:
- Spies and wizards: subtract 5 × (SPA + WPA) × land × fudge, from an old CS.
- Training: units in the BS training queue are in the raw DP and later also in the NW growth.

### Phase 5: draftee projection (hard)

Replace the last CS draftee value with a projection.

```
per tick:  draftees += 1% × peasants
peasants  ≈ max pop − military
cap:       draftees ≤ max pop − units − spywiz
```

This is an upper bound, because the draft rate is private. Training uses population space but has
no NW, so a dominion that trains a lot has fewer draftees than the projection.

Max pop, best source first:

| Have | Estimate |
|------|----------|
| Old survey | building ratios × current land |
| Old land spy only | homes ≤ home-land acres × current land ÷ old land, the rest 15 for each acre |
| Nothing | 15 × land as the floor, all home land as homes as the ceiling |

Land added after the old op uses the same ratios.

### Phase 6: calibration (hard)

The ceiling is an upper bound. Make it a realistic estimate from our own ops:

- For each opsed dominion, compare the real DP with the ceiling. Keep the median ratio for each race.
- For the "Nothing" row in phase 5, use the median home-land share of the race from our land spies.

## Not now

- Estimate the OP that a dominion sent from the Town Crier and the 5/4 rule.
- DP for each tick for the next 12 ticks. That needs a BS, so it belongs on Military or dominion
  info, not on this tab.

## Code to fix on the way

| Where | Problem | Phase |
|-------|---------|-------|
| `Buildings.raw_capacity`, `odinfo/domain/domainhelper.py:70` | gives 15 for each barracks, the game gives 0 + 36 troops | 5 |
| `Buildings.total_capacity`, `domainhelper.py:78` | calls `Dominion.population_bonus`, which does not exist | 5 |
| `Technology.pop_bonus`, `domainhelper.py:149` | no callers yet, needed for max pop | 5 |
| `NETWORTH_VALUES` import, `odinfo/calculators/military.py:9` | not used | any |

## Open

- An About page for the tab, with `reviewed_on` and `doc-sources`.
- The value of the fudge factor for spywiz.
