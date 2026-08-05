# BATTLE AUDIT — every door into one engine (2026-07-25)

Joel: "we gotta do a full blown battle audit. we did a bunch of changes
recently and we gotta make sure its hooked up correctly."

The recent run touched combat from six directions: the home battle key
(v0.5.198), the Pen20 lock rework (199-204), injury (205), the rolling win
gate (212), the one-card rule (179), death-is-final (180) and the cup's
single entrance (240).  Scope of this audit: every SOURCE of a fight,
walked from its gate through the engine to the ledger and the card.

**Verdict: the wiring is right — one real bug, one ruling for Joel.**  The
bug is not in the maths; it is in the keys, and it is the kind a phone
player hits every single fight.

---

## 1. THE MATRIX (measured, not read)

| door | gate | energy | weight | battles / log | wins·exp·KO6 | purse | card |
|------|------|--------|--------|---------------|--------------|-------|------|
| home **m** | `can_battle` | −5 | −4, floors at base | ✔ | ✔ | none | battle |
| road wild | *(none — see §3)* | −5 | ✔ | ✔ | ✔ | bounty | battle |
| road boss | *(none — see §3)* | −5 | ✔ | ✔ | ✔ | bounty | battle |
| cup bout | `can_enter` + `battle_condition` | −5 | ✔ | ✔ | ✔ | trophy purse | battle |
| town cup | `can_enter` + `battle_condition` | −5 | ✔ | ✔ | ✔ | purse | battle |
| raid volley | attempts only | — | — | **nothing** | — | server | battle (pool) |
| lobby PvP | `can_battle` / `battle_condition` | −5 | ✔ | **nothing** | **nothing** | server | battle |

Everything in that table was produced by running the real engine and
diffing the pet, not by reading intentions.  The two "nothing" rows are
the L17 ruling (online is progression-neutral) and the raid's report-not-
a-bout rule, both holding exactly as written.

## 2. F1 — THE HURRY KEY RAN THE FIGHT BACKWARD  ✅ FIXED

`BattlePanel.key`'s skip branch jumps the playhead to `first`, the START
of the closing impact run, so you still SEE the hit you hurried to.  It
never checked whether the playhead was already past that point — so a
press made mid-run **snapped it back**, and a press every frame snapped it
back every frame.

Measured on one bout (same seed, same fight):

| input | frames to finish | rewinds | outcome |
|-------|------------------|---------|---------|
| no presses | 647 | 0 | round 6 |
| press every 10 frames | 162 | 0 | round 6 |
| press every 3 frames | 83 | 0 | round 6 |
| **press every frame** | **never (4000+)** | **3953** | **stuck in round 1** |

The faster you pressed, the slower it went; mash it and the fight simply
stops — the bars freeze mid-round with the pet standing there.  **Joel
plays on a phone**, where tap-tap-tap is the normal way to hurry a beat,
and the QOL round that built this branch was itself about making skip
presses land (v0.5.187).

Fix: `self.i = max(self.i, first)` — a hurry key may only ever hurry.
After it, mashing is the FASTEST way to finish (62 frames) and the outcome
is unchanged, because the rounds are precomputed at the lock.

This is one code path serving every door, so the fix lands on the home
bout, both road fights, both cups, the raid volley and the PvP replay at
once.

## 3. THE ONE RULING — the road never asks the condition gate

`battle_condition` is THE source, and it answers for five states.  Which
doors ask it, measured:

| state | home **m** | cup / town cup | lobby | **road wild + boss** | raid |
|-------|-----------|----------------|-------|----------------------|------|
| injured | "Too hurt to fight." | ✔ | ✔ | **fights anyway** | fights anyway |
| sick | "Too sick to fight." | ✔ | ✔ | **fights anyway** | fights anyway |
| starving | "Too hungry to fight." | ✔ | ✔ | **fights anyway** | fights anyway |
| drained | "Too drained to fight." | ✔ | ✔ | **fights anyway** | fights anyway |
| filthy | "Clean up first!" | ✔ | ✔ | **fights anyway** | fights anyway |

For an AMBUSH this is deliberate and right — you cannot decline a pounce,
and the energy grammar has the same carve-out.  The open questions are the
CHOSEN fights that share the carve-out by accident:

- a road **BOSS** is walked into on purpose, at a gate, with a prompt;
- a **raid volley** is chosen from a menu;

...and both let an injured pet fight while the shelf, the alarm and the
home key all say "Too hurt to fight."  That was P5 on the REAL VPET board
("'too hurt to fight' isn't literally true"), still unruled, and it is
wider than injury.

> ### ✅ RULED + SHIPPED v0.5.246 — option (b)
>
> Joel, same day: *"tuipet is its own game, supposed to feel as close to
> bandai vpet as much as possible, so anything else is extra and need
> something smart to build it."*  That settles it by principle rather than
> by taste: **`battle_condition` IS the device's battle button asking
> whether this body can fight.**  Adventure and raids are tuipet's own
> extras, so they answer to the device wherever the PLAYER chooses the
> fight — and only there.
>
> * the road **BOSS gate** asks the body; refused, the pet STANDS at the
>   gate wearing the reason ("Too hurt to fight. · T warp · ESC home")
>   instead of being marched in.  Pressing SPACE re-asks.
> * the **raid volley** asks the body; refused, the board says which, and
>   the attempt is not spent.
> * the **wayside ambush** keeps its carve-out and is now PINNED as the one
>   exception: you cannot decline a pounce, and the energy grammar has
>   always had the same hole in the same place.
> * a refused gate is never a dead end — ESC home always works, and a held
>   transport still opens the warp menu (the same honest outs the
>   planted-on-the-road refusal offers).

