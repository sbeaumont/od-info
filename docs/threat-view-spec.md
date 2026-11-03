# Threat View Spec

*Created: 2026-11-02*
*Status: Phases 0 to 4 done. Phase 5 is optional.*

## Problem

The military overview shows the OP of every dominion. That does not tell a defender who can really
hit them. Most attackers do not send their full OP, because a full send leaves them weak at home.
Other dominions hold them back. When a top OP sends, it stops holding the others back, and many
hits follow in the next ticks.

A hit is often possible only in one or two ticks: when units come home, when training completes,
or when land changes the range. A defender also needs to know if a daily land bonus puts them in
range of a dangerous attacker.

The threat view answers one question for one realmie: **who can hit this dominion in the next 12
ticks, at which tick, and what has to happen first?**

## Terms

| Term | Meaning |
|------|---------|
| Defender | The realmie selected in the dropdown |
| Attacker | A dominion in another realm that has the defender in range |
| Threat | A dominion that can hit the attacker back while the attacker's army is out |
| 5/4 send | The most OP a dominion can send under the 5/4 rule |
| Safe send | The most OP a dominion can send while its home DP still beats every threat to it |
| Trigger | A threat that has to send first before the attacker's safe send breaks the defender |
| Free sender | A dominion whose home DP after a 5/4 send beats every threat to it |
| Normal send | Unit slots 1 and 4 go out, slots 2 and 3 stay home. The "Normal Send" on the military page. |

## The algorithm

This section is written for the manual. It goes into the About pages unchanged.

### Range

An attacker can hit the defender at a tick when the defender's land is between the minimum and the
maximum range of the attacker's land at that tick. The maximum range is 250%. The minimum range is
75% by default. A hit below 75% is bottom
feeding. The game penalizes it heavily, so it only happens as a last measure near the end of the
round. You can set a lower minimum range on the page to see those attackers too.

Land changes during the 12 ticks. An invasion in the Town Crier gives the attacker 2 times the land
its target lost, 12 ticks after the hit. A Land Spy also shows land from exploring. It replaces the
invasions from before its time, and invasions after it add to it. A daily land bonus gives 20 acres
at once. Range is therefore calculated again for each tick.

### OP and DP at a tick

For each tick from now to 12 ticks ahead, the view calculates the army that is home at that tick:

- Units at home now stay home.
- Returning units count from the tick they arrive.
- Units in training count from the tick their training completes.

Each unit counts from the tick it arrives home. A hit happens at one tick, so the army at that tick
is what counts. The defender's numbers are exact, because they come from the realm advisors. The
numbers of other dominions come from their last ops.

### The safe send of an attacker

1. Find all threats to the attacker at the tick. A threat is in another realm than the attacker
   and has the attacker in range. Its units that are out do not count in its OP at that tick.
2. Calculate the 5/4 send of each threat, with its temples, against the attacker's DP bonus.
3. Take the strongest one. The attacker has to keep enough DP home to beat it.
4. Send the units that are free to go: pure offense units first, then hybrid units from best
   OP/DP ratio down, until the DP that stays home is just enough.
5. The OP that goes out is the safe send. It is never more than the 5/4 send.

A dominion with no threats, or with home DP after a 5/4 send that beats every threat, is a free
sender. Its safe send is its 5/4 send.

### Can the attacker break the defender?

Take the attacker's safe send with its temples, against the defender's DP bonus. Compare it with
the defender's DP at the tick. The difference is the margin. A positive margin means the attacker
can break the defender without risk.

### Triggers: what sets an attacker free

When a strong dominion sends, its army is out until it returns. During that time it is no threat
to anyone. Every dominion that it held back can send more. This is why many hits follow when a
top OP sends.

If the safe send does not break the defender, the view looks for the trigger:

1. Put the threats to the attacker in order, strongest first.
2. Take away the strongest threat. Calculate the safe send again without it.
3. If the safe send now breaks the defender, stop. The threats taken away are the triggers.
4. If not, take away the next threat and go back to step 2.
5. Stop after two triggers. A longer chain depends on old ops of many dominions, so the view does
   not show it. The maximum is `THREAT_MAX_TRIGGERS` in `odinfo/config.py`.
6. If the attacker still cannot break the defender, the attacker has no safe hit at this tick.

The defender can itself be a threat to the attacker. When the view takes the defender away, the
defender has sent. It then keeps only its home DP after a full 5/4 send, and the attacker has to
beat that DP instead of the full DP. So a defender that sends can make itself a target, even for
an attacker that cannot break its full DP.

For each trigger, the view also shows if the trigger is itself a free sender. A trigger that is
free can send at any time. A trigger that is held back needs its own trigger first, so that chain
is less likely.

### What the view leaves out

