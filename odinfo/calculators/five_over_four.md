# The issue with Five over Four calculations

The five over four rule is documented here: https://wiki.opendominion.net/wiki/Offensive_power

OP = Offensive Power
DP = Defensive Power

## Military Units

There are always four types of military units:

- Spec Offense, always a X OP / 0 DP unit
- Spec Defense, always a 0 OP / X DP unit
- Elite Offense, always a unit with higher OP than DP
- Elite Defense, always a unit with higher DP than OP

## The issue

When we want to calculate what a dominion can maximally send, we need to figure out what the most efficient way is to
achieve the 5/4 amount. But because whenever you send an elite unit both OP increases and DP decreases, the algorithm
is not trivial.

I do not know how to create a good algorithm that efficiently figures out what the 5/4 amount is. I've tried to brute
force it by trying a composition, calculating and then trying to converge to the answer, but that's really slow.

## Notes

- I account for bonuses with the with_bonus=True parameter. This adds the bonus to each individual unit so that the calculation can be done without worrying about it.
- Race.hybrid_units returns the list of hybrid units in order of highest OP to DP ratio to lowest. This means that first we calculate with the most "bang for the buck" and when that's not enough we take the next one.

## The fix I need

I need the method MilitaryCalculator.five_over_four() to work correctly and as efficient as possible.

## Mathematical Solution

### The 5/4 Rule Constraint

The constraint is: **sendable_OP ≤ 5/4 × remaining_DP**

Where:
- `sendable_OP` = total offensive power of units being sent
- `remaining_DP` = defensive power of units staying home + draftees

### Why the Greedy Approach Works

The key insight is that this is a **fractional knapsack problem** where we want to maximize OP while respecting the constraint.

For each unit type, when we send `x` units:
- We gain: `x × OP_per_unit` offensive power
- We lose: `x × DP_per_unit` defensive power from home

The **efficiency ratio** is: `OP_per_unit / DP_per_unit` - this tells us how much OP we gain per DP we lose.

### The Mathematical Formula 

For each hybrid unit type, we need to find the maximum number we can send:

Starting constraint: `sendable_OP + (to_send × OP_per_unit) ≤ 5/4 × (remaining_DP - to_send × DP_per_unit)`

Expanding: `sendable_OP + to_send × OP_per_unit ≤ 5/4 × remaining_DP - 5/4 × to_send × DP_per_unit`

Rearranging: `to_send × OP_per_unit + 5/4 × to_send × DP_per_unit ≤ 5/4 × remaining_DP - sendable_OP`

Factoring: `to_send × (OP_per_unit + 5/4 × DP_per_unit) ≤ 5/4 × remaining_DP - sendable_OP`

**Solution**: `to_send ≤ (5/4 × remaining_DP - sendable_OP) / (OP_per_unit + 5/4 × DP_per_unit)`

### Why Process in Efficiency Order

Since `Race.hybrid_units` gives us units sorted by OP/DP ratio (highest first), we process the most efficient units first. This ensures we maximize the total OP we can send because:

1. **Pure offense units** (ratio = ∞) are sent first - they don't reduce remaining_DP
2. **High-efficiency hybrids** are sent next - maximum OP gain per DP loss  
3. **Lower-efficiency hybrids** fill remaining capacity

This greedy approach is mathematically optimal for this type of constraint because each unit type has a fixed efficiency ratio, and we can send fractional amounts (the algorithm handles partial unit sending via the `partial_amount` parameter).