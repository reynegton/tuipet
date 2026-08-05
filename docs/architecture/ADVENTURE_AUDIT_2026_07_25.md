# ADVENTURE AUDIT — the road, end to end (2026-07-25)

Joel: "lets do a full blown adventure audit next."

Scope: the run model (`adventure.py`) and the road screen
(`adventurescreen.py`) — the march, its drain, encounters, hazards, finds,
towns, transports, the gate boss, progression, the purse and every state
the panel can be in.  Method: **run the road**, hundreds of times, and hold
its own claims against it.

**Verdict: the road is sound, and my own change broke its endgame.**  The
engine's invariants held across every run I threw at it; the two findings
are a regression I shipped yesterday and a 500b item that quietly stopped
being what it says.

---

## 1. F1 — THE BOSS GATE REFUSED EVERY HONEST RUN  ✅ HOTFIXED v0.5.250

Yesterday's battle-audit ruling gave the road's boss gate the HOME door's
condition check.  It took the energy clause with it, and **a march arrives
drained by design**: 40 legs cost 10 energy, ~8 wild fights cost 5 apiece,
against a tank of 24.

Measured the moment the soak ran:

| boss-gate arrivals | 86 |
|---|---|
| energy: min / median / max | 0 / 0 / 7 |
| under `BATTLE_MIN_ENERGY` (10) | **86 of 86** |
| `battle_condition()` said | "Too drained to fight." — every time |

The zone's whole point was unreachable, and it was live on PyPI for a day.

The road already had a ruling on exactly this, older than mine: the
adventure energy audit's **D3** (2026-07-23).  A spend floors at 0,
**fighting on empty is allowed** and billed through the hit formula's
condition term, and only a hazard KNOCK pushes past empty to plant the
feet.  I put a home rule on top of a road rule without measuring it.

`battle_condition(check_energy=True)` now takes an explicit flag, and the
road's gate is its only caller with `False`.  Everything the DEVICE
refuses for — starving, sick, hurt, filthy — still stops a pet at the
gate, which was the ruling's actual point.  The home key, the cup and the
raid keep the energy clause: a pet at home has a bed, a shop and a larder
within reach.

> **LESSON, recorded:** a gate is a measurement, not an opinion.  I
> reasoned about which fights are "chosen" and never asked what the body
> looks like when it arrives.  One soak line asked.

## 2. F2 — THE TOWN TRANSPORT PAST THE LAST TOWN  ✅ FIXED

Every zone carries **exactly one** town span (26 zones, 26 towns).  The
warp targeted `town_legs[0]` and moved forward only, so past that span it:

- spent the 500b ticket,
- rested the pet where it stood,
- announced *"Warped to a town — rested up."*,
- and left it on open road — no hub, no shop, no visit-or-walk-on choice,

which is precisely what v0.5.196 promised it would stop doing.  And *late,
drained, past the town* is exactly when a tamer reaches for that ticket.

Fixed on the pattern already in the file: `held_transports()` hides the
Life Recovery at full hearts, so it now hides the Town Transport when no
town lies ahead, and `use_transport` refuses defensively.  The ticket is
kept, and the planted-feet strip stops offering "T warp" when there is
nothing to warp to.

## 3. HELD UNDER LOAD (the invariants, run not read)

Across 200+ full runs spanning the whole 26-zone road:

- **lives** stayed in 0..3, **loc** in 0..total, the **streak** never
  exceeded its own best;
- **the weight floor held** — the march never ground a pet under its
  species base;
- **the effort cap held** — walking tops the gauge at 4, never past;
- **every find resolved to a catalog key** the bag can show and use;
- **the town rest** fills to at least half a tank, restores all three
  lives, breaks the chain, and fires exactly ONCE per town span (the
  `_resting` latch);
- **progression is monotonic**: only the frontier advances the road, a
  replay advances nothing, an out-of-order conquest advances nothing, and
  the last zone clamps;
- **`pet.away` is transient by construction** — a bare attribute every
  reader takes with `getattr(..., False)`, so a quit mid-run cannot leave
  a stale "away" behind.

Run endings over 200 runs at a realistic win rate: 111 conquered, 40
planted feet (spent past empty), 25 lost on lives, 24 lost at the gate — a
curve with real tension and no dead ends.

**Difficulty, measured against how the pet was raised** (win rate vs the
early zones' own wild pools):

| the pet | zone 1 | zone 2 | zone 3 | zone 6 |
|---|---|---|---|---|
| fresh Champion, never drilled | 72% | 55% | 69% | 65% |
| 50 drills | 72% | 56% | 70% | 66% |
| 200 drills + a 20-fight record | 76% | 62% | 72% | 68% |
| 500 drills + a mega lock | 96% | 94% | 95% | 94% |

The lock is the lever, exactly as the Pen20 ruling intends; drills nudge.
Nothing here needs changing — it is recorded so the next balance question
starts from numbers.

**Every road state renders inside the arena** (12×40) with its own hint
line: march, glint, ambush warning and lunge, town prompt, town rest, life
recovery, the gate (knocked back AND refused), the warp menu, the summary,
the pulse and the parade.

## 4. SHIPPED

- **v0.5.250** — F1, the hotfix (pins in `test_battle_audit.py`).
- **v0.5.251** — F2 plus `tests/test_adventure_audit.py` (18 pins: the
  warp, the invariants, the town rest, progression, and a render sweep of
  every road state).
