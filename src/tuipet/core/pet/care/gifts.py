from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.utils.sound as sound
import tuipet.core.shop as shop
from tuipet.core.petbase import FULL_HUNGER

def _pick_gift(pet: Any, festival: bool=False) -> Any:
    """A SURPRISE present (2026-07-24, Joel: "presents should be just
    that, a surprise" / "make these items actually work").  Where the
    old pool was four fixed treats, a gift is now a TIER-WEIGHTED pick
    from the whole giftable catalog -- mostly a common treat, now and
    then something nicer, so you never quite know what you'll unwrap.

    A FESTIVAL present reaches one tier higher (up to rare); an ordinary
    day tops out at uncommon.  Legendary goods and the banned set are
    never gifts."""
    import tuipet.core.shop as shop
    cap = shop.TIER_ORDER.index("rare" if festival else "uncommon")
    pool = [k for k, v in shop.CATALOG.items()
            if k not in pet._GIFT_BANNED and v.where == "home"
            and shop.TIER_ORDER.index(v.tier or "common") <= cap]
    weights = [shop.tier_weight(k) for k in pool]
    return random.choice(pool) if not weights \
        else random.choices(pool, weights=weights, k=1)[0]


def claim_gift(pet: Any) -> Any:
    """ClockTic.giftEnd: the present lands in the bag and the pet cheers."""
    key, pet.gift = pet.gift, ""
    if not key:
        return ""
    e = shop.entry(key) or {}
    pet.add_item(key)
    pet._set_anim("happy", 2.0)                # giftEnd -> State.Cheering
    return f"{pet.name} gives you {e.get('name', 'a present')}!"


