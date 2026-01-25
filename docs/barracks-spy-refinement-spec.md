# Barracks Spy Refinement Spec

*Created: January 2025*
*Status: Phases 0-3 Complete*

## Problem

BarracksSpy data has a fuzz range. From OD source (`InfoMapper.php`), each observed value is:
```
random_int(ceil(true * 0.85), floor(true / 0.85))
```
So observed is in range **[true × 0.85, true × 1.176]** (asymmetric: -15% to +17.6%).

**Important**: Each unit value (draftees, unit1-4, each returning entry) gets its own independent random roll. Training queue values are **NOT fuzzed** - they're exact.

Currently, the code uses a pessimistic single-observation estimate:
- Home units: `observed / 0.85` (assumes we saw the minimum, true value could be higher)
- Away units: `observed * 0.85` (assumes we saw the maximum, true value could be lower)

## Solution

When multiple BarracksSpy observations exist within the same tick (hour), combine them to get tighter bounds on the true value.

### The Math

If true value is T, each observation O is uniformly distributed in [0.85×T, T/0.85] = [0.85×T, 1.176×T].

Given multiple observations:
- **Lower bound on T**: `max(observations) / 1.176`
- **Upper bound on T**: `min(observations) / 0.85`

The more observations, the tighter the bounds (statistically likely to capture more of the range).

**Special case - "Locked" value**: If observations span the full fuzz range (ratio of max/min >= 1.38), we've captured both extremes. The true value can be calculated exactly:
```
T = max(observations) / 1.176 ≈ min(observations) / 0.85
```

### Example

Observations for home_unit1: [333, 379, 428, 450, 456]
- min = 333, max = 456
- ratio = 456/333 = 1.37 (< 1.38, so not quite "locked")
- Lower bound = 456 / 1.176 = 388
- Upper bound = 333 / 0.85 = 392
- Bounds are very tight → true value ≈ 390 (±0.5%)

With one more low observation that pushes ratio to 1.38+, value would be fully locked.

## Two Strength Calculations

### Current Strength (new)
What they have *right now*:
- Home units (with refined estimates)
- Units that have already returned

Does NOT include:
- Training units (12 ticks away)
- Units still returning

Use case: "Can I hit them right now?"

### Paid Strength (existing)
What they'll have when all training/returning completes:
- Home units (fuzzed)
- All returning units (fuzzed)
- All training units (**exact** - no fuzz!)

Use case: "What do I need to train to match them eventually?"

**Note**: Since training values are exact, improving paid strength estimates only requires refining home and returning values. When significant units are in training, the paid estimate is already fairly accurate.

**Implementation note**: `Dominion.military` already prefers ClearSight (exact) over BarracksSpy (fuzzed) when CS is recent. Refinement is only used for "current strength" calculations, keeping the implementation simple.

**Expected behavior**: Current strength can be significantly lower than paid strength when:
1. Many units are in training (common scenario)
2. Units are still returning from a send

Example: A dominion with 1,524 Flamewolves home + 781 in training shows ~3,100 current OP vs ~9,600 paid OP. This correctly reflects that ~2,000 offensive units aren't deployable yet.

## Data Collection Issue

**Problem**: Current scraping only fetches the *latest* BS for each dominion. If multiple BSes were done between refreshes, we lose the intermediate observations.

**Current behavior (confirmed)**:
- `grab_ops()` in `ops.py` fetches `/dominion/op-center/{dom_code}`
- This returns a JSON with only the **latest** ops data
- `update_ops()` in `updater.py` stores the BS if that exact timestamp doesn't exist
- Multiple BSes between refreshes → only the last one is captured

**Solution**: Scrape the BS archive pages on OpenDominion to get historical BS data.

**Investigation needed**:
- [x] Confirm current scraping behavior - **CONFIRMED: only gets latest**
- [x] Find the BS archive page URL structure on OpenDominion - **FOUND**

**Archive URL pattern**:
```
/dominion/op-center/{dom_code}/barracks_spy
/dominion/op-center/{dom_code}/survey_dominion
/dominion/op-center/{dom_code}/castle_spy
/dominion/op-center/{dom_code}/land_spy
... (similar for all op types)
```

Where `{dom_code}` is the dominion code (e.g., 15538) - same as used elsewhere in the system.

Each archive page:
- Shows all historical scans of that type for the dominion
- Scans are listed vertically
- Pages are paginated

**Remaining investigation**:
- [x] Determine HTML structure of archive pages (for scraping) - **DONE**
- [x] Check pagination structure - `?page=N` query parameter
- [x] Determine data retention - **OD keeps ALL scans for the entire round**
- [x] Implement archive scraping for barracks_spy - **DONE** (BarracksArchive class)
- [ ] Consider extending to other op types later

**Important**: Use the timestamp from each BS entry's `<em>Revealed {timestamp}...</em>` to determine which tick it belongs to. Existing `read_server_time()` in scrapetools handles OD time parsing.

### Archive Page HTML Structure

Each BS entry on the archive page consists of:

