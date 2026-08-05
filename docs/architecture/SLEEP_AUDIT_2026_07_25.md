# THE SLEEP AUDIT — 2026-07-25

Joel: *"lets do a full blown sleep audit next."*

Method, as ever: **run the system, don't read it.** Every line below was
measured on a real hatched **line** pet — a bare `Pet(...)` has no
`line_id`, falls back to the legacy pressure model, and never sees the
wall-clock bedtime this audit is about. Probing the wrong fixture would
have audited a code path no player ever touches.

Pins: `tests/test_sleep_audit.py` (41).
Ships as **v0.5.259**.

---

## §1 · S1 (FIXED) — the raid board fought a sleeping pet

The raid gate landed four days ago in the battle audit, reasoning:

> a volley is a fight you CHOOSE, so the body answers first — exactly as
> the home key, both cups and the lobby have always done.

It copied the **body** half of that rule and left the **sleep** half
behind. Measured on the real `RaidPanel` with a standing boss and
attempts left:

```
press SPACE on a sleeper -> msg='Calling the raid gate…'
                            bout launched = True
                            asleep = True      disturb = 0
```

The pet slept through its own raid. This was the **only** fight door in
the game that neither woke the sleeper nor refused:

| door | on a sleeper | wakes | disturb |
|---|---|---|---|
| home battle key (`can_battle`) | "It grumbles awake." | ✓ | +1 |
| both cups (`can_enter`) | "It grumbles awake." | ✓ | +1 |
| training (`can_train`) | "It grumbles awake." | ✓ | +1 |
| adventure | "It grumbles awake." | ✓ | +1 |
| jogress (`can_jogress`) | "It grumbles awake." | ✓ | +1 |
| care pill / bandage / feed | lands, then wakes | ✓ | +1 |
| **raid board** | **fought** | **✗** | **0** |
| lobby invite (`_session_gate`) | "zzz… asleep" | ✗ *(by design)* | 0 |

The lobby is the deliberate opposite and stays that way: a **stranger's**
invite must never touch the pet, because it isn't the player's finger.
Everything the player presses themselves pays the same price.

**Fix** (`raidscreen.key`): the sleeper answers *above* the body gate, so
the first press wakes-and-refuses and the second press volleys — the
exact `can_battle`/`can_enter` shape.

```
press 1 (asleep): 'It grumbles awake.'  bout=False  awake=True  disturb=1
press 2 (awake) :                       bout=True               disturb=1
awake healthy pet: bout=True — the ordinary player pays nothing
```

The body gate the battle audit installed still sits underneath it
(`injured` → "Too hurt to fight.", pinned).

---

## §2 · S2 (DOC) — LINES_SPEC §5 contradicted the shipped device

§5 said a lit sleeper logs *"the once-per-night lights mistake"*. The
device books one **every 120 lit minutes** — measured at 1.48 / 3.48 /
5.48 / 7.48 / 9.48 hours into a lit 10-hour night, gaps of exactly 2.0:

```
mistake hours: [1.48, 3.48, 5.48, 7.48, 9.48]   gaps: [2.0, 2.0, 2.0, 2.0]
obedience changes during that same night: 1
```

