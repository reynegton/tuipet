# EVOLUTION AUDIT — the charts, end to end (2026-07-25)

Joel: "lets do a full blown evolution audit next."

Scope: the trigger (`_maybe_evolve`), the line charts and their gates, the
corpus graph behind them, the two off-chart doors (DNA divergence, armor
crests), the counters an evolution resets, the DigiCore's promises, and
the album's denominator.  Method unchanged: **raise pets, don't read
charts.**

---

## VERDICT: NOTHING BROKEN — the first clean audit of the seven

Every road I walked ended somewhere real.  So this board is not a fix
list; it is the **measurement**, and `tests/test_evolution_audit.py` (39
pins) is the ratchet that keeps it true.

### What was measured

| check | result |
|-------|--------|
| every egg raised WELL and NEGLECTED (46 × 2 = 92 roads) | no stalls, no placeholder endings |
| well-raised outcomes | 40 Mega · 5 Ultimate · 1 Champion |
| neglected outcomes | 44 Champion · 1 Ultimate · 1 Mega |
| gate satisfiability across 51 lines / 1,151 rows | **no unsatisfiable gate** |
| rule atoms in the data (`cm lv tr win jogress ko6 btl of area`) | every kind has a live handler AND a checklist row |
| counters on evolve | stage counters zeroed, lifetime kept (drills, battles, wins, the Pen20 window) |
| album roster | 1,218 species, zero placeholders, no duplicates |
| DigiCore pages (all 9) | 12×40 exactly — none over |
| the core countdown | never contradicts what's pending |
| DNA divergence | arms, fires, re-anchors to a claiming line, lands off-placeholder, clears its charge |
| armor crests | the landing always comes from the set the shop dossier promised |
| the elder freeze | sits ~184× beyond the whole stage ladder — cannot strand a raiser |

The care gates do their job: the same eggs raised well climb strictly
higher than the same eggs neglected, and neglect parks 44 of 46 roads at
Champion — the Numemon country the design intends.

### Three false leads, written down so nobody re-chases them

1. **`unmet=0` with `ready=False` is not a lie.**  It is the DOOR shape: a
   row whose only road is a fusion, an armor jump or a Field divergence
   reports informationally (`met=None`) — e.g. `· jogress with a
   Vaccine/Free partner` — so it counts as neither met nor unmet, and the
   page *names the road* instead of faking a countdown.  Six of the 92
   roads stop at exactly such a door; all six say so on screen.
2. **`dna_applied` is not emptied on evolve, it is ZEROED.**  The charges
   do clear; the dict keeps its keys, so `if not pet.dna_applied` is the
   wrong test.
3. **A crest's landing looks random** because several armor forms can
   answer one crest (Courage → Boarmon / Lynxmon / Salamandamon).  The
   shop dossier lists exactly that set, and `item_select` never picks
   outside it — pinned.

### The singleton worth knowing about

Exactly **one** row in the entire corpus uses the `AREA` atom —
DoruGreymon → Alphamon, `AREA 3` (adventure map 3 cleared, with the raid
count as the documented fallback).  A one-of-a-kind atom is where an
unhandled kind would hide and silently delete a form from the game; it is
handled in both the checker and the checklist, and a pin now walks every
atom kind the data uses through both.

## SHIPPED

**v0.5.255** — pins and this board only; no behaviour changed, because
nothing needed to.  Suite 2076 → 2115.