- The view takes the threat to an attacker as the full 5/4 send of that threat. A threat that is
  itself held back cannot send its full OP. So the safe send is the lowest value, and a real
  attacker can send somewhat more.
- An attacker can accept risk and send more than its safe send. The yellow cells show where a full
  5/4 send breaks the defender.
- The view shows one hit at a time. A realm can hit one target with several dominions in a row.
- Numbers of other dominions are as good as their last ops. Old ops make the per-tick numbers
  guesses.
- Other dominions can claim a daily land bonus too. The view does not know when.

## The page

Route `/threats`, with `?defender=<code>`. The default defender is my dominion. Tab next to Targets.

### Controls

| Control | Effect |
|---------|--------|
| Defender | Dropdown of the realmies, the same as the attacker dropdown on the Targets tab |
| Min range | Number box, default 75 (%) |
| Daily land bonus | Checkbox plus a tick dropdown (now to +12). Adds the bonus acres to the defender's land from that tick. |
| Realms | Realm checkboxes, the same as on the military page |

### Grid

One row for each dominion that has the defender in range at one or more ticks. One column for each
tick from now to +12. Before the tick columns: dominion, realm, race, ops age.

```
Attacker   Realm  Ops   now    +1     +2     +3     +4    ...  +12
Grimjaw    5      2     -8k    -8k    +4k    +4k    +4k        +9k
Moonveil   7      0                          -2k    +3k        +3k
Vex        7      1     -3k    -3k    -3k    +1k    +1k        +1k
```

The value in a cell is the margin in thousands of OP. The color gives the meaning:

| Cell | Value | Color |
|------|-------|-------|
| Not in range | empty | dark grey |
| Even a 5/4 send cannot break | 5/4 margin (negative) | none |
| Only a 5/4 send breaks, and it is not safe | 5/4 margin | yellow |
| Safe send breaks after one or more triggers | safe send margin with the triggers out | orange |
| Safe send breaks now | safe send margin | red |

A row whose ops are older than 12 ticks is shown dim, the same rule as the `invalid` class.

### Tooltip

Each cell value has a tooltip in short text:

| Cell | Tooltip example |
|------|-----------------|
| Red | `safe 132k vs DP 128k · free` |
| Orange | `safe 132k vs DP 128k · after Vex (free)` |
| Orange, two triggers | `after Vex (held: Kragg), Kragg (free)` |
| Yellow | `5/4 141k · safe 110k · held: Vex, Kragg` |
| None | `5/4 120k vs DP 128k` |
| Returning units | add `· +40k OP at +4` |

### Sort

By the first tick at which a cell is red, then orange, then yellow. Ties by margin.

## Data

| Needed | Source |
|--------|--------|
| Military at a tick, other dominions | CS for home units, BS for returning units and training queue (`arrived_returning_units`, `arrived_training_units` with `from_tick`) |
| Military at a tick, defender | Realm advisors |
| Land at a tick | `Dominion.land_at`: `current_land` (arrived land only), plus the incoming acres of the Land Spy, plus `conquest_land_factor` × land lost for each invasion in the Town Crier after the Land Spy, arriving `land_arrival_ticks` after the hit |
| Range limits | `MIN_RANGE` and `MAX_RANGE` from `odinfoweb/viewmodels/targets.py`, shared with the Targets tab |
| Temples, DP bonus | `MilitaryCalculator`, same as the military page |
| 5/4 send and safe send | `MilitaryCalculator.five_over_four` and `safe_op_versus`, on the army at the tick |
| Return time | New `return_ticks: 12` in `data/game-constants.json`, less the `faster_return` perk from the race, wonder and other ref-data |
| Daily land bonus | New `daily_land_bonus: 20` in `data/game-constants.json` |

The safe send is the lower of `safe_op_versus` and the 5/4 send.

## Phase 0: Military in the domain

The threat view needs the military of a dominion at each tick. `Dominion.military` gives the
military as a plain dict, and `MilitaryCalculator` and `RatioCalculator` keep that dict as
`self.army`. The dict holds numbers only, so the logic that tracks troop numbers is in three places.
`MilitaryCalculator` holds both the tracking and the OP/DP calculation. Draftees come from two
sources: `MilitaryCalculator.draftees` reads the last CS, and `safe_op_versus` reads
`self.army['draftees']`.

Phase 0 makes the military an object that does its own tracking. The name stays `military`, as in
the game.

### Two responsibilities

| Responsibility | Question it answers | Home after phase 0 |
|----------------|---------------------|--------------------|
| Tracking | How many units of each type, and draftees, are home at tick t, with what bounds? | `Military` in `odinfo/domain/military.py` |
| Implications | What OP and DP do those numbers give, with bonuses, temples and the 5/4 rule? | `MilitaryCalculator` |

