import random
import datetime
import time
from math import gcd as _gcd
import tuipet.data.loaders.data as data
from tuipet.i18n.translator import t
from tuipet.core.petbase import *
from tuipet.core.shop.catalog import *
import tuipet.core.shop.eggs as eggs
import tuipet.core.shop.catalog as catalog

def buy(pet, e):
    """-> (message, sfx)."""
    if pet.bits < e["price"]:
        return (f"Precisa de {e['price']}b — você tem {pet.bits}b.", "error")
    pet.spend_bits(e["price"])
    pet.add_item(e["key"])
    return (f"Comprou {e['name']}!", "confirm")


def resell_price(e):
    # a town-priced bag row carries its LOCAL sell price (buy-low/sell-high,
    # shops arc 2026-07-21); home keeps the flat half
    if "sell_price" in e:
        return max(1, int(e["sell_price"]))
    return max(1, e.get("price", 0) // 2)


def sell(pet, e):
    if pet.inventory.get(e["key"], 0) <= 0:
        return ("Você não tem isso.", "error")
    pet.take_item(e["key"])                    # classic take_item returns None
    pet.bits += resell_price(e)
    return (f"Vendeu {e['name']} por {resell_price(e)}b.", "confirm")


def _today_ordinal(today=None):
    import tuipet.core.tournament as tournament
    d = today if today is not None else tournament._today()
    return d.toordinal()


def _town_maps():
    """town_id -> the MAP whose zone hosts the town (the road's own
    geography; item diversity audit 2026-07-23)."""
    import tuipet.data.loaders.data as data
    out = {}
    for mp in data.load_maps():
        for z in mp["zones"]:
            for _lo, _hi, tid in z.get("towns", ()):
                out[tid] = z["map"]
    return out


def _econ_stub(key):
    """A synthetic econ row for non-authored shelf rows (guest/regional):
    catalog price, standard factors, capped stock -- no money printer."""
    v = CATALOG[key]
    return {"price": v.price, "sale_factor": 2, "resell_factor": 2,
            "max_stock": 2, "is_food": v.category == "Feed",
            "consumable_id": -1}


def _base_rows(town_id):
    """The town's authored shelf + its map's regional specialty:
    [(sid, catalog_key, econ_row, local_price)] in list order (items shelf
    first, then the food family).  local_price is the PRICE-LAW ratio (see
    above); rows whose consumable has no living CATALOG identity are
    dropped -- their systems (chips, furniture) aren't in tuipet, and
    dormant data stays dormant."""
    import tuipet.data.loaders.data as data
    t = data.load_towns().get(town_id)
    if not t:
        return []
    ov = data.load_shop_overrides()
    import tuipet.data.loaders.data_shop as data_shop
    foods, items = data_shop._load_consumables()
    rows = []
    for sid in t["items_override"] + t["foods_override"]:
        o = ov.get(sid)
        if not o or o["price"] <= 0:
            continue
        icon = ("f:" if o["is_food"] else "i:") + str(o["consumable_id"])
        k = key_for_icon(icon)
        if not k:
            continue
        e = entry(k)
        default = ((foods if o["is_food"] else items).get(o["consumable_id"])
                   or {}).get("price", 0)
        if e and default > 0:
            local = max(1, round(e["price"] * o["price"] / default))
        else:
            local = o["price"]
        if any(k == have for _s, have, _o, _l in rows):
            # RETIRED resolution can land two authored rows on one heir (a
            # town that stocked both the toilet and the port-potty now has
            # two port-potty lines): the shelf keeps the FIRST, because a
            # duplicate row breaks the one-key-one-row grammar everything
            # downstream (deal dedup included) assumes (refactor 2026-07-27)
            continue
        rows.append((sid, k, o, local))
    from .catalog import _MAP_SPECIALTY
    sk = _MAP_SPECIALTY.get(_town_maps().get(town_id))
    if sk and sk not in {k for _sid, k, _o, _p in rows}:
        rows.append((f"regional:{town_id}", sk, _econ_stub(sk),
                     CATALOG[sk].price))
    return rows


def _guest_deal():
    """town_id -> its standing guest good, dealt WITHOUT replacement
    across ALL towns (item diversity audit 2026-07-23: the old per-town
    crc32 pick birthday-collided -- 8 items served 2-3 towns each, and
    towns 11+12 were byte-identical shops).  The pool is the UNGATED
    priced catalog minus Adventure (its map-clear gate must hold) and
    minus the Poison Mushroom (a town's one signature good is never a
    trap -- the raid-pool rule).  26 towns, 36 candidates: every town's
    guest is unique game-wide.  crc32-ordered, so the deal is STABLE --
    a town's character stays permanent (the guest-good law); the daily
    deal already rotates.

    COVERAGE FIRST (2026-07-24, Joel "pull them into town rotation"): the
    guest slot exists for VARIETY, so it fills gaps before it spends a slot
    on a good already sold in some town's authored base.  15 goods live in a
    base somewhere; the other 21 need a guest slot to appear anywhere, and 21
    fits in 26 slots with room to spare -- yet the old pure-crc32 order let a
    few slots land on base-covered goods, stranding tuna, cheese_burger and
    the ball in NO town at all.  Sorting the not-in-any-base goods to the
    FRONT covers every one of the 21 (still crc32 WITHIN each band, so the
    deal stays stable), and the leftover slots go to base-covered goods."""
    import zlib
    pool = [k for k, v in CATALOG.items()
            if v.price is not None and v.category != "Road"
            and k != "poison_mushroom"]
    base_anywhere = set()
    for tid in _town_maps():
        base_anywhere.update(k for _sid, k, _o, _p in _base_rows(tid))
    pool.sort(key=lambda k: (k in base_anywhere,
                             zlib.crc32(f"guest2:{k}".encode())))
    taken, out = set(), {}
    for tid in sorted(_town_maps()):
        stocked = {k for _sid, k, _o, _p in _base_rows(tid)}
        pick = (next((k for k in pool
                      if k not in taken and k not in stocked), None)
                or next((k for k in pool if k not in stocked), None))
        if pick:
            taken.add(pick)
            out[tid] = pick
    return out


def _town_rows(town_id):
    """The full town shelf: authored base + regional specialty + the
    standing guest good (gameplay polish #24; re-dealt collision-free in
    the item diversity audit 2026-07-23) + THE ROAD SHELF.

    The road shelf (item sweep 2026-07-24): a town counter carries every
    Adventure item, not just the two the authored overrides happen to
    name.  `shopConsumable.csv` stocks i:29/i:30 (the two transports) in
    all 26 towns and has no row for i:27, so Life Recovery -- the road
    tool you most need WHILE ON THE ROAD -- was the one buyable good no
    counter in the world sold.  The guest slot could never fix it: its
    pool excludes Adventure precisely because the map-clear gate has to
    hold, and a guest row is ungated.

    These rows are the shelf's IDENTITY, gate or no gate.  What a tamer
    may actually buy today is `_open_rows`."""
    rows = _base_rows(town_id)
    gk = _guest_deal().get(town_id)
    if gk:
        rows.append((f"guest:{town_id}", gk, _econ_stub(gk),
                     CATALOG[gk].price))
    have = {k for _sid, k, _o, _p in rows}
    for k, v in CATALOG.items():
        if v.category == "Road" and k not in have:
            rows.append((f"road:{town_id}:{k}", k, _econ_stub(k), v.price))
    return rows


def _open_rows(town_id, prog=None):
    """The town shelf a tamer can actually SHOP today: `_town_rows` minus
    anything whose earned-access gate is still shut.

    THE GATE HELD IN EXACTLY ONE SHOP (item sweep 2026-07-24).  The road
    shelf unlocks by CLEARING MAPS -- `catalog()` has honoured that since
    v0.5.114, so the home shop hides a locked transport.  Town counters
    never asked: town 0 sits on map 1's FIRST leg, and it sold Town
    Transport and Disaster Transport to a tamer who had cleared nothing.
    An earned-access rule that any starting town sells around is not a
    rule.  (Read fresh each call rather than cached: `_guest_deal`'s
    lru_cache reads `_base_rows`, which stays progress-free, so no cache
    can freeze a tamer's progress into a town's shelf.)"""
    if prog is None:
        import tuipet.utils.persistence as persistence
        prog = persistence.get_progress()
    return [r for r in _town_rows(town_id) if adventure_open(r[1], prog)]


_DEAL_LOOKBACK = 32

def _deal_index(seed, count, today=None):
    """A daily rotating index in [0, count), crc32-seeded on (seed, day):
    stable all day, different tomorrow.  DEDUPED (2026-07-24, Joel: "dedup
    the town deal") -- it never repeats YESTERDAY's pick, so no shelf shows
    the same deal two days running.  (With a single item there is nothing
    to rotate to; it stays put.)

    The dedup compares against yesterday's FINAL (post-bump) pick, not its
    raw index -- if it compared raws, a day that was itself bumped could be
    silently repeated by today.  So the picks are walked FORWARD from a
    fixed lookback: each day bumps off the previous day's final.  Any error
    in the window's first day washes out long before today."""
    if count <= 0:
        return None
    if count == 1:
        return 0
    import zlib
    def raw(day):
        return zlib.crc32(f"{seed}:{day}".encode()) % count
    day = _today_ordinal(today)
    final = raw(day - _DEAL_LOOKBACK)
    for d in range(day - _DEAL_LOOKBACK + 1, day + 1):
        r = raw(d)
        if r == final:                       # would repeat yesterday's pick
            r = (r + 1) % count
        final = r
    return final


def town_deal_sid(town_id, today=None, prog=None):
    """The town's ONE rotating daily deal: seeded on (town, day) -- stable
    all day, different tomorrow, different next town, and never the same as
    yesterday (dedup 2026-07-24).

    Dealt over the OPEN rows only: a deal on a row the tamer can't see is
    no deal at all (the v0.5.164 lesson -- the deal rolled onto the
    invisible Adventure shelf about half of all days)."""
    rows = _open_rows(town_id, prog)
    if not rows:
        return None
    return rows[_deal_index(town_id, len(rows), today)][0]


def _home_deal_pool():
    return sorted(k for k, v in CATALOG.items()
                  if v.price is not None and v.category != "Road")


def home_deal_key(today=None):
    """The home shelf's ONE rotating daily deal key (2026-07-24, Joel: "add
    the home daily deal") -- seeded on the day, deduped vs yesterday."""
    pool = _home_deal_pool()
    i = _deal_index("home", len(pool), today)
    return pool[i] if i is not None else None


def home_band(today=None):
    """The day's rotating guest rows.

    A SHUFFLED CYCLE, not a random draw (audit 2026-07-27): the first cut
    of this was tier-weighted sampling, and a 40-day probe caught it simply
    never dealing Flaming Wings -- a shelf that MAY show a thing eventually
    is the slot machine, not the store.  Joel's actual question ("are items
    spread out evenly thoughout the week?") is the spec: the non-staple pool
    is shuffled once per EPOCH (seeded, so every device deals the same week)
    and dealt out in day-sized hands, so every sellable key is guaranteed a
    home-shelf day each cycle (~1 week).  Rarity stays where it belongs --
    in prices, town curation and the tier rations -- not in whether the
    counter will ever stock the good at all."""
    pool = [k for k, v in sorted(CATALOG.items())
            if v.price is not None and k not in HOME_STAPLES
            and v.category != "Road"]        # road rows ride their own gate
    if not pool:
        return []
    days = -(-len(pool) // HOME_BAND_SIZE)          # hands per full cycle
    o = _today_ordinal(today)
    epoch, day = divmod(o, days)
    deck = list(pool)
    random.Random(f"homeband:{epoch}").shuffle(deck)
    hand = deck[day * HOME_BAND_SIZE:(day + 1) * HOME_BAND_SIZE]
    # the last hand of a short deck tops up from the front, never short-shelves
    if len(hand) < HOME_BAND_SIZE:
        hand += deck[:HOME_BAND_SIZE - len(hand)]
    return hand


def _ration_left(shop_id, key, taken):
    """Today's remaining ration for a tier-limited row -- THE one place the
    arithmetic lives (assembly dedup 2026-07-27: home and town each hand-
    rolled this line, the seam where the two shelves could drift)."""
    return max(0, tier_stock(key) - int(taken.get(f"{shop_id}:{key}", 0)))


def home_stock(today=None, pet=None):
    """The home shelf: staples + the day's band + the deal, decorated the
    same way a town counter is (shops-look-the-same law).

    Pricing and rationing are unchanged from the audit rulings: staples and
    band rows sell UNLIMITED at full catalog price (a flip at catalog is
    always a loss -- item sweep 2026-07-24), the one deal row and the
    capsule keep their daily tier rations, and a spent deal ration falls
    back to full price rather than a shut door."""
    deal = home_deal_key(today)
    band = set(home_band(today))
    taken = _town_taken(pet, today) if pet is not None else {}
    out = []
    for e in catalog():
        k = e["key"]
        if (k != deal and k not in HOME_STAPLES and k not in band
                and e["category"] not in (ARMOR_CATEGORY, "Road")):
            # not on today's shelf -- come back tomorrow.  TWO shelves
            # bypass the band, because both are DOORS, not stock: the
            # Relic shelf (the crest system's single door) and the
            # ROAD shelf (map-clear gated -- a tamer who just earned the
            # warp must not wait three days to buy it; the gate IS its
            # scarcity).  Everything else rotates.
            continue
        if k in HOME_RATIONED and k != deal:
            # THE CAPSULE RATION (expansion audit 2026-07-26): its contents
            # out-value its price by construction, so the always-open shelf
            # rations it like a deal row or it prints bits
            left = _ration_left(HOME_SHOP_ID, k, taken)
            out.append(dict(e, left=left, town_id=HOME_SHOP_ID))
            continue
        if k == deal:
            base = e["price"]
            left = _ration_left(HOME_SHOP_ID, k, taken)
            e = (dict(e, deal=True, base_price=base, left=left,
                      town_id=HOME_SHOP_ID,
                      price=max(1, base // HOME_DEAL_FACTOR)) if left > 0
                 else dict(e, deal_spent=True))
        out.append(e)
    return out


def _stocked(town_id, key):
    """This town's shelf row for `key`, or None (the demand test)."""
    for _sid, k, o, local in _town_rows(town_id):
        if k == key:
            return o, local
    return None


def _town_taken(pet, today=None):
    """The day's purchase ledger for this pet ({} once the day turns)."""
    tb = getattr(pet, "town_bought", None) or {}
    return tb if tb.get("day") == _today_ordinal(today) else {}


def town_stock(town_id, today=None, pet=None):
    """The town shop's shelves as ready entries [{key,name,price,category,
    base_price,deal,left,town_id}].  The day's rotating deal (and, on a
    FESTIVAL, every row -- the festival market) sells at the canon
    checkSale price: price // SaleFactor.  `left` is the authored maxStock
    minus the day's take (the anti-pump: town prices are DVPet's own,
    far under the catalog -- the daily cap is what makes the demand
    resale a treat instead of a printer)."""
    import tuipet.core.adventure as adventure
    import tuipet.utils.persistence as persistence
    prog = persistence.get_progress()
    deal = town_deal_sid(town_id, today, prog)
    fest = bool(adventure.active_holiday(today))
    taken = _town_taken(pet, today) if pet is not None else {}
    out = []
    for sid, k, o, local in _open_rows(town_id, prog):
        e = entry(k)
        if not e:
            continue
        on = fest or sid == deal
        price = local // max(1, o["sale_factor"]) if on else local
        # TIERED STOCK (D1, 2026-07-24): rarity now limits how many a town
        # will part with in a day, on the same ladder the road rolls -- a
        # legendary good is one-per-town-per-day, a common one three.  The
        # authored maxStock and the global daily cap still bound it.
        # the authored maxStock and the global cap still bound the shared ration
        left = min(_ration_left(town_id, k, taken),
                   max(0, min(o["max_stock"], TOWN_DAILY_CAP)
                       - int(taken.get(f"{town_id}:{k}", 0))))
        out.append(dict(e, price=max(1, price), base_price=local,
                        deal=on, left=left, town_id=town_id))
    return out


def town_buy(pet, e, today=None):
    """A town counter purchase: blocked once the day's authored stock is
    gone, recorded in the pet's daily ledger otherwise.

    THE LIVE ROW, never the caller's copy (live-play audit 2026-07-25):
    this is the ONE rationed counter door, and it trusted the entry dict
    it was handed -- a stale row replayed after the ration was spent
    oversold the deal at the deal price.  The UI rebuilds rows every
    keypress so no key reaches it today, but any future caller that
    caches a row would mint discounted stock.  Re-fetch the row from its
    own builder and buy THAT: forged/stale `left` and `price` both die
    here."""
    tid = e.get("town_id", HOME_SHOP_ID)
    rows = (home_stock(today, pet) if tid == HOME_SHOP_ID
            else town_stock(tid, today, pet))
    live = next((r for r in rows if r.get("key") == e.get("key")
                 and r.get("left") is not None), None)
    if live is None or live.get("left", 0) <= 0:
        return ("Esgotado hoje — volte amanhã.", "error")
    e = live
    msg, sfx = buy(pet, e)
    if sfx == "confirm":
        day = _today_ordinal(today)
        tb = getattr(pet, "town_bought", None) or {}
        if tb.get("day") != day:
            tb = {"day": day}                  # a new day sweeps the ledger
        k = f"{e['town_id']}:{e['key']}"
        tb[k] = int(tb.get(k, 0)) + 1
        pet.town_bought = tb
    return (msg, sfx)


def town_sell_price(key, town_id):
    """Buy-low/sell-high: a good this town STOCKS resells at the canon
    local_price // ResellFactor (it has plenty); one it DOESN'T stock is
    in DEMAND -- 70% of catalog price, better than home's half.  The
    trade window: buy a family's exclusive ON DEAL, carry it to the
    OTHER family's towns."""
    hit = _stocked(town_id, key)
    if hit is not None:
        o, local = hit
        return max(1, local // max(1, o["resell_factor"]))
    e = entry(key)
    if not e:
        return 1
    return max(1, e["price"] * TOWN_DEMAND_NUM // TOWN_DEMAND_DEN)