**1. Units in training and home table**
```html
<div class="box box-primary">
  <div class="box-header with-border">
    <h3 class="box-title"><i class="ra ra-sword"></i> Units in training and home</h3>
  </div>
  <div class="box-body table-responsive no-padding">
    <table class="table">
      <thead>
        <tr>
          <th>Unit</th>
          <th>1</th>...<th>12</th>  <!-- training ticks -->
          <th>Home (Training)</th>
        </tr>
      </thead>
      <tbody>
        <tr><td>Draftees:</td><td colspan="12">&nbsp;</td><td>~3,227</td></tr>
        <tr><td>Spearman:</td><td>-</td>...<td>-</td><td>0</td></tr>
        <!-- more unit rows -->
      </tbody>
    </table>
  </div>
  <div class="box-footer">
    <em>Revealed 2025-12-23 16:36:41 by Music Video Palpatine</em>
    <span class="label label-danger">Invalid</span>  <!-- or label-warning for stale -->
    <br>
    <span class="label label-default">Day 45</span>
    <span class="label label-default">Hour 23</span>
  </div>
</div>
```

**2. Units returning from battle table** (same structure, different header)
```html
<div class="box box-primary">
  <h3 class="box-title"><i class="fa fa-clock-o"></i> Units returning from battle</h3>
  <!-- Similar table with ticks 1-12 and "Total" column -->
</div>
```

**Key data points to extract**:
- Timestamp from `<em>Revealed {timestamp} by {player}</em>`
- Day/Hour from the `label-default` spans
- Home unit counts from last column (values prefixed with `~` indicate uncertainty)
- Training amounts from tick columns (1-12)
- Returning amounts from the second table

**Value formats**:
- `~3,227` - uncertain value (subject to 15% error)
- `0` - exact zero
- `-` - no units in that tick
- `???` - unknown/missing data

**Pagination**:
- URL pattern: `/dominion/op-center/{dom_code}/barracks_spy?page=N`
- Links in `<ul class="pagination">` element

## Situation Change Detection

Within a tick, the true value should be constant UNLESS:
1. Someone sends troops (AWAY increases, HOME defense drops)
2. Someone gets hit (units die)
3. Training completes (shouldn't happen mid-tick if ticks are hourly)

**Detection approach**:
- If observation spread exceeds normal max (ratio > 1.45), something changed mid-tick
- Flag this in the UI as "situation may have changed"
- Could indicate tactical opportunity (they just sent!)

## Implementation Plan

### Phase 0: Rename op/dp to paid_op/paid_dp ✓
Rename existing properties for clarity before adding current strength.

**MilitaryCalculator:**
- [x] Rename `op` property → `paid_op`
- [x] Rename `dp` property → `paid_dp`
- [x] Keep `raw_op`, `raw_dp` as-is (already clear)
- [x] Keep `op_of()`, `dp_of()` methods as-is (unit-level calculations)

**View Models:**
- [x] `MilitaryRowVM`: `op` → `paid_op`, `dp` → `paid_dp`
- [x] `RealmieRowVM`: `dp` → `paid_dp`
- [x] `DomMilitaryVM`: `op` → `paid_op`, `dp` → `paid_dp`

**Services & Templates:**
- [x] Update `MilitaryService` usages
- [x] Update `dominfo.html`, `military.html`, `realmies.html`

**Tests:**
- [x] Update test assertions

### Phase 1: Archive Scraping ✓
Scrape BS archive pages and store as standard BarracksSpy objects.
    
- [x] Add `BarracksArchive` class to `ops.py` with `scrape()` method
- [x] Parse archive HTML structure (timestamp, units, training, returning)
- [x] Create BarracksSpy objects from each entry (reuse existing model)
- [x] Handle pagination (`?page=N`)
- [x] Store in database via `update_barracks_archive()` in `updater.py`

### Phase 2: Service & Calculator Split ✓

**MilitaryService** (data retrieval):
- [x] Add `truncate_to_tick(timestamp)` helper in `timeutils.py`
- [x] Add `get_barracks_spies_in_tick(dom, tick_time)` to MilitaryService
- [x] Pass list of BSes to calculator for refinement

**MilitaryCalculator** (calculations):
- [x] Add `refine_unit_estimate(observations)` static method
- [x] Add `refined_home_units(barracks_spies)` method
- [x] Add `current_op(refined_units)`, `current_dp(refined_units)` methods
- [x] Existing `paid_op`, `paid_dp` remain as paid values

### Phase 3: View Model & Template Changes ✓
- [x] Add `current_op`, `current_dp`, `confidence` fields to MilitaryRowVM
- [x] Add `include_current_strength` parameter to facade and service
- [x] Add "Current Strength" checkbox to military template
- [x] Add Cur OP, Cur DP, Conf columns (shown when checkbox enabled)
- [ ] Color code based on confidence (optional, deferred)

## Open Questions

1. **Away units direction**: Current code uses `away * 0.85` (lower bound). Should this be upper bound for consistency with "pessimistic" approach? Need to understand the original intent.

2. **Archive data retention**: How far back does OD keep BS archives? Do we need to scrape frequently to not lose data?

3. **Database changes**: Do we need to store refined estimates, or compute on-demand from raw BS records?

4. **ClearSight accuracy**: ClearSight has a `clear_sight_accuracy` field. Should similar refinement logic apply when accuracy < 1.0?

## Reference: Troll BS Data

Example from manual BS session (multiple observations same tick):

```
HOME (use MIN)                          AWAY (use MAX)
Brute   Basher    Smasher               Brute   Basher  Smasher
428     31682     33991                 52944   11226   8119
450     31154     28443                 47011   13491   8092
379     23648     36699                 52588   11344   8903
...
MIN: 333  23648   27478                 MAX: 52946  13556  8978
```

Ratios achieved (need >= 1.38 for locked):
- Brute: 456/333 = 1.37 (nearly locked)
- Basher: 31912/23648 = 1.35 (good precision)
- Smasher: 36699/27478 = 1.34 (good precision)