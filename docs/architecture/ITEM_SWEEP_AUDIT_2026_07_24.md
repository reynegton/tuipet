# ITEM SWEEP — the end-to-end audit (2026-07-24)

Joel: "audit the item sweep. it should be finished. look at everything and
harden. polish. make better. tuipet is its own game now."

Scope: every catalog item walked from the SHELF (home, town, road, gift,
prize) through the BAG to the BELLY (handler, show, message), plus the
economy the shelves sit in.  Ground truth re-derived from the shipped
modules — nothing recalled, nothing trusted from the older boards.

**Verdict: the sweep was NOT finished.**  Coverage was — every one of the
44 items exists, resolves, has a handler, has a show, and can be obtained.
What was missing is the layer no static pin could see: three of the
prices/clocks disagreed with their own labels, one earned-access rule held
in only one of the two shops that sell the goods it gates, and the newest
feature (the home daily deal) undercut the economy's own anti-printer law.

---

## 1. THE MATRIX (re-derived, 44 items)

| axis | result |
|------|--------|
| catalog entries | 44 (Food 11 · Evolution 11 · Play 7 · Care 5 · Training 3 · Adventure 3 · Medicine 2 · Legacy 2) |
| `use_item` branch missing | **none** |
| items with NO show | **none** (eat 24 · script 15 · own-door 5) |
| items obtainable nowhere | **none** |
| towns stocking each priced good | ≥1 for all — after F3 |
| zones with a unique signature find | 26 of 26, no collisions |
| gift pool | 25 keys ordinary, 33 on a festival, bans hold |

Everything above was already true before this pass and stays true after —
that half of the arc really was finished.

## 2. WHAT THE SWEEP FOUND

### F1 — the raid prize line printed raw keys  ✅ FIXED

`raidscreen._apply_reward` named the claimed goods out of
`data.load_vitems()`.  Since the TUIPET catalog (2026-07-18) that file
holds the 11 Digimentals plus the RETIRED shelf, so the server's pool
(`energy_drink · vitamin · textbook · dna_crystal · fish`, all CATALOG
keys) resolved to one stale name and four raw keys:

> `Boss fell! Rank 1: 12000b + Energy.D, vitamin, dna_crystal`

The felled-boss claim is the biggest single moment the game has.  Now
resolved through `shop.entry` — THE key resolver — so it reads
`Energy Drink, Vitamin, DNA Crystal`.

### F2 — the map-clear gate held in exactly one shop  ✅ FIXED

The road shelf unlocks by CLEARING MAPS (`shop.ADVENTURE_GATES`), and
`catalog()` has honoured that since v0.5.114 — the home shop hides a
locked transport.  **No town shelf ever asked.**  Town 0 sits on map 1's
first leg, and at zero progress it sold Town Transport and Disaster
Transport outright.  An earned-access rule that the first town on the road
sells around is not a rule.

`shop._open_rows()` now filters every town shelf through the same
`adventure_open` the home shelf uses, and the daily deal is dealt over the
OPEN rows (the v0.5.164 lesson: a deal on an invisible row is no deal).

### F3 — Life Recovery was sold in NO town on earth  ✅ FIXED

`shopConsumable.csv` authors i:29/i:30 (both transports) in all 26 towns
and has no row for i:27, so the road tool you most need WHILE ON THE ROAD
was the one buyable good no counter anywhere stocked.  The guest slot
could never fill it — its pool excludes Adventure precisely so the gate
holds, and a guest row is ungated.  Town counters now carry the whole road
shelf, gated: all three tools, once earned.

### F4 — the Grow Capsule was a stage-skip sold as a nudge  ✅ FIXED

`_time_gear` set `stage_seconds += 7200`.  Under THE UNIT LAW dt is
game-minutes 1:1, and the stage clocks are 180 / 360 / 1440 / 2160 / 2880 —
so one 500b capsule was **2.5× the longest stage in the game**: it filled
ANY stage's growth gate outright, at any point, forever.

The quiet half is worse.  `LATE_STAGE_WINDOW` is 2880, so the same capsule
vaulted an Ultimate/Mega straight into the Pen20 frailty window — the rule
where 5 care mistakes is death.  A tamer at 4 slips buys a growth item and
dies on the next one, with nothing on the shelf hinting at it.

This is the **third** instance of the 60× family (after the vitamin guard,
P0a, and the fidget cadence).  The 2026-07-19 "the words won" pass read
"+120min" as 120 REAL minutes; that reading is only available for items on
a WALL clock.  Steak (12h satiety) and Port. Potty (24h auto-clean) ride
`world_seconds` and STAND exactly as ruled — the capsule rides the growth
clock, which is the pet's own.  No reading of "+120min" describes "the
whole stage, instantly", so the ruling's own goal is what moved the
number: **+120 game-minutes**, the label's own figure.

> ⚠ If the capsule should feel richer than 8% of a Rookie stage, that is
> a balance call and one number (`petcare._time_gear`).  What it must
> never be again is a growth constant denominated in real time.

**RULED, same day — "make the grow capsule worth 500b" (v0.5.242).**  The
honest +120 was worth about 8% of a Rookie stage, which is not 500b of
anything.  It now buys **a quarter of THIS stage**
(`GROW_CAPSULE_FRACTION`), which is the only shape that means the same
thing at both ends of a 180→2880 range — a flat figure worth having at
Ultimate skips a baby stage whole.  Two rails keep the priced version from
becoming the bug it replaced:

* it **hurries the wait, never ends it** — the push stops one tick short
  of the gate, so no stack of capsules evolves a pet outright, and at
  Ultimate (whose stage length IS `LATE_STAGE_WINDOW`) that same stop is
  what keeps capsules from arming the Pen20 frailty death by themselves;
* a **final form refuses** it — a Mega has no clock to hurry and
  `stage_seconds` only feeds frailty there, so the shelf would be selling
  a pure downside (the no-duds rule, same call as F6).

The shelf text moved with it: "growth: a quarter of this stage", and the
use message names the real figure ("+360min" in a Rookie).

### F5 — the home daily deal was an uncapped bits printer  ✅ FIXED

The town economy was built so every flip lands at-or-below water, and the
few that don't are bounded: "the daily cap is what makes the demand resale
a treat instead of a printer" (`TOWN_DAILY_CAP`, shops arc).  The home
deal (v0.5.225) arrived after that law and skipped it — it sells at HALF
catalog while any town that doesn't stock the good pays TOWN_DEMAND 70%.

Measured: **+20% of catalog per unit, unbounded** — on Omni Chip G's day,
buy at 4,000 and sell at 5,600, as many as bits allow (+1,600 a copy).