### What moves into `Military`

| Logic | Lives now in |
|-------|--------------|
| CS and BS merge, paid training (`military`, `military_from_cs`, `military_has_bs_worst_case`) | `Dominion` |
| Draftees from the last CS (`draftees`) | `MilitaryCalculator` |
| BS refinement and arrivals (`refine_unit_estimate`, `refined_home_units`, `clear_sight_units`, `starting_point`, `arrived_returning_units`, `arrived_training_units`, `_refined_amounts`) | `MilitaryCalculator` |
| BS ops of one tick (`get_barracks_spies_in_tick`) | `MilitaryService` |
| The orchestration of current strength, refined paid strength and forecast (`calculate_current_strength`, `refine_paid_strength`, `strength_forecast`) | `MilitaryService` |

`BarracksSpy` and `ClearSight` keep the logic that reads one op (`allows_amount`, `paid_training`,
`amount_returning`, `military`). `Military` combines the ops. `get_barracks_spies_in_tick` filters
`dom.barracks_spy` only, so `Military` works on the dominion alone.

### Interface

- `Dominion.military` returns a `Military`, or `None` without a CS or BS.
- A `Military` holds the values of the dict now: the count of each unit, `draftees`, `timestamp`
  and `paid_until`. `amount(unit_nr)` gives a unit count.
- `dom.military` is the paid military, with the same numbers as the dict now.
- `military.at(tick)` returns a `Military` with the units home at a tick from now. That is the
  refined home units, plus the returning units and training that arrive by that tick. Without a
  BS, it is the CS military, the same at every tick.
- `military.confidence` gives the confidence string that the military page shows now.
- The calculators rename `self.army` to `self.military`. `MilitaryCalculator(dom, tick=None)` sets
  it to `dom.military` without a tick, and to `dom.military.at(tick)` with one. `RatioCalculator`
  sets it to `dom.military`.
- Current strength is `at(0)`. Refined paid strength is `at(paid_until)`. The forecast is `at(0)` to
  `at(12)`, each through a `MilitaryCalculator` for that tick.

### Readers of the dict now

| Reader | Uses |
|--------|------|
| `MilitaryCalculator` | `unit1` to `unit4`, `draftees`, `timestamp`, `paid_until`, and `None` for no ops |
| `RatioCalculator` | the same dict |
| `MilitaryService.military_list` | `mc.army` for no ops, `paid_until` |
| `viewmodels/targets.py` | `mc.army is not None` |
| `test/test_dominion.py` | `dom.military['unit3']` |

These readers change from dict keys to attributes, and from `mc.army` to `mc.military`.

### Steps

1. **Move**: make `Military` with the tracking logic unchanged, and change the readers to it. Every
   number on every page stays the same. Move the tests of the moved methods to
   `test/test_military.py`. All tests pass unchanged apart from the place they call.
2. **One draftee rule**: draftees follow the same CS and BS rules as the units. In the BS branch,
   keep the CS draftees when the BS allows them, else take the BS worst case.
   `military_has_bs_worst_case` counts draftees too. `MilitaryCalculator.draftees` and
   `safe_op_versus` both read `self.military.draftees`. This step changes numbers. A test shows the new
   draftee count for a BS that is newer than the CS.
3. **Land**: `Dominion.land_at(tick)` gives `current_land` plus the Land Spy acres that arrive by
   that tick. The arrival logic moves out of `Land.incoming`, which then uses it.

### Land from a survey

Every building sits on an acre of its land type. So a survey gives a lower limit on the land of
each type, and on the total land. Phase 0 uses the Land Spy only. The survey is a source to add
when a dominion has a survey but no Land Spy.

## Phases

1. **Military at a tick**: done by phase 0. What is left is a test that
   `MilitaryCalculator(dom, tick)` gives the 5/4 send of the military at that tick.
2. **Safe send and triggers**: pure functions for the threats, the safe send, the margin and the
   trigger search. Tests with small made-up realms.
3. **Page**: route, facade method, view model, template with grid, colors and tooltips.
4. **Manual**: an About page with the algorithm section, with `reviewed_on` and `doc-sources`.
5. **Optional**: a safe send column on the military page.

## Open questions

- **Land arrival for 9-tick units**: conquered land arrives 12 ticks after the hit. For units that
  return in 9 ticks, the 12 ticks is a best guess. Check it in the game.
- **Guards**: a guard (Royal, Elite) limits the range in both directions. The first version uses
  the normal range only.
- **Better threat estimate**: the threat to an attacker can use the safe send of that threat
  instead of its 5/4 send, calculated in a second pass. That gives an upper value next to the
  lower value. Add it only if the lower value turns out to be too careful.