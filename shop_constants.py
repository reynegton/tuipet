_TOUCHES = {
    # ---- FOOD ----
    "fish": ("hunger",),
    "vegetable": ("hunger", "weight"),
    "tuna": ("hunger", "energy"),
    "cake": ("hunger", "energy", "weight"),
    "cupcake": ("hunger", "energy"),
    "cookie": ("hunger", "energy"),
    "candy": ("hunger", "energy"),
    "cheese_burger": ("hunger", "weight", "care_mistakes"),
    "giga_meal": ("hunger", "energy", "weight"),
    "steak": ("hunger", "full_until"),
    "poison_mushroom": ("dead",),          # _die(): the one lethal entry
    # ---- CARE ----
    "energy_drink": ("energy",),
    "slim_drink": ("weight",),
    "vitamin": ("strength", "vitamin_lapse"),
    "miracle_drink": ("care_mistakes", "energy"),
    "sleeping_pill": ("asleep", "lights", "nap"),
    # BOTH channels, because it really does use both (item sweep
    # 2026-07-24: a line pet -- every hatch -- pushes bedtime through the
    # grace clock, and only a pressure pet moves sleep_lapse.  Declaring
    # one and moving the other is exactly the drift `touches` exists to
    # catch, and the behavioural pin now catches it.)
    "caffeine_pill": ("sleep_lapse", "_bed_postpone_t"),
    "music_player": ("asleep", "lights", "nap", "awake_lapse"),
    "textbook": ("obedience",),
    "port_potty": ("poop", "poop_sizes", "auto_clean_until"),
    # ---- GROWTH ----
    "dumbbell": ("stage_trainings",),
    "grow_capsule": ("stage_seconds",),
    "anti_evo_chip": ("evo_blocked",),
    "x_antibody": ("x_antibody",),
    "dna_crystal": ("dna_owned",),
    "vaccine_chip": ("vaccine",),
    "data_chip": ("data_power",),
    "virus_chip": ("virus",),
    "vaccine_chip_g": ("vaccine",),
    "data_chip_g": ("data_power",),
    "virus_chip_g": ("virus",),
    "omni_chip_g": ("vaccine", "data_power", "virus"),
    "revive_floppy": ("dead",),
    "memory": ("vaccine", "data_power", "virus", "memory"),
    # ---- TOYS ----
    "ball": ("weight",),
    "skateboard": ("weight", "energy"),
    "xylophone": ("energy",),
    "video_game": ("energy", "weight"),
    "television": ("energy", "weight"),
    # ---- ADVENTURE ----
    # Empty by design: from the HOME bag these three only refuse.  Their
    # real work is adventure-run state (the march's location, its lives),
    # which is not Pet state and does not belong in this namespace.
    # `where="road"` is what carries that meaning.
    "town_transport": (),
    "disaster_transport": (),
    "life_recovery": (),
    # ---- THE EXPANSION (2026-07-26): read out of the new handlers ----------
    "meat": ('hunger', 'weight'),
    "fruit": ('hunger', 'obedience'),
    "bread": ('hunger', 'weight'),
    "cheese": ('hunger', 'weight'),
    "broccoli": ('hunger', 'obedience'),
    "orange": ('hunger', 'obedience'),
    "honey": ('hunger', 'energy', 'obedience', 'weight'),
    "chocolate_egg": ('hunger', 'weight'),
    "burnt_food": ('hunger', 'strength', 'obedience'),
    "yellow_pepper": ("hunger", "obedience", "virus"),
    "green_pepper": ("hunger", "obedience", "data_power"),
    "red_pepper": ("hunger", "obedience", "vaccine"),
    "med": ('sick',),
    "elixir": ('sick', 'energy'),
    "vitamin_g": ('injured', 'strength', 'vitamin_lapse'),
    "cold_compress": ('care_mistakes', 'energy'),
    "gold_pill": ('energy',),
    "supplement": ('strength', 'obedience', 'weight'),
    "food_pill": ('hunger', 'obedience', 'weight'),
    "ai_supplement": ('strength',),
    "ai_food_pill": ('hunger',),
    "hp_chip": ('vaccine', 'data_power', 'virus'),
    "hp_chip_g": ('vaccine', 'data_power', 'virus'),
    "hedonism_101": ('obedience',),
    "book": ('obedience',),
    "board_game": ('vaccine', 'data_power', 'obedience'),
    "computer_game": ('virus', 'data_power'),
    "trampoline": ('strength', 'weight'),
    "x_program": ('hunger', 'strength', 'energy', 'x_antibody'),
    "zone_transport": (),
    "continent_transport": (),
    "datatron": ('num',),
    "horn_helmet": ('num',),
    "grey_claws": ('num',),
    "water_bottle": ('num',),
    "torn_tatter": ('num',),
    "white_wings": ('num',),
    "black_wings": ('num',),
    "metal_armor": ('num',),
    "flaming_wings": ('num',),
    "toy_oven": ('hunger',),
    "capsule_a": (),
    "capsule_b": (),
    "capsule_c": (),
    "capsule_d": (),
    "capsule_e": (),
    "capsule_f": (),
    "capsule_g": (),
    "capsule_h": (),
    "prank_capsule_a": (),
    "prank_capsule_b": (),
    "futon": ('futon_doze',),
    "human_fire_spirit": ('num',),
    "human_light_spirit": ('num',),
    "human_ice_spirit": ('num',),
    "human_wind_spirit": ('num',),
    "human_thunder_spirit": ('num',),
    "human_earth_spirit": ('num',),
    "human_water_spirit": ('num',),
    "human_wood_spirit": ('num',),
    "human_metal_spirit": ('num',),
    "human_dark_spirit": ('num',),
    "beast_fire_spirit": ('num',),
    "beast_light_spirit": ('num',),
    "beast_ice_spirit": ('num',),
    "beast_wind_spirit": ('num',),
    "beast_thunder_spirit": ('num',),
    "beast_earth_spirit": ('num',),
    "beast_water_spirit": ('num',),
    "beast_wood_spirit": ('num',),
    "beast_metal_spirit": ('num',),
    "beast_dark_spirit": ('num',),
}

# ---------------------------------------------------------------------------
# TIERED RARITY (distribution arc, 2026-07-24 -- Joel ruled D1 "stock and
# find").  The tier is DERIVED FROM THE CANON PRICE, never hand-assigned:
# 20 of the 40 priced entries carry DVPet's own DefaultPrice, and P5/P6
# deliberately took those numbers, so price already IS the game's opinion of
# an item's worth.  Deriving means no economy gets invented here -- the bands
# are just a reading of data that was already there.
#
# The ladder falls out cleanly: 14 common, 12 uncommon, 9 rare, 5 legendary.
# Grant-only treats (price None) have no band and read as common wherever a
# weight is needed -- a birthday cupcake is the commonest thing there is.
TIER_BANDS = ((300, "common"), (1000, "uncommon"), (2500, "rare"))
TIER_TOP = "legendary"
TIER_ORDER = ("common", "uncommon", "rare", "legendary")


def tier_for_price(price):
    """The band a price falls in, or None for a grant-only item."""
    if price is None:
        return None
    for ceiling, name in TIER_BANDS:
        if price <= ceiling:
            return name
    return TIER_TOP


# How much RARER a tier is, both on the shelf and on the road.  One curve
# for both levers so "rare" means one thing in this game.
TIER_WEIGHT = {"common": 8, "uncommon": 4, "rare": 2, "legendary": 1}
# Daily town stock ceiling by tier (capped further by TOWN_DAILY_CAP).
TIER_STOCK = {"common": 3, "uncommon": 2, "rare": 1, "legendary": 1}


# grant-only keys whose rarity is NOT "commonest thing there is" (the
# birthday-treat default): the endgame spirits and the elite X sample roll
# at legendary weight wherever a weighted pick sees them (2026-07-26).
_WEIGHT_OVERRIDE = {k: TIER_WEIGHT["legendary"] for k in (
    "x_program",
    "human_fire_spirit", "human_light_spirit", "human_ice_spirit",
    "human_wind_spirit", "human_thunder_spirit", "human_earth_spirit",
    "human_water_spirit", "human_wood_spirit", "human_metal_spirit",
    "human_dark_spirit",
    "beast_fire_spirit", "beast_light_spirit", "beast_ice_spirit",
    "beast_wind_spirit", "beast_thunder_spirit", "beast_earth_spirit",
    "beast_water_spirit", "beast_wood_spirit", "beast_metal_spirit",
    "beast_dark_spirit")}


def tier_weight(key):
    """Roll weight for `key` -- the find pools and any weighted shelf pick."""
    if key in _WEIGHT_OVERRIDE:
        return _WEIGHT_OVERRIDE[key]
    v = CATALOG.get(key)
    return TIER_WEIGHT.get((v.tier if v else None) or "common", 1)


def tier_stock(key):
    v = CATALOG.get(key)
    return TIER_STOCK.get((v.tier if v else None) or "common", 1)


_ROAD_ONLY = frozenset({"town_transport", "disaster_transport",
                        "life_recovery",
                        # the expansion (2026-07-26): the escape rope and
                        # the portable camp are road tools like their kin
                        "zone_transport", "continent_transport"})

# THE catalog: the authored table, field-named.  Everything downstream
# reads this, never `_AUTHORED`.
CATALOG = {
    _k: Item(*_v,
             touches=_TOUCHES.get(_k, ()),
             where="road" if _k in _ROAD_ONLY else "home",
             tier=tier_for_price(_v[2]))
    for _k, _v in _AUTHORED.items()
}

# the road's shelf unlocks by CLEARING MAPS (the profile `maps` set): once a
# tamer has beaten a continent, the transports/recovery it needs go on sale.
# key -> how many maps must be cleared.  Same earned-access rule as the eggs.
ADVENTURE_GATES = {
    "town_transport": 1, "disaster_transport": 1, "life_recovery": 2,
    # the expansion (2026-07-26): the escape rope opens with the first
    # cleared map; the portable camp is the deepest tool (matches its kin)
    "zone_transport": 1, "continent_transport": 2,
}


def adventure_open(key, prog=None):
    """Is this road-shelf item unlocked (enough maps cleared)?  Non-gated keys
    are always open."""
    need = ADVENTURE_GATES.get(key)
    if need is None:
        return True
    if prog is None:
        import tuipet.utils.persistence as persistence
        prog = persistence.get_progress()
    return len(prog.get("maps", ()) or ()) >= need


# sprite icon (i:/f:) -> the CATALOG key that wears it: adventure loot is
# authored by data id, but the bag/use system speaks CATALOG keys (the same
# "the bag could neither show nor use" trap the i:32 heal fixed) -- so found
# loot maps back through this to a real, usable entry.
_BY_ICON: dict[str, str] = {}
for _k, _v in CATALOG.items():
    _BY_ICON.setdefault(_v.icon, _k)


def key_for_icon(icon):
    """The CATALOG key whose sprite is `icon`, or None (unmapped loot).
    A RETIRED key's icon resolves to its heir -- authored loot rows, cup
    prizes and town stock lines written against a cut item keep paying."""
    k = _BY_ICON.get(icon)
    if k is not None:
        return k
    old = _RETIRED_ICONS.get(icon)
    return RETIRED.get(old) if old else None


# Which frame of an item's sheet IS the item, for every still cell that
# shows one (shop row, bag row, adventure find).  Frame 0 otherwise.
#
# The Music Player's sheet leads with a generic disc that isn't the item at
# all -- the box is frame 1 (Joel 2026-07-27: "the icon shpuld be what the
# other frame is, and the icon shouldnt even be used").  The MusicBox fx
# skips the disc too, so frame 0 of i:9 is now drawn nowhere.
_ICON_FRAME = {"music_player": 1}

# ...and when NO frame of an item's sheet can survive the 10-column cell,
# the cell borrows a DIFFERENT rip outright (Joel 2026-07-28: "use the orb").
# i:9's box is 13px wide with a note-trail overhead -- at cell scale it
# crunched to a smudge; the beamed-note orb (special 42, Gekomon's own shot,
# the same rip the MusicBox show flies) is natively 8x8 and fits the cell
# 1:1.  Still-cells only: the SHOW keeps playing the box's real frames.
_ICON_ART = {"music_player": ("special", "42")}


def icon_art(key):
    """A still-cell's substitute sprite for `key` (catalog key or raw icon
    key), or None to use the sheet frame.  Falls back to None if the orb
    bank is missing so the frame path always still renders something."""
    k = key if key in CATALOG else (key_for_icon(key) or "")
    ref = _ICON_ART.get(k)
    if not ref:
        return None
    import tuipet.data.loaders.data_world as data_world
    group, idx = ref
    return (data_world.load_orbs().get(group) or {}).get(idx)


def icon_frame(key):
    """The display frame for a CATALOG key or a raw icon key ('i:9')."""
    k = key if key in CATALOG else (key_for_icon(key) or "")
    return _ICON_FRAME.get(k, 0)

