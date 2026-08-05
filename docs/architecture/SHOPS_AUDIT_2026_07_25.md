# THE SHOPS AUDIT — 2026-07-25

Joel: *"lets do a full blown shops audit next."*

Method, as ever: **run the economy, don't read it.** Everything below was
measured by driving `shop.py`, the panels and the ledger — 26 town
counters, 44 catalog goods, 41 digitama, a year of deals.

Pins: `tests/test_shops_audit.py` (32).
Ships as **v0.5.260**.

---

## §1 · S1 (FIXED) — the shop read differently on every launch

`wave_status` picks the closest sealed Digimental wave to tease. It did
it with `max(set(sealed), key=ratio)` — and that walks a **set**, so when
two waves tie on ratio the winner falls out of string-hash iteration
order, which Python randomises **per process**.

Measured across seven `PYTHONHASHSEED` values, one identical save:

```
seed=0    -> 'wins 0/25 wake Light & Kindness'
seed=2    -> 'generation 0/5 wakes Destiny'
seed=3    -> 'wins 0/25 wake Light & Kindness'
seed=42   -> 'generation 0/5 wakes Destiny'
```

Same pet, same progress, different shop — decided by nothing but process
startup. **7% of sampled progress states sit on such a tie** (any player
at gen 5+ with no armor evo and no wins is in one).

This breaks a law the rest of the shop keeps carefully: a shop's
character is *stable*. The guest good is crc32-ordered so "a town's
character stays permanent"; the daily deal is fixed for the day. The
tease was the one consumer reading raw set order.

Ties now break toward the **nearest goal** (smallest `need`) — which is
also the more useful line: *"your 1st armor evo wakes the crest 5"* beats
*"wins 0/25"* when both are equally far off.

Pinned the only way this bug can be pinned: across **real subprocesses**
with different hash seeds. Verified the pin fails against the old code
(it reports both variants) before trusting it — and the same pin now
guards the town deal, the guest good, the egg bands and the home deal as
a class.

---

## §2 · The anti-printer law, measured at the right yardstick

This is the part of a shop audit that matters, so it got the most
measurement — and it is where I nearly shipped a fix to a system that had
already been ruled on.

**What looked wrong.** All 8 attribute chips sit at exactly the home flip
(50% of catalog) while a town that doesn't stock a good pays **DEMAND at
70%**. That reads as a standing money loop needing no deal and no timing:

```
omni_chip_g   catalog 8000b  town base 4000b  demand pays 5600b  -> +1600b/unit
vaccine_chip  catalog 1500b  town base  750b  demand pays 1050b  -> + 300b/unit
...8 goods, in 9-14 towns each
```

The shipped guard, `test_no_town_price_undercuts_the_home_flip`, only
checks `base_price >= home resale` — the chips sit exactly **at** that
line, passing a test aimed at a weaker yardstick than the one the towns
actually pay.

**Why it is not a defect.** The F5 ruling (item sweep, 2026-07-24) already
settled this class: a profitable flip is fine **if it is rationed** —
that is what turned the home deal from a printer into a treat. Measured,
every one of these flips is:

```
omni_chip_g     legendary  tier_stock=1  -> town sold 1 in a day
vaccine_chip_g  legendary  tier_stock=1  -> town sold 1 in a day
anti_evo_chip   uncommon   tier_stock=2  -> town sold 2 in a day
```

Bounded is the whole law. So the pin this audit adds is not a price rule
— it is the **general** one, which is what was actually missing: *walk
every town's every row; for any good that resells above its shelf price
anywhere, prove the counter parts with a finite number in a day.*

**And the scale is honest.** A 26-town sweep suggests a "+68,170b/day
perfect trader" (+148,170b on a festival), but there is **one town per
adventure zone** — one run reaches one counter, and selling needs a
second run. The reachable number per visit:

| | |
|---|---|
| profit per single town visit | **+1,300b** min · +1,700b median · **+5,400b** max |
| working capital it needs | ~6,500–7,750b |
| for scale: a road boss bounty | 100–3,000b |
| a wild kill | 0–1,000b (avg cap ~91b) |

A side channel worth roughly a good boss, gated behind capital and two
runs. That is a trade game, not a printer.

---

## §3 · Verified clean

Everything here was driven, not read.

- **The gates hold in both shops, exactly on their thresholds.** 0 maps →
  nothing gated on sale; 1 map → both transports; 2 maps → Life Recovery
  joins. A sealed Digimental reaches **no** shelf at a fresh save (9 of
  11 sealed), while `entry()` still resolves one you own so the bag can
  render it.
- **Nothing is stranded.** All 40 priced goods are sold somewhere across
  the 26 counters plus 40 days of home deals.
- **The daily ledger holds.** Hammered, one town sold 14 units across 10
  goods and nothing exceeded its cap; one town's ledger never empties
  another's shelf; it survives a save round-trip and sweeps at midnight.
- **The home deal's F5 fix still works end to end** — 3 cut-price copies,
  then the one-press guard eats the next ENTER (*"deal's gone — ENTER
  again for 300b"*), then full price without limit, where no counter in
  the game pays more. The bag's `_retarget` guard likewise refuses to
  sell the neighbour when a stack empties under the cursor.
- **Deals rotate honestly.** 2,166 town-days sampled: exactly one deal a
  day, **never** the same good two days running, always half price. The
  only exceptions are the 4 festival days, which put the whole counter on
  sale by design.
- **The egg market is clean.** All 41 earnable digitama are covered
  across the towns, no town stocks a dupe, no two towns share a band, an
  egg is bought once, costs real bits, refuses a broke tamer, and cannot
  be flipped through the item sell path.
- **Every authored table resolves** — map specialties, road-only keys,
  adventure gates, own-flow keys and all 13 legacy aliases point at real
  catalog entries. All 44 entries are well-formed and every category has
  a tab.
- **Every panel renders inside the LCD.** Home shop, bag, four town
  counters, two egg counters and a bag holding all 44 goods, each driven
  through a key walk: 0 rows over 12, 0 lines over 40, no markup faults.
  Every dossier fits its four 26-column rows in both modes, with the
  effect text surviving rather than being clipped.
- **The purse never breaks.** Exact change buys; one bit short refuses
  and charges nothing; selling what you don't own refuses.

---

## §4 · Three probe errors worth recording

All mine; the first two would have become false findings, and the third
broke a test in a neighbouring file:

1. **I probed `shop.buy()` and concluded the home deal never reverts to
   full price** — F5 regressing. It doesn't: the ration is written by
   `town_buy()`, which is what the screen actually calls for a deal row.
   Same shape as the sleep audit's `battle_condition` slip: *knock on the
   door the player uses.*
2. **I read "3 goods stranded, sold nowhere"** from a probe that passed
   `pet=...` while the gate reads **global** progress via
   `persistence.get_progress()`. Driving real progress showed full
   coverage.
3. **My own new pins polluted the suite.** `shopscreen._LAST_POS` is
   module-level session memory (the home shop reopens where you left
   it), and parking cursors on tabs left it pointing at Titles — so
   `test_status_box_sweep::test_shop_and_bag_cards` opened on a title
   card and failed. It passed alone and failed after my file: the
   signature of shared state, not of a real defect. An autouse fixture
   now saves and restores it.

---

## The ledger

| | |
|---|---|
| defects found | 1 |
| defects fixed | 1 |
| false leads cleared | 3 (chip "printer", home-deal "regression", "stranded" goods) |
| pins added | 32 |
| files touched | `shop.py`, `tests/test_shops_audit.py` |
