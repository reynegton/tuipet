# TRAINING AUDIT — the drill, end to end (2026-07-25)

Joel: "lets do a full blown training audit next."

Scope: the drill screen (the timing bar, the strike show, the verdict),
`train_result`'s ledger, the grading rule it shares with battles, the
window care widens, and the door that decides who may drill at all.

**Verdict: the drill is sound. Its DOOR was not — and the same root reached
two more surfaces.**

---

## 1. THE FINDING — one ailment, half the doors  ✅ FIXED

Injury came back on 2026-07-23 and was taught to `battle_condition`: a
wounded pet cannot fight, at home, in a cup, in the lobby, and (since
yesterday's ruling) at a road boss gate or a raid.  **Three places never
learned it**, and together they made the wound almost weightless:

| door | before | now |
|------|--------|-----|
| `can_train` | a hurt pet drills freely | "Too hurt to train." |
| `needs_care()` | injury raises **no** call | it calls, like sickness |
| the HUD's hurt line | "**I** — a Bandage from the bag" | "**F** — patch it up" |

**Why the alarm was silent.**  The canon restoration said the wound "rides
the same care-alarm cascade as sickness", and wired it into
`_alarm_urgency` — but that function only decides how LOUD an
already-triggered alarm rings.  The trigger is `needs_care()`, which never
learned the second ailment.  So a pet that was *only* hurt rang nothing,
raised no `!`, and never reached the HUD line written to name its cure:
**the alert existed and could not fire.**

**Why the line was wrong.**  When it did fire — because the pet was also
sick or starving — it sent a panicked tamer to the BAG for a Bandage that
the items refactor moved to the free F menu (R3, 2026-07-23).  That is the
identical bug v0.5.178 fixed for the pill, sitting on the very next line,
made wrong two days later by an unrelated arc.

The net effect: "too hurt to fight" meant "go do timed strike drills
instead", with nothing on screen asking you to patch the pet up.  All three
now agree, and the cure is one key away and free.

## 2. THE DRILL ITSELF — measured, and clean

- **Fits the box.**  Both states (bar, shoot) render 12×40 exactly.
- **Cannot be frozen.**  Driven at every press rate including a
  frame-by-frame mash, the drill finishes in the same 58 frames — the
  battle-freeze class does not exist here.
- **The ledger is what it advertises**: energy −2, weight −2 (floored at
  the species base, holding over 20 straight drills), effort +1 win or
  lose, and +1 on BOTH training clocks — stage (the TR evolution gate) and
  lifetime (the hit formula's +20% term).  A miss trains too; only the
  praise window and the pose differ.
- **The bar is honest and care widens it.**  A neglected pet's mega zone is
  3px — 300ms at the marker's step, the human minimum the 2026-07-23
  timing rework floored it at — and a well-kept one gets 5px.  Every
  position on the bar grades to something sane.
- **One grading rule with the bout.**  The drill and the fight both call
  `strikefx.grade_lock` with `battlescreen.mega_window`, so practised
  timing means the same thing in a real fight.

## 3. NOTED, NOT TOUCHED

The **AI assistant** cleans, feeds, tops effort and kills the lights.  It
cures sickness in passing (its tonic is the pill) but has no bandage act,
so a hired helper will not patch a wound.  Teaching it one is a new
assistant behaviour — a design call, not a wiring fix — so it stays on this
board until Joel rules.

## 4. SHIPPED

**v0.5.254** — the three-door fix plus `tests/test_training_audit.py`
(13 pins: the ailment agreement across doors, the alarm trigger, the
cure's key, the mash, the box, the ledger, the weight floor, the shared
grading rule).  Suite 2063 → 2076.