# compat views over the one table (shelf text / icons / tests import these)
EFFECTS = {k: v.effect for k, v in CATALOG.items()}
ICON_KEYS = {k: v.icon for k, v in CATALOG.items()}
FLAVORS = {k: v.flavor for k, v in CATALOG.items()}   # the dossier taglines

# (FOOD_KEYS -- the Food-category set -- CUT 2026-07-25 on Joel's order.
# It was the SECOND answer to "is this eaten", and the item-show audit
# 2026-07-23 already settled that question on the SHEET: item_is_eaten
# reads the `f:` prefix, which is why the six food-sheet consumables --
# both drinks, both pills, the vitamin, the anti-evo chip -- eat like the
# pill instead of flashing text.  The category set said NO to all six, so
# the two never agreed; it had no live consumer left by the item sweep.
# Do not reintroduce a second is-it-eaten test.)
# Items whose use has its OWN door and must never be hijacked by a
# generic item show: the memory chip's inherit flow, the two road
# transports and the road's Life Recovery (all spent on the march), and
# the Revive Floppy -- its canon type is Play, but it is used on a DEAD
# pet and the bag is unreachable at the grave, so that show could only
# ever be wrong or unplayable (item-show audit 2026-07-23).
_OWN_FLOW = frozenset({"memory", "town_transport", "disaster_transport",
                       "life_recovery", "revive_floppy",
                       # the expansion (2026-07-26): evolution keys play the
                       # evolution itself; the road tools and the futon run
                       # their own doors
                       "zone_transport", "continent_transport", "futon",
                       "datatron", "horn_helmet", "grey_claws",
                       "water_bottle", "torn_tatter", "white_wings",
                       "black_wings", "metal_armor", "flaming_wings",
                       "human_fire_spirit", "human_light_spirit",
                       "human_ice_spirit", "human_wind_spirit",
                       "human_thunder_spirit", "human_earth_spirit",
                       "human_water_spirit", "human_wood_spirit",
                       "human_metal_spirit", "human_dark_spirit",
                       "beast_fire_spirit", "beast_light_spirit",
                       "beast_ice_spirit", "beast_wind_spirit",
                       "beast_thunder_spirit", "beast_earth_spirit",
                       "beast_water_spirit", "beast_wood_spirit",
                       "beast_metal_spirit", "beast_dark_spirit"})


def item_is_eaten(key):
    """True when USING this item should play the EAT show.

    The canon rule is the SHEET (item-show audit 2026-07-23, Joel "do
    the eat show for the consumables too"): foods.csv carries no
    AnimationType column at all, because eating IS the animation --
    exactly how the pill already works ("the pill is EATEN, the
    source's EATING action, same as meat", pill-anim fix 2026-07-18).
    So every `f:` item eats: the 11 foods as before, plus the six
    food-sheet CONSUMABLES that used to flash bare text -- both
    drinks, both pills, the vitamin and the anti-evo chip.  `i:`
    items take a script instead (see item_script)."""
    return ICON_KEYS.get(key, "").startswith("f:")


def item_script(key):
    """The canon SHOW for a catalog item, or None.

    ONE SOURCE (item-show audit 2026-07-23, Joel: "is all of that
    already wired in?"): items.csv carries an AnimationType for every
    row, and our icon key `i:N` IS that row id -- so the mapping is
    free.  This replaces TOY_SCRIPTS, a 7-entry hand-map that
    duplicated the column and left 19 items with ripped art and no
    show at all.  Returns None for anything without an implemented
    script, for own-door items, and for `f:` consumables -- food-sheet
    items are EATEN (foods.csv has no AnimationType at all) and ride
    the eat fx, exactly like the pill."""
    if key in _OWN_FLOW:
        return None
    import tuipet.utils.itemfx as itemfx
    if key in itemfx._SCRIPT_OVERRIDE:      # a canon type with no usable show,
        return itemfx._SCRIPT_OVERRIDE[key]  # remapped to a fitting one (2026-07-24)
    icon = ICON_KEYS.get(key, "")
    if not icon.startswith("i:"):
        return None
    act = (data.consumable_by_key(icon) or {}).get("action") or ""
    return act if act in itemfx.SCRIPTS else None