The deal now carries the same tier ration a town row does (common 3,
uncommon 2, rare/legendary 1).  A spent ration is **not** a shut door: the
row reverts to full price and stays buyable without limit, because home is
the shelf that is always open — and at full price no flip is profitable
anywhere.  A one-press guard (the bag's `_retarget` grammar) eats the
first ENTER after the bargain runs out, so a mash can't pay 2× by
accident.

### F6 — the Caffeine Pill could be spent for nothing  ✅ FIXED

Both branches could consume a 300b pill and move no number at all — a
second pill while the grace clock already holds that push, or a pressure
pet whose `sleep_lapse` is still 0 — while cheerfully saying "Wide awake
for a while yet."  Every care sibling refuses at full instead ("Energy is
already full", "already a model pupil", "belly's full").  It refuses now,
and keeps the pill.

### F7 — the bedtime grace clock evaporated on quit  ✅ FIXED

Found BY F6's fix, not by looking: `_bed_postpone_t` was a bare instance
attribute, never a Pet field, so it never rode a save.  It carries a
disturb's postpone AND the entire effect of a 300b Caffeine Pill — which
for a line pet (every hatch) rides this channel and nothing else.  Quit
after taking one and the pill's effect was simply gone.

Same class the F8 audit closed for four other clocks in 2026-07-20
(`_hunger_call_t`, `_str_call_t`, `_ac_pay`, `_dp_t`); this was the fifth,
and it hid because `getattr(self, "_bed_postpone_t", 0.0)` reads fine
whether the attribute exists or not.  Now a persisted field.

## 3. THE HARDENING — `touches` stopped being a claim

P2's `Item.touches` was read out of the handlers by hand and pinned
STATICALLY: the pins proved every name was a real Pet field and none was
dormant, and nothing ever checked that the handler moves what the entry
says it moves.

`tests/test_items_sweep.py` now USES each item on a permissive pet and
diffs the dataclass: anything declared must move, anything moved must be
declared (bar the documented side channels), and every landing use spends
exactly one while every refusal spends none.  That pin immediately caught
its first drift — the Caffeine Pill declared `sleep_lapse` and, for every
line pet in the game, moves `_bed_postpone_t` instead.  Both are declared
now.

### The last gap closed — the shelf's NUMBERS (v0.5.243)

Joel: "no need for a refactor?"  The structure needed none — P1-P6 landed
the named record, the one grouping, the single show/name/buy sources, and
the sweep proved they hold.  Of the old scoping board's candidates, P-A /
P-D / P-F are closed, **P-E is now closed outright** — `FOOD_KEYS` had zero
live consumers and was CUT on Joel's named order 2026-07-25, so
`item_is_eaten` is the single answer to "is this eaten" (the category set
said no to all six food-sheet consumables, which is precisely the
disagreement P-E named); a pin fails if the rival set ever returns.  P-B
(the dispatch dict rebuilt per call) is cosmetic at one keypress per use.

**P-C was the one that was still open**, and it needed a pin, not a
rewrite.  `touches` proves WHICH meter moves; the dossier prose promises
HOW FAR, and only 10 of the 29 numeric claims were checked anywhere — so
`_snack(weight=-1)` edited to `-2` left the Vegetable's card lying with the
whole suite green.

`test_the_shelf_text_promises_the_number_the_handler_delivers` now READS
the claim out of the shelf text and measures it against the handler, all
29 at once.  Two properties matter:

* an unmeasured number FAILS rather than passing vacuously -- a new item
  cannot bring an unchecked claim onto the shelf;
* mutation-tested both ways before shipping: `weight=-1` → `-2` fails the
  Vegetable, and a fabricated "· vim +3" on the Tuna fails the guard.

No drift existed — every one of the 29 was already honest.  The pin is
what keeps it that way.

## 4. LOOKED AT, LEFT ALONE (deliberate, not oversights)

- **Poison Mushroom is a zone signature.**  The TOWN rule bans it from
  guest slots ("a signature good is never a trap"); the ZONE pass has no
  such ban, so one zone signs it.  It has been findable in forestgate
  since the diversity audit, so this concentrates an existing find rather
  than adding a trap.  Changing it moves loot for three zones — a named
  order, not a sweep fix.
- **`digimemory` is findable in 3 biome pools** yet deliberately unfindable
  as a signature.  D5's ruling: a wild chip has no ancestor payload.  Those
  pool entries pre-date the ruling; a found one says "The chip is silent."
  Flagged, unchanged — the D5 board explicitly ruled the item, not the
  pools.
- **`pet.py:715` grants a RAW icon key** (`add_item(f"i:{give_item}")`) —
  the exact trap the i:32 heal fixed, latent only because `evolutions.csv`
  ships no item columns.  Dormant data stays dormant; noted here so the
  next person who wakes that column knows to route it through
  `shop.key_for_icon`.
- **Steak / Port. Potty real-hour durations** — Joel's 2026-07-19 ruling,
  wall clocks, untouched (see F4).
- **Tier is never SHOWN to the player.**  D1 ruled rarity is *felt* (stock
  + find), and the 26-col dossier holds exactly two rows.  Adding a rarity
  word is a design call.

## 5. STATE

v0.5.241 staged — F1-F7 plus the pins.  Suite **1881 → 1937 green**;
ruff 259 (flat), bandit 2 (flat), **mypy baseline ratcheted 24 → 23**
(two annotations in files this pass touched; HEAD itself was already one
over its recorded baseline, so the gate was red before this work and is
green after).  Smoke-launched live: the shop renders the deal row
("150b · DEAL! (was 300b)"), the spent-ration row ("300b · deal gone
today") and the guard flash ("deal's gone — ENTER again for 300b").

Not published — awaiting Joel's word on the release.