The behaviour is canon-derived and deliberate — `_tick_asleep` says so in
a dated comment ("`AfterMistakeMinutesPostponed` is -60, **NOT a latch**…
the obedience ding lands ONCE per night"). So the **contract** was the
wrong half, not the code. §5 now matches the device, and both halves are
pinned so the next reader of that paragraph doesn't "fix" the code to it.

This is the second time this session a *document* was the defect. Worth
naming: the spec is a contract, and a contract that drifts is a trap for
whoever trusts it next.

---

## §3 · Cleared — measured before believed

Five candidate findings died on contact with a measurement.

**"Waking a sleeper costs a care mistake."** It doesn't, and the reading
that suggested it was mine: an early probe fed a **full** sleeper and saw
`mistakes 0→1`. That was the **overfeed** penalty (D2) — the act was
refused and the pet *never woke at all* (`disturb 0→0, asleep=True`). Fed
while genuinely hungry, a sleeper wakes, bills one disturb, and takes no
mistake. The price of a disturb is paid in a different currency:

**The disturb is real currency.** 208 of 1597 corpus forms gate on it
(174 `GreaterThan`, 34 `EqualTo`); it is read by `check()` (hard
pass/fail), `fulfilled()` (score), `deviation()` (tie-break) and the
dossier's "disturbs" row. A pet with disturbs scores strictly higher on a
disturb-gated form and sits further from the threshold. So waking your
pet at 3am doesn't ding your care record — it changes **who it becomes**.

**`battle_condition()` returns `None` on a sleeper.** By design: it is
documented as the *pure* condition half (no disturb, no anim, no refusal
roll) and its callers own the sleep clause. After §1 they all do.

**The night, per form.** Six distinct bedtimes across 814 line members
(20:00 · 21:00 · 22:00 · 23:00 · 24:00 · 00:00 — both midnight spellings
map to minute 0), every one waking at **07:00 sharp**. LINES_SPEC §5
exactly. A 21:00 sleeper sleeps 10.0h on the wall clock.

**A short night isn't a bug.** Lights out *before* bedtime is the
documented shallow daytime doze, and a drained pet dozes back to **half**
a tank (recovery doze, v0.5.191) — measured 0→8 of 16, ending at 22:48,
after which the real night ran 22:48→07:00 and filled it to 16. The
nightly ritual (lights out *at* bedtime) is 10.0h and 2→16. What looked
at first like "the night is cut short" was two correct systems in
sequence.

---

## §4 · Open, for Joel — the two refusal orderings

Not fixed, because both are canon-dated and I'm not inventing a ruling.

The **fight** doors take the sleep clause *above* the body gate, so a sick
sleeper **wakes** to be told it's too sick. The **feed** door takes it
*below*, and `feed_meat` documents the choice outright: *"Feeding a
sleeper DISTURBS it first (refusals don't wake it)."* So:

- press the battle key on a sick sleeper → it wakes, +1 disturb, refused
- press meat on a sick sleeper → it sleeps on, +0 disturb, refused

Both behaviours are pinned as they stand. If you want one law — *"a
refusal never wakes it"* is the kinder one and the cheaper change — say
so and it's a small edit at `can_battle`/`can_enter`.

---

## §5 · Also verified

- **TIME LAW** holds structurally: exactly **one** `self.pet.tick(` site
  in the codebase, and it returns behind `self.mode is not None` with no
  exception — so a pet can neither fall asleep nor wake behind a panel.
  Pinned against a second tick site appearing.
- **The morning note tells the truth about the tank** (v0.5.177). The
  mood roll stays canon; on a good roll the note reads "beaming" at or
  above half a tank and "up — still weary…" below it. A *disturbed* wake
  clears the note, so no stale morning line survives into the day.
- **The item-sleep law** is intact at `petcare.py:482` — music player
  wakes mistake-**and**-disturb-free (its whole point), the cold shower
  runs its own disturb inside so "AWAKE and bracing" can be true, the
  sleeping pill is a no-op on a sleeper, and everything else disturbs then
  applies.
- **The sleep status card** fits its 26-column box under every
  combination probed, including asleep+sick+injured+poop.
- **Hunger drains identically asleep and awake**; a sleeper does not poop.

---

## The ledger

| | |
|---|---|
| defects found | 2 (1 behaviour, 1 contract) |
| defects fixed | 2 |
| false leads cleared | 5 |
| pins added | 41 |
| files touched | `raidscreen.py`, `LINES_SPEC.md`†, `tests/test_sleep_audit.py` |

† `LINES_SPEC.md` is **gitignored** (`.gitignore:45`) — local-only, so the
§5 correction lives on this machine and does not ship with the release.
The behaviour it now describes is pinned in the repo either way, which is
what actually protects it.
