# CARE AUDIT — the loop the whole game is made of (2026-07-25)

Joel: "lets do a full blown care audit next."

Scope: the body tick — hunger, calories, weight, effort, filth, sleep,
sickness, injury, the care-mistake economy and the deaths it feeds.  Method
as before: **live the days.**  Real ticks, three regimes, every meter held
against its rails on every tick.

---

## 1. F1 — THE STARVATION DEATH COULD NEVER FIRE  ✅ FIXED

```python
self._starve_t += dt                      # dt is GAME-MINUTES
if self._starve_t >= 12 * 3600:           # ...compared to a real-seconds shape
    self._die("starvation")
```

43,200 game-minutes is **thirty game-days of unbroken starvation**.
Measured: after three game-days held at an empty belly the clock stood at
2,940 while the 20-mistake ladder was already at 13 — so the death it
guards could not happen, ever.

Two things make it a bug rather than a dormant idea: the comment says
"empty hunger 12h → death", and round 41 (F8) deliberately **persisted**
`_starve_t` so quit-cycling couldn't dodge it.  Nobody persists a clock
that cannot fire.

It is **the unit law's fourth instance** (after the vitamin guard, the
fidget cadence and the Grow Capsule) — and the warning for it sits twelve
lines below the bug in the same function.  The number is now
`STARVE_DEATH_MIN = 12 * 60`, on the body's own clock, the same rescale
`FILTH_SICK_BOUND` took ("12000 real-min → /60 game scale").

Measured after the fix: a pet **held** at an empty belly dies at exactly 12
game-hours, cause `starvation`, with 1 care mistake.  A fed belly resets
the clock; a sleeping pet does not starve in its sleep (awake-only, like
the hunger call).  **An attentive player is untouched** — 0 mistakes over
three game-days, no breaches.

## 2. F2 — HUNGER WAS TOO SLOW TO MATTER  ✅ RULED + RETUNED

While measuring F1 I had to answer "how long until a belly is empty?", and
the answer is the bigger finding:

| the hunger clock | game-min | game-days | real play |
|---|---|---|---|
| one calorie lapse | 225 | 0.16 | 4 min |
| one hunger heart (8 lapses) | 1,800 | 1.2 | 30 min |
| **a full belly (4 hearts)** | **7,200** | **5.0** | **2.0 hours** |

Against that, measured deaths by neglect:

- pure neglect (never fed, never cleaned): dies at **3.5 game-days**
- tidy but never fed: dies at **4.6 game-days**

**The pet dies two to three game-days before its belly can empty.**  So in
a natural life, hunger never reaches zero — and everything downstream of an
empty belly is unreachable:

- the **hunger call** (the `!`, the alarm, the care mistake),
- **"Too hungry to fight"** and **"Too hungry to train"**,
- the **starvation death**, even after F1.

Which means: **feeding is optional.**  A pet you never feed once dies of
filth and lights, not of hunger, with hearts still on the meter.

For a game whose whole point is a Bandai V-Pet — where you feed the thing
several times a device-day — that reads wrong.  But the constants are
labelled *"tuipet's tuned pace"* and *"keep ~1800s per hunger heart"*, so
this is a **balance ruling, not a unit slip**, and it is yours.

> ### ✅ RULED — Joel, same day: "yeah retune the hunger, do it"
>
> `CALORIE_DECAY_SEC` is now **tied to the day itself** rather than to a
> loose number: `DAY_MINUTES / (FULL_HUNGER × 2 × CALORIE_LIMIT)` = 45, so
> four hearts × eight lapses is exactly one game-day and the scale can
> never drift out of the day again.
>
> | | before | after |
> |---|---|---|
> | one hunger heart | 1.2 game-days (30 real min) | **0.25 game-days (6 real min)** |
> | a full belly | 5.0 game-days (2 real hours) | **1.0 game-day (24 real min)** |
> | a pet nobody feeds | died at 3.5 days of *neglect*, hearts left | **belly empties at 1.4, starves at 1.9** |
> | an attentive player | 0 mistakes | **0 mistakes, ~3 meals a game-day, never sees an empty belly** |
>
> So the whole chain downstream of an empty belly is live for the first
> time: the hunger call and its `!`, both "too hungry" refusals, and F1's
> starvation death — which is now what actually kills a neglected pet,
> rather than a clock that could never run.
>
> **The sibling clocks followed** — see §2b.

## 2b. THE SIBLING CLOCKS  ✅ RULED + RETUNED (v0.5.258)

Joel, immediately after: *"retune the poop and effort clocks too."*  Both
were left on the old scale by the hunger pass and looked absurd beside a
one-game-day belly.  Both are now expressed against `DAY_MINUTES`:

| clock | before | after |
|---|---|---|
| a poop pile | 1.9 game-days | **0.25 (four a game-day — the device's eat→poop coupling)** |
| an effort heart | 2.1 game-days | **0.33 (three a game-day; gentler than the belly, since a drill is a bigger ask than a meal)** |

**And that exposed the last unfloored weight sink.**  `_do_poop` shed
weight with no base floor — invisible while a pile arrived every 1.9
game-days, ruinous at four a day: at base 40 that is **−16g of pooping
against +3g of meals**, so a pet fed exactly on time still wasted to the
hard clamp within two game-days and wore the **maximum condition penalty
(−0.10 hit chance) for its whole life**.  Every other drain — training,
battles, the march — has floored at the species base since v0.5.204's
weight-floor law; this one never got it.  It has it now.  Real starvation
still wastes a pet below base, deliberately: that branch is the body with
nothing left to burn.

**The difficulty curve, measured across five play styles** (6 game-days
each), because a retune that quietly makes the game brutal is a bad
retune:

| player | outcome |
|---|---|
| perfect | survives · 0 mistakes · weight exactly at base |
| misses 30% of chores | survives · 0 mistakes |
| misses 60% | survives · 0 mistakes · sick 0.1 game-hours |
| misses 90% | survives · 0 mistakes · a little overweight (29 vs 25) |
| **never touches it** | **dies of sickness at 0.42 game-days (~10 real min)** |

That is the shape to keep: **present but sloppy is fine; abandonment
kills.**  It is pinned as a parametrised test, so a future tuning pass that
breaks the forgiving end fails immediately.

## 3. HELD UNDER LOAD

- **The meters never leave their rails** across every regime and day: hunger
  and effort 0..4, energy never over max, weight never under 1, mistakes
  never negative, and the poop pile count always equal to its size list.
- **All four mistake sources fire, exactly once each**: an ignored hunger
  call, filth left standing, lights burning at bedtime, and stuffing a full
  belly.
- **The death ladder holds at both ends**: 19 mistakes lives, 20 dies of
  `neglect`; a late-window Ultimate at 5 dies of `frailty` (the Pen20
  contract).
- **An attentive player keeps a spotless pet** — two game-days of real
  feeding, cleaning, lights and cures leave zero mistakes.

## 4. SHIPPED

- **v0.5.256** — F1, the starvation clock, plus `tests/test_care_audit.py`
  (11 pins).  Suite 2115 → 2126.
- **v0.5.257** — F2 ruled and retuned: a full belly is one game-day.  The
  pins that recorded the broken numbers were superseded in place, which is
  exactly what they were written for.  Suite 2126 → 2127.
- **v0.5.258** — the sibling clocks ruled and retuned (§2b), plus the
  weight-floor law's last sink.  Suite 2127 → 2135.
