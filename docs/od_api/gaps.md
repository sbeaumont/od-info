# What we cannot see today

The site shows a player these things; a scraper cannot get at them, or cannot get at them
reliably. Ordered by how much each one distorts what OD Info tells its user.

## Wrong numbers

**Wonders.** Which realm holds which wonder is public knowledge in the game and invisible
to a tool, so nothing in OD Info reads `wonders.yml` at all. The combat perks in there are
realm-wide: Obelisk of Power (+5 OP, +5 DP), Lair of the Dragon (+10 OP, +5 DP), Great
Wall (+10 DP), Monument of Protection (+5 DP), Temple of the Damned (`enemy_defense` −5).

All five are `active: false` in the data we mirror today, so the error is latent rather
than live. That is exactly what makes it worth raising: the day one of them is switched
back on, every tool is quietly wrong about every dominion in the holding realm, in the
same direction, for the rest of the round, and nothing in what a tool can see would tell
it. Wonder ownership plus an authoritative active flag closes it for good.

**Fuzz we cannot see.** Barracks spy numbers are fuzzed by a factor we hardcode as 0.85.
Spire of Illusion (`clear_sight_accuracy: 85`, also inactive at the moment) would fuzz
clear sight as well, and a tool has no way to know it happened — so those readings would
be presented as exact, with no warning, which is worse than presenting them as a range.
Accuracy stated per observation makes this the server's business instead of every tool's
guess.

**Heroes.** `heroes.yml` lists combat perks (`combat_defense`, `combat_evasion` and
friends) but a dominion's hero and its level are not visible, so none of it is applied.

**`???` is not zero.** The barracks archive prints `???` for a value the spy did not
reveal, and HTML gives us no way to keep that distinct from `0` once parsed. We currently
store zero, which quietly understates a dominion's army.

## Fragile plumbing

**Town Crier as prose.** Nine event types recovered from English sentences with regular
expressions. Any rewording upstream turns real events into `other`, silently, and the tool
keeps running with a hole in its history.

**The barracks spy archive as paginated HTML.** Historical observations of the same tick
are what let a tool narrow the fuzz range honestly, and getting them means walking pages
of `div.box-primary` blocks, reading timestamps out of the sentence "Revealed … by …", and
counting tick columns by position.

**No change feed.** The OP Center index says a dominion has *something* newer; it does not
say what, so the only way to find out is to fetch the whole dominion again. And the Town
Crier has nothing of the sort at all, so a refresh re-reads the entire round.

**Backfill ordering.** Intel gathered by a realm member can become visible to us long
after the tick it describes. Nothing on the site exposes when a record became visible, so
a client that syncs on observation time will miss records that arrive late.

**Reference data from a branch, not from the server.** We mirror `app/data` from the
`develop` branch on GitHub and hope it matches the running round. Nothing tells us whether
it does.

**Numbers the game does not publish.** Roughly twenty-five constants — population per
building, build ticks, the masonry multiplier, the guard tower, gryphon nest and temple
factors with their caps, the six improvement curves, the networth weights, boats per dock,
the barracks spy fuzz — live in a file we maintain by hand and that goes stale silently
after a balance change.

**Naming.** The search page says `Dark Elf`, the race file is `darkelf.yml`, and
`spells.yml` keys the same race `dark-elf`. Every tool writes its own bridge between
those, and every bridge breaks on a race whose name has an apostrophe or a second space.

## Friction the user carries

**Who am I.** The player looks up their own dominion id by hovering over their name in the
search page, and types it into a configuration file. A session that can tell a tool which
dominion it is playing removes the single most common setup mistake.

**What time is it.** The server clock is a `title` attribute in the page footer, and the
round day and tick are two `<strong>` tags inside it. Because that is fiddly, OD Info also
ships a `LOCAL_TIME_SHIFT` setting the user has to work out for themselves by comparing
their own clock with the game's.

**Is the round over.** When a round ends, the day and tick disappear from the footer. A
tool cannot tell that from its own scraper having broken, so it reports a malfunction to
its user instead of "the round has ended".
