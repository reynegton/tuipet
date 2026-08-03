import math
import math
import tuipet.data.loaders.data as data
import tuipet.core.egg as egg_mod
from tuipet.i18n.translator import t
from tuipet.core.petbase import *
from tuipet.core.shop.catalog import *

def _sellable_eggs():
    """The egg a town may stock: every egg that ISN'T a free starter
import tuipet.core.shop.catalog as catalog
    (the five START babies you already own) and CAN be owned.  A can_perm
    FALSE row is a lineage egg -- hatchable only the generation its
    condition holds, never permanently ownable (eggmigrate._sane_owned
    strips exactly these from eggs_owned "however they snuck in"), so the
    buy-outright shortcut must not sell what a repair pass deletes (egg
    audit 2026-07-25: towns 0/2/5 sold all five lineage eggs)."""
    import tuipet.core.egg as egg_mod
    import tuipet.data.loaders.data as data
    rules = data.load_egg_unlock()
    return [i for i in range(egg_mod.count())
            if not (rules.get(i) or {}).get("start")
            and (rules.get(i) or {}).get("can_perm", True)]


def town_egg_stock(town_id, count=EGG_STOCK_PER_TOWN):
    """The DISTINCT set of eggs THIS town sells -- a stable band over the
    earnable egg, rotated by town so no two town shops feel the same."""
    pool = _sellable_eggs()
    if not pool:
        return []
    count = min(count, len(pool))
    # a stride CO-PRIME with the pool keeps every town's band distinct --
    # stepping by the band width alone collapsed to len(pool)/count bands
    # the moment the width divided the pool (egg audit 2026-07-25: cutting
    # the 5 lineage eggs left a 36-egg pool, and 26 towns fell into 6 bands)
    stride = count
    while len(pool) > 1 and math.gcd(stride, len(pool)) != 1:
        stride += 1
    start = (int(town_id) * stride) % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(count)]


def egg_price(idx):
    """A town egg's bit price -- earned eggs are a treat, so the buy-outright
    shortcut costs real bits.  Starters (never stocked) are free."""
    import tuipet.data.loaders.data as data
    rule = data.load_egg_unlock().get(idx) or {}
    return 0 if rule.get("start") else 800


def town_egg_rows(town_id):
    """The town's egg band as SHOP ROWS (shops-look-the-same,
    2026-07-22: Joel — "the egg tabs in town shops are different than the
    normal shops, why arent these things modulized").  Same entry shape
    the shelf renders everywhere; `egg_idx` rides the existing menu icon
    plumbing (shop eggs draw their real egg frames)."""
    import tuipet.core.egg as egg_mod
    owned = egg_mod.owned_now()          # earned-but-unbanked counts as owned
    return [{"key": f"egg:{i}", "name": egg_mod.hatch_name(i)[:18],
             "price": egg_price(i), "category": "Egg",
             "egg_idx": i, "owned": i in owned, "town_id": town_id}
            for i in town_egg_stock(town_id)]


def town_egg_buy(pet, idx):
    """Buy a egg outright (bits -> persistence.egg_own) -> (msg, sfx).
    THE single buy path — the town egg panel and the shop's Eggs tab both
    call here (single-source law)."""
    import tuipet.data.loaders.data as data
    import tuipet.core.egg as egg_mod
    import tuipet.utils.persistence as persistence
    rule = data.load_egg_unlock().get(idx)
    if rule is not None and not rule["can_perm"]:
        # the single buy path guards what the shelf filter promises: a
        # lineage egg is never permanently ownable (egg audit 2026-07-25)
        return ("Um ovo de linhagem — choca para quem o conquista.", "error")
    if idx in egg_mod.owned_now():       # same read as the shelf: never sell
        return ("Você já possui esse ovo.", "error")   # what's already earned
    price = egg_price(idx)
    if not pet.spend_bits(price):
        return (f"{price}b — bits insuficientes.", "error")
    persistence.egg_own(idx)
    return (f"Comprou o ovo de {egg_mod.hatch_name(idx)} — "
            "it's on your carousel!", "reward")


