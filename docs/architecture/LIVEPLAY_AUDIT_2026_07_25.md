# LIVE-PLAY AUDIT — 2026-07-25

Joel (overnight order): *"make a couple agents to live play the game and
report bugs back to you. audit polish harden."*  Three QA personas played
headlessly — THE DILIGENT CARETAKER (full lifetimes, neglect, elders,
generations), THE CHAOS PLAYER (~40,000 fuzzed keys over ~30 panels,
verb abuse, ~230 poisoned saves), THE ECONOMY GRINDER (flips, cups,
estates, forged rows).  Every report was re-verified with evidence before
any fix.  Shipped v0.5.264; pins in `tests/test_liveplay_audit.py` (40;
33 verified to FAIL on the old code).

## L1+L2 — The poisoned-save gate had holes  ✅ FIXED (chaos player)

`load()`'s contract is .bak → quarantine → "Starting fresh", never a
raise (a load crash is a crash LOOP — the .bak holds the same poison).
But two migrations ran BEFORE any type check: the manners heal
(`float(obedience)`) and the wager settle (`dna_wager_pending > 0`)
raised straight out of `load()` on a string — boot crash.  And the
13-field wrong-type list missed ~20 fields (`stage_seconds`, `calories`,
`gift_t`, `tourney_alarm`, `adv_progress`, `town_bought`, ...) whose
poison loaded "fine" and crashed on the first tick or first render.

**Fix, both levels**: a GENERIC type gate over `fields(Pet)` — every save
value must match its dataclass default's shape, checked before the
migrations; one sweep, no list to forget.  Plus the belt: `load()` wraps
`pet_from_save`, so anything that slips a future gate still lands in the
fallback chain.  (Documented pre-gate heals — `egg_type`, `_lights_t` —
keep healing.)

## L3 — The filth-sickness scaling was never wired  ✅ FIXED (caretaker)

`_filth_effects`' docstring promised "chance × piles vs the bound × the
species multiplier", but the roll actually shipped as a flat
`SICK_POOP_P = 0.015/min` in `_tick_mortality`: `FILTH_SICK_CHANCE`/
`FILTH_SICK_BOUND` sat unreferenced and 232 species'
`PoopSickChanceBoundMultiplier` was parsed and never read.  Player-felt
symptom: one unanswerable ~3am desperate pile → ~97% sick morning after
flawless care (measured: sick on 17 of 24 pile-nights).

**Fix**: the roll moved home to `_filth_effects` with the documented
shape — per game-min, `piles / (200 × mult)`.  Measured across every
multiplier row: one overnight pile now 49–74% by species (was 97%), a
4-pile sty stays punishing (90–100%), and at the 3-pile mess the old
flat rate matches exactly.  The overweight roll stays in mortality; the
road shield (countFilth=0 away) survives.  `FILTH_WORSE_CHANCE` stays
UNWIRED on purpose — the DSprite sickness ruling is one flag, "no
worsening".

## L4 — The town cup reopened the cup-hour farm  ✅ FIXED (grinder)

The home board's rule — "the cup RUNS once per hour" — exists to close a
"~1,500b a minute" purse farm.  `Tournament.__init__` burns the pet's
cup-hour slot on EVERY entry, but the town door never checked it.  And
adventure marches park the world clock (TIME LAW) with pre-bell flees
free, so a march-and-flee loop re-entered the town cup every arrival.
Measured: **100 consecutive cups, +47,632 bits, 0.0 game-seconds**.
Each entry also silently killed that hour's home cup — the slot was
spent but never checked, wrong in both directions.

**Fix**: the town door checks the shared slot.  One slot, both doors;
the next main-view hour re-opens it (cadence, not a shut door).  The
title-defense purse (×1.5, veteran field, flat stake) is AUTHORED
("its your call on the purse", 2026-07-21) and now bounded by the hour —
the rationed bucket, left alone.

## L5 — The rationed counter trusted the caller's row  ✅ HARDENED (grinder)

`town_buy` honored the entry dict it was handed: a stale row replayed
after the ration was spent oversold the deal, and a forged `price`
underpaid.  No key reaches it today (the UI rebuilds rows per keypress) —
hardened because any future caching caller would mint discounted stock.
**Fix**: the one counter door re-fetches the LIVE row from its own
builder and buys that; forged/stale `left` and `price` both die.

## Verified clean by the personas (no action)

- Careful life to Mega on schedule, 0 mistakes, stats in range every tick;
  neglect → rescue resets every timer; elder flip at exactly 15 days;
  estate inheritance intact (incl. int-keyed trophies_won, digimemory
  exclusion, legacy headstone).
- Zero panel crashes and zero over-wide lines in ~40,000 fuzzed keys;
  verb abuse all soft-refused; wallet never negative; save roundtrip
  faithful; unknown/negative nums handled.
- No money printer in the shops (exhaustive home/town × deal/festival
  scan); rations enforced through the UI; egg-re-roll pump confirmed dead;
  no estate dupe window; DNA lab sound; gift faucet negligible.

## Noted, not actioned

- Lobby/PvP and raid purses are server-authoritative — headless probes
  can't reach the relay; the `online_reward` 100b loss-purse remains
  untested for collusion farming (would need a live lobby soak).
- The filth-sick residual: even scaled, a mult-1.0 species that drops a
  3am pile wakes sick ~2 nights in 3.  That's canon's own constants
  (12000 real-min bound /60); tuning it gentler is Joel's call, not mine.