**The options as they stood:**

- **(a) leave it** — the road is the road; only chosen HOME fights gate.
  Then the injury alert's wording should soften ("too hurt for the ring").
- **(b) gate the road BOSS and the raid** (chosen fights), leave ambushes
  ungated — the most consistent with how the town cup already behaves.
- **(c) gate everything on the road**, ambushes included — simplest to
  explain, but it turns a wandering injured pet into a stranded one.

My read: **(b)**.  It matches the existing town-cup behaviour on the same
road and keeps the ambush carve-out that the energy grammar depends on.

## 4. VERIFIED CLEAN (with the evidence, so nobody re-audits it)

- **The lock reaches the fight and is pure upside.**  `saved_hit_type` is
  written at the lock and read by `Side.of_pet` for the fight built one
  line later; mega = +0.10 aim and −0.10 on the foe's roll (0.633 vs
  0.400 measured), and **normal and miss score identically** — a shank
  costs nothing, as the Pen20 shake ruling says.
- **The drill and the bout share ONE grading rule.**  Both call
  `strikefx.grade_lock` with `battlescreen.mega_window`, and both build the
  latency-grace history the same way, line for line.
- **The bar arms before it accepts a lock** (LOCK_ARM_T): the very first
  press after the bar appears is swallowed, including on the cup's
  `skip_intro` path, which starts ON the bar.
- **Death is final within a round** — a foe dropped to 0 by your volley
  never returns fire; NPC bracket matches coin-flip initiative so list
  order grants no edge.
- **The weight bill floors at the species base** — 30 bouts in a row leave
  a pet exactly at base.
- **The cup ramp reaches the fight**: QF a fresh wild, SF (250, 2500, 40,
  25), Final (500, 5000, 80, 55), attached through `e["side"]`, which
  `Battle` prefers over a species Side.
- **One card, every door** — `painter_for` walks `mode.sub`, so a fight
  hosted inside the cup, the road or the raid paints the same battle card;
  the raid shows the community POOL and a 10/10 tank from its first frame.
- **The outcome does not depend on input speed** (precomputed at the lock)
  — now pinned, because that is what made F1 a freeze instead of a cheat.

## 5. LOOKED AT, LEFT ALONE (named, not touched)

- ~~**A bout feeds `stage_trainings` (+2) but never `total_trainings`.**~~
  → **FLIPPED v0.5.247** (Joel: "feed the total_trainings thing too, flip
  it").  Fighting fed the TR evolution gate and the hit formula's +10%
  stage term while the bigger +20% LIFETIME term sat still no matter how
  much a pet fought; a bout now pays both, at its own +2 rate (the drill
  keeps its 1:1).  The DigiCore row was renamed **Drills → Training** the
  same hour: a row named for one of its two sources is a row that lies
  about the other (the liveness law).
- ~~**`BattlePanel`'s `source="pvp"` branch is dormant**~~ → **CUT
  v0.5.248** on Joel's named order.  Nothing has ever set a `pvp` key on an
  enemy dict, so the test could not be true; a lobby duel never reaches
  that line at all (the lobby builds the panel as a presentation-only
  REPLAY and files its own bout with `record_battle(online=True)`).  Every
  fight born at the timing bar is local, and a pin now says so.

  ~~**Kept on purpose:** `Battle`'s own `source` parameter and
  `record_battle`'s~~ → **ALSO CUT v0.5.249**, on Joel's follow-up order.
  The reasoning that kept them was sound but the conclusion was one step
  short: the guarantee they protected does not live in the `source`
  spelling, it lives in **`online`** — the door the lobby, the only caller
  that ever fights online, has always used.  Two spellings for one rule
  are two places for it to drift; there is one now.  `Battle` is a LOCAL
  bout by construction (nothing ever built one otherwise), and
  `test_pvp_megas_are_not_farmable` pins the same guarantee on
  `online=True`, plus its mirror — a local bout against the same Mega
  DOES count — so the pin can no longer pass by simply counting nothing.
- ~~**The pre-fight readiness line builds its own foe**~~ → FIXED
  v0.5.246: it reads `enemy["side"]` first, exactly as `Battle` does, so
  the card and the fight can never describe two different creatures (a cup
  opponent carries a RAMPED Side, a lobby peer its relayed card).

## 6. SHIPPED

- **v0.5.245** — F1 (the hurry key) plus `tests/test_battle_audit.py`
  (22 pins: the hurry key at four press rates, the five-door ledger
  matrix, the gate, the lock, the card).  Suite 1967 → 1989.
- **v0.5.246** — the §3 ruling: the device's gate on every chosen fight
  (road boss + raid volley), the ambush carve-out pinned as the one
  exception, and the readiness line reading the fight's own foe.  12 more
  pins; suite 1989 → 2001.
- **v0.5.247** — a bout trains on BOTH clocks (§5's first item, flipped by
  Joel), and the DigiCore row renamed to Training.  Suite 2001 → 2003.
- **v0.5.248** — the panel's dead PvP selector cut (§5's second item).
  Suite 2003 → 2004.
- **v0.5.249** — the `source` parameters cut from `Battle` and
  `record_battle` too; `online` is the one door to the online rules, and
  the anti-farm guarantee is re-pinned there with its mirror.  **§5 is now
  empty: every item the audit named is ruled, flipped or cut.**