# old-catalog keys -> their heirs (the save-heal maps bags 1:1 on load;
# nobody loses goods when the shelf turns over)
# THE RETIRED LEDGER (item refactor 2026-07-27).  Every key cut by the
# refactor names an HEIR: owned copies convert 1:1 in the bag heal
# (persistence._heal_bag), and any authored channel still speaking the old
# icon -- a loot row, a cup prize, a town stock line -- resolves to the heir
# through key_for_icon's fallback below.  Nobody loses goods; no authored
# data goes dark.
# the icons the RETIRED keys wore, for key_for_icon's fallback (static on
# purpose: the rows are gone from CATALOG, so nothing can derive these; the
# test suite pins that every entry here names a live heir)
_RETIRED_ICONS = {
    "f:45": "nuts", "f:46": "oats", "f:48": "egg", "f:50": "guava",
    "f:47": "milk", "f:40": "chicken_soup", "f:29": "rice", "f:53": "salmon",
    "f:52": "beans", "f:39": "ice_cream", "f:9": "banana",
    "f:30": "bitter_herbs", "i:12": "balloon", "i:26": "bubble_bath",
    "i:11": "toy_car", "i:4": "stuffed_animal",
    # (no i:67 row: cold_compress WEARS the shower art now, so the live icon
    # table already routes it -- the shower literally continues as the compress)
    "i:82": "toilet",
}

RETIRED = {
    "balloon": "ball",
    "banana": "cake",
    "beans": "broccoli",
    "bitter_herbs": "book",
    "bubble_bath": "ball",
    "chicken_soup": "bread",
    "cold_shower": "cold_compress",
    "egg": "bread",
    "gluttons_platter": "giga_meal",
    "guava": "bread",
    "ice_cream": "cake",
    "milk": "bread",
    "nuts": "bread",
    "oats": "bread",
    "rice": "cheese",
    "salmon": "cheese",
    "stuffed_animal": "ball",
    "toilet": "port_potty",
    "toy_car": "ball",
}

LEGACY_KEYS = {
    "best_fruit": "tuna", "normal_fruit": "fish", "worst_fruit": "vegetable",
    "deadly_fruit": "poison_mushroom", "junk_food": "cheese_burger",
    "premium_meat": "steak", "super_carrot": "slim_drink",
    "care_mistake_eraser": "miracle_drink", "alarm_clock": "music_player",
    "time_gear": "grow_capsule", "training_pack": "dumbbell",
    "poop_clean_pill": "port_potty",
    # the inheritance chip circulated under its raw icon key -- a key the
    # bag could neither show nor use (gameplay audit 2026-07-19)
    "i:32": "memory",
}

# the crest eggs: used from the bag, they trigger the classic ARMOR evolution
# (Pet._crest_egg -> evolution.item_select via the Relic ids)
ARMOR_CATEGORY = "Armor-Spirit"

# the Relic waves (Joel 2026-07-17: "wire the gates") -- the canon
# discovery order, on the same earned-access rule as the egg carousel:
# sealed ones simply don't appear.  Courage & Hope open armor evolution
# from day one; the crest seven follow the FIRST armor evolution; the 02
# pair rides lifetime wins; Miracles is golden (raids); Destiny is the
# movie one (generation 5).  Gate signals are persistence.get_progress().
RELIC_GATES = {
    "egg_of_courage": None,
    "egg_of_hope": None,
    "egg_of_friendship": ("armor_evos", 1),
    "egg_of_love": ("armor_evos", 1),
    "egg_of_knowledge": ("armor_evos", 1),
    "egg_of_sincerity": ("armor_evos", 1),
    "egg_of_reliability": ("armor_evos", 1),
    "egg_of_light": ("wins", 25),
    "egg_of_kindness": ("wins", 25),
    "egg_of_miracles": ("raids", 2),
    "egg_of_destiny": ("max_gen", 5),
}


def relic_open(key, prog=None):
    """Is this Relic's wave reached?  (Non-relic keys are open.)"""
    gate = RELIC_GATES.get(key)
    if gate is None:
        return True
    if prog is None:
        import tuipet.utils.persistence as persistence
        prog = persistence.get_progress()
    sig, need = gate
    return int(prog.get(sig, 0)) >= need


# --- per-town egg market (Joel 2026-07-21: "different towns sell different
# eggs -- all shops feel unique").  Each town stocks a DISTINCT band of the
# earnable egg, shown as the real 8x8 egg thumbnails; buying one owns it
# outright (bits -> persistence.egg_own).  Eggs still unlock FREE by condition
# elsewhere -- a town is the road shortcut, priced.
EGG_STOCK_PER_TOWN = 6


def _sellable_eggs():
    """The egg a town may stock: every egg that ISN'T a free starter
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
    while len(pool) > 1 and _gcd(stride, len(pool)) != 1:
        stride += 1
    start = (int(town_id) * stride) % len(pool)
    return [pool[(start + i) % len(pool)] for i in range(count)]


def egg_price(idx):
    """A town egg's bit price -- earned eggs are a treat, so the buy-outright
    shortcut costs real bits.  Starters (never stocked) are free."""
    import tuipet.data.loaders.data as data
    rule = data.load_egg_unlock().get(idx) or {}
    return 0 if rule.get("start") else 800

# (the DVPet staple props -- Toilet/Port. Potty/Futon, items.csv 81-83, and
# their uses/cap stock maths -- left 2026-07-17: strict-DSprite items
# ("go strict").  DSprite's catalog has no furniture; the shelf is exactly
# vitems.json.)

# the source shop prices any entry with no explicit price at a flat default
# (`e.price || 1e3`); the 11 crest eggs ship priceless, so without this they
# never reach the shelf.  Faithful to the source default, not invented.
DEFAULT_PRICE = 1000

def _price(v):
    return int(v.get("price") or DEFAULT_PRICE)


def _usable(key, category):
    """Only goods Pet.use_item can actually APPLY are sold.  Since the
    TUIPET catalog (2026-07-18) the consumables are authored in CATALOG;
    vitems contributes only the Relics (its theme_* skins,
    storage_drive and retired consumables never reach the shelf)."""
    return category == ARMOR_CATEGORY or key in CATALOG


def catalog():
    """Every buyable entry: [{key, name, price, category}], price order.
    The consumable shelf is the authored CATALOG (price None = unsold);
    the 11 Relics still come from vitems.json.  A Relic whose
    wave isn't reached is SEALED: it stays off the shelf entirely (the
    egg-carousel rule), though entry() still resolves it so an
    already-owned one renders in the bag."""
    import tuipet.utils.persistence as persistence
    prog = persistence.get_progress()
    out = []
    for k, v in CATALOG.items():
        if v.price is not None and adventure_open(k, prog):  # road shelf gated by maps
            out.append({"key": k, "name": v.name, "price": v.price,
                        "category": v.category})
    for k, v in data.load_vitems().items():
        if isinstance(v, dict) and v.get("category") == ARMOR_CATEGORY \
                and relic_open(k, prog):
            out.append({"key": k, "name": v.get("name", k),
                        "price": _price(v),
                        "category": ARMOR_CATEGORY})
    out.sort(key=lambda e: (e["category"], e["price"], e["name"]))
    return out


def entry(key):
    """Resolve any key: the authored CATALOG first (an unsold treat still
    renders in the bag at a nominal resale), then vitems (Relics)."""
    c = CATALOG.get(key)
    if c is not None:
        return {"key": key, "name": c.name,
                "price": c.price if c.price is not None else 100,
                "category": c.category}
    v = data.load_vitems().get(key)
    if not isinstance(v, dict):
        return None
    return {"key": key, "name": v.get("name", key),
            "price": _price(v),
            "category": v.get("category", "Item")}


def categories():
    have = {e["category"] for e in catalog()}
    out = [c for c in CATEGORY_ORDER if c in have]
    return out + sorted(have - set(out))


def shelf(cat):
    return [e for e in catalog() if e["category"] == cat]


# shelf tabs in PLAY order -- everyday care first, the relics last (shop
# polish 2026-07-17: the old alphabetical order opened the shop on a
# two-item Armor-Spirit tab).  Unknown categories append alphabetically.
# EIGHT TABS BY ACT (item refactor 2026-07-27, Joel: "all items need to be
# completely refactored and catagorized"): each tab names the thing the
# player wants to HAPPEN, in play order -- feed first, the doors late.
CATEGORY_ORDER = ("Feed", "Rest", "Cure", "Drill", "Modos", "Power",
                  "Tesouro", "Evoluir", "Road", ARMOR_CATEGORY)


def crest_answer(pet, key):
    """The forms THIS pet's armor jump would land right now -- the same
    evolution.check gate the crest egg runs on use (display only, no
    roll).  [] when nothing answers (not a crest key, egg/dead, gates
    unmet)."""
    import tuipet.core.evolution as evolution
    from tuipet.core.pet import Pet
    item_id = Pet._CREST_IDS.get(key, -1)
    if (item_id < 0 or pet is None or getattr(pet, "num", -1) < 0
            or getattr(pet, "dead", False) or pet.stage == "Egg"):
        return []
    _, by_num = data.load_sprites()
    return sorted({by_num[t]["name"]
                   for t in data.load_evolutions().get(pet.num, [])
                   if t in by_num and not data.is_placeholder(t)
                   and evolution.check(pet, t, item=item_id)})


# the sealed-wave tease texts, keyed by gate -- live numbers filled from
# persistence.get_progress() (the egg carousel's locked-hint pattern).
# Kept SHORT: they ride the 38-col shop footer, and footers never marquee.
_WAVE_TEASE = {
    ("armor_evos", 1): "your 1st armor evo wakes the crest 5",
    ("wins", 25): "wins {have}/25 wake Light & Kindness",
    ("raids", 2): "raids {have}/2 wake Miracles",
    ("max_gen", 5): "generation {have}/5 wakes Destiny",
}


def wave_status(prog=None):
    """(sealed_count, closest-wave tease) from live RELIC_GATES
    progress -- (0, '') once every relic is on the shelf."""
    if prog is None:
        import tuipet.utils.persistence as persistence
        prog = persistence.get_progress()
    sealed = [g for k, g in RELIC_GATES.items()
              if g is not None and not relic_open(k, prog)]
    if not sealed:
        return 0, ""

    def ratio(g):
        sig, need = g
        return min(1.0, int(prog.get(sig, 0)) / need)
    # DETERMINISTIC TIE-BREAK (shops audit 2026-07-25).  `max(set(...))`
    # walked a SET, so when two sealed waves tied on ratio the winner fell
    # out of string-hash iteration order -- which Python randomises PER
    # PROCESS.  Measured: the same save printed "wins 0/25 wake Light &
    # Kindness" or "generation 0/5 wakes Destiny" depending on the launch,
    # and 7% of sampled progress states tie (any player at gen 5+ with no
    # armor evo and no wins sits in one).  A shop's character is supposed
    # to be STABLE -- the same law that keeps a town's guest good crc32-
    # ordered and its deal fixed for the day.  Ties now break toward the
    # NEAREST goal in absolute terms (smallest `need`), which is also the
    # more useful tease: "your 1st armor evo" over "wins 0/25".
    sig, need = max(sorted(set(sealed)), key=lambda g: (ratio(g), -g[1]))
    have = min(int(prog.get(sig, 0)), need)
    tease = _WAVE_TEASE.get((sig, need), "mais relíquias surgem por aí")
    return len(sealed), tease.format(have=have, need=need)


def effect_line(e):
    if e.get("category") == ARMOR_CATEGORY:
        return "an armor evolution (the right Child)"
    k = e["key"]
    eff = EFFECTS.get(k, "uma curiosidade")
    fl = FLAVORS.get(k)
    # the dossier speaks effect AND character ("polish up the shop
    # descriptions" 2026-07-18) -- but the info block holds exactly two
    # 26-col rows, so a long effect keeps the stage to itself
    if fl:
        import textwrap
        joined = f"{eff} — {fl}"
        if len(textwrap.wrap(joined, 26)) <= 2:
            return joined
    return eff


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


# (the OLD town storefront chain -- home_shop_open / town_shop_open /
# town_shop_hours / roll_town_shop / slot_label / slot_info / sell_info /
# purchase_price + Pet.buy_slot -- CUT 2026-07-19, Joel: "cut the town
# chain".  The hours/rolled-slot machine stays dead.  What follows is the
# NEW town economy Joel ordered 2026-07-21 ("shops, town shops, deals"):
# deterministic, no rolls, no opening hours -- the authored data driving
# tuipet-idiom systems.)

# -- the town economy (shops arc, 2026-07-21) --------------------------------
# towns.csv override lists -> shopConsumable.csv econ rows -> CATALOG
# identities.  The 26 towns split into TWO authored stock families (a shared
# items shelf + two food families) -- that split IS the trade map: a town
# pays DEMAND rates for goods it doesn't stock.
TOWN_DEMAND_NUM, TOWN_DEMAND_DEN = 7, 10   # unstocked goods: towns pay 70%
#                                            (home pays 50%; canon towns pay
#                                            price//ResellFactor for their
#                                            OWN stock -- they have plenty)
TOWN_DAILY_CAP = 3        # tuipet's own per-(town,item,day) purchase bound.
#                           DVPet's 25-50-steak crates served ITS economy;
#                           against tuipet's catalog even ratio-scaled deal
#                           margins would compound into a printer at 50/day.

# PRICE LAW: a town price is the AUTHORED RATIO scaled to tuipet's catalog --
# catalog_price * row_price / DefaultPrice (the Default* cols are DVPet's own
# home economy, so the ratio IS the authored "towns discount steak 25%, halve
# chips, sell furniture at par" structure).  Raw row prices against tuipet's
# repriced catalog were money printers (375b steak vs 2000b catalog: +625
# per home flip); the ratio keeps every flip at-or-below water and makes
# DEALS the only trade window -- by design.


def _today_ordinal(today=None):
    import tuipet.core.tournament as tournament
    d = today if today is not None else tournament._today()
    return d.toordinal()


@lru_cache(maxsize=1)
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


# P4 (item diversity audit 2026-07-23, Joel: "do it all"): each MAP's
# towns carry ONE regional specialty beyond the authored base, so the
# five maps read differently before the guest good even lands.  REDEALT
# from the grown catalog (Joel 2026-07-26: "yeah redeal the specialties
# too") -- same depth logic, new faces: the starter map sells the toy
# surprise, the mid maps comfort and cunning, and the deep maps keep the
# premium-tier slots (the old map-4 Revive Floppy rule): map 4 deals the
# dark fluid, map 5 the gilded pill.
_MAP_SPECIALTY = {1: "chocolate_egg", 2: "futon", 3: "board_game",
                  4: "datatron", 5: "gold_pill"}


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
    foods, items = data._load_consumables()
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
    sk = _MAP_SPECIALTY.get(_town_maps().get(town_id))
    if sk and sk not in {k for _sid, k, _o, _p in rows}:
        rows.append((f"regional:{town_id}", sk, _econ_stub(sk),
                     CATALOG[sk].price))
    return rows


@lru_cache(maxsize=1)
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


_DEAL_LOOKBACK = 32          # days walked to stabilise the dedup chain


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


# the home shop's daily bargain -- half off, like a town deal, but home
# stays otherwise fixed-price (the reliable shelf).  Dealt from the always-
# stocked priced goods (no gated Adventure item, no egg), so the deal is
# never something you can't see on the shelf.
HOME_DEAL_FACTOR = 2


@lru_cache(maxsize=1)
def _home_deal_pool():
    return sorted(k for k, v in CATALOG.items()
                  if v.price is not None and v.category != "Road")


def home_deal_key(today=None):
    """The home shelf's ONE rotating daily deal key (2026-07-24, Joel: "add
    the home daily deal") -- seeded on the day, deduped vs yesterday."""
    pool = _home_deal_pool()
    i = _deal_index("home", len(pool), today)
    return pool[i] if i is not None else None


HOME_SHOP_ID = "home"        # the deal ledger's pseudo-town (see home_stock)

# keys whose contents out-value their price BY CONSTRUCTION (the capsule
# rolls the gift pool), so the always-open home shelf must ration them
# like a deal row or mint bits (expansion audit 2026-07-26)
HOME_RATIONED = frozenset({"capsule_a"})


# THE HOME COUNTER, refactored (2026-07-27, Joel: "shops need the same
# thing... daily items. not all at once like the home shop. basic items
# sure but cmon").  Home stops being the whole catalog on one wall.  It
# carries the STAPLES -- the basics a tamer must always be able to buy --
# and a rotating DAILY BAND drawn from everything else, tier-weighted so
# a legendary drops in rarely and a common often.  ~20 rows a day, and
# the week has texture.  Towns are untouched: they were already the
# curated half of the economy.
HOME_STAPLES = frozenset({
    # feed basics: the ladder's everyday rungs
    "fish", "bread", "cheese", "vegetable",
    # rest basics: the night and the tank
    "sleeping_pill", "music_player", "energy_drink",
    # drill + cure basics
    "dumbbell", "slim_drink", "supplement",
    # the gacha counter never closes -- its RATION is the guard, not absence
    "capsule_a",
})
HOME_BAND_SIZE = 10
