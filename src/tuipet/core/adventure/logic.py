"""Adventure — the MARCH engine (rebuild phase 2, 2026-07-20).

⛔ OWN-GAME LAW (Joel 2026-07-13, carried forward): DVPet is NOT canon for
adventures.  One biome per run, start to the goal, no mid-run scenery swap.

Built: the MARCH (cross a zone in ~INTERACTIVE_STEPS travel actions, the journey
on a ribbon, arrival ends the run); WILD ENCOUNTERS (a per-leg roll from the
zone's own enemy table, lives, win/flee/loss/fail); and the real 26-ZONE
GEOGRAPHY -- the zones come from data/zones.csv + enemies.csv (data.load_maps),
each wearing ONE biome (its gate boss's terrain, no mid-zone span-hopping) with
its own wild pool; the zone BOSS FIGHT -- reaching the end opens the gate boss
(resolve_boss), and FELLING it is the real victory (a loss costs a life, 0 lives
fails, a survivable loss lets the pet face it again); TRAVEL DRAIN -- each
marched leg tires (energy), burns the calorie buffer (weight trims toward base)
and tops the effort gauge, so a run comes home spent; TOWNS -- a mid-zone
waypoint refills lives, rests energy to at least half the tank and suppresses
encounters; and PROGRESSION --
pet.adv_progress tracks zones conquered (the frontier index); felling a zone's
boss unlocks the next, and the ZonePickPanel lets the player embark on any
unlocked zone; and FINDS -- a marched step may spot loot from the zone's own
table (rand_items/rand_foods) to dig up or pass; the home STATUS CARD (statusbox.adventure_line: Quest
N/26 on the home screen); and TRANSPORT items -- a town warp (Birdra) jumps to
the town and rests, a danger warp (Garuda) dashes toward the boss and gets
ambushed.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import math
import random
from functools import lru_cache

import tuipet.data.loaders.data as data
import tuipet.utils.backgrounds as backgrounds

INTERACTIVE_STEPS = 40    # a zone is crossed in ~40 travel actions (the compression
#                           knob the old engine used -- kept as the pacing unit)
MAX_LIVES = 3             # adventure lives (canon MaxAdventureLife): a loss costs one
ENCOUNTER_CHANCE = 0.20   # per leg -- ~8 wild fights over a 40-leg zone (the old
#                           engine's target, reached here with a clean per-leg roll
#                           instead of the per-controller-fire compound -- rebuilt,
#                           not cloned)
FIND_CHANCE = 0.12        # per marched step -- a chance to spot loot on the road
#                           (Zone.checkItem), ~3-4 finds over a zone; the player
#                           digs it up (into the bag) or walks on
SKIP_LEGS = 10            # the Zone Transport's safe lift (expansion 2026-07-26)
HAZARD_CHANCE = 0.06      # per marched step -- an ambush pounce on the road
#                           (arcade arc, Joel 2026-07-21 "do the hazard dodges"):
#                           a zone wild telegraphs and lunges; SPACE ducks it,
#                           eating it costs a small energy toll
HAZARD_ENERGY = 2         # the toll for eating a pounce (a SMALL hit -- the
#                           march drain is 1 per 4 legs for scale)
# THE ENERGY FLOOR LAW (D3 ruling 2026-07-23): a SPEND floors at zero, a
# KNOCK pushes past it.  Marching and battling are exertion the pet chooses
# to pay -- an empty tank can't fund them, so both floor at 0 (_march_drain
# here, record_battle in petbattle.py).  A hazard pounce is DAMAGE -- being
# blindsided can knock the pet past empty (hazard_hit, unfloored), and only
# that: negative energy is what plants its feet (check_stop_travel) and
# strands the run on the refuse strip's outs (T warp / ESC home -- and the
# warp reaches the nearest town in EITHER direction since 2026-07-25, so
# the out is real anywhere on the road, not just before the span).
# REPLAY DIFFICULTY (Joel 2026-07-21 "do the replay difficulty scaling"): a
# CONQUERED zone re-run is a VETERAN ROAD -- the same species fight TRAINED,
# through the real hit-formula terms (Side.hit_chance's trainings + winning-
# record legs, the very ones the pet earns), never invented stats; bounties
# pay half again for it.  No new persistence: "conquered" IS the tier.
VETERAN_TRAININGS = (500, 5000)   # trainings_cur/total: half each trained ceiling
VETERAN_RECORD = (100, 75)        # battles/wins: a 75% career (+wr term)
REPLAY_BITS_NUM, REPLAY_BITS_DEN = 3, 2   # veteran bounties: +50%

# the RUN SCORE (arcade arc, Joel 2026-07-21 "do the run score"): one number
# rolled from the tallies the summary card already shows, so a run can chase
# the zone's standing best (persistence.zone_bests).  Bits ride 1:1 (already
# streak/festival-scaled); the rest weight what the run DID.
SCORE_WIN = 10            # per fight won
SCORE_FIND = 5            # per find dug up
SCORE_LIFE = 25           # per adventure life still held at the end
SCORE_STREAK = 10         # per chained win past the first (the run's best chain)
SCORE_CONQUEST = 100      # the boss fell -- the run's whole point

STREAK_STEP = 0.25        # WIN STREAK (arcade arc, Joel 2026-07-21 "do the win
#                           streak bonus"): each chained win past the first
#                           adds +25% to bounties...
STREAK_CAP = 2.0          # ...capped at DOUBLE (the festival double's scale).
#                           A loss or a flee breaks the chain; so does any town
#                           rest -- and the mid-zone waypoint rests on ARRIVAL,
#                           so every crossing's chain resets there by design
#                           (truthed 2026-07-25: there is no push-on choice at
#                           the waypoint; the cap is earned on the far side).
HOLIDAY_BITS_MULT = 2     # festival purse: bounties pay double on a holiday
HOLIDAY_FIND_MULT = 2     # more loot spills on the road during a festival
FESTIVAL_PRESENT_CHANCE = 0.34   # ...and a third of festival finds are a
#                                  wrapped SURPRISE from the gift pool, not the
#                                  zone's loot -- home gifts are home-only, so
#                                  this is how the road celebrates (2026-07-24)
POST_FIGHT_GRACE = 1      # legs of encounter immunity after ANY fight (canon
#                           getBattleImmunity on a win, widened so the pet always
#                           takes a clear step between fights -- no same-spot re-jump)
# travel drain (WorldMap.checkEnergyDec, rebuilt clean): the march itself has a
# toll -- it tires (energy), burns the calorie buffer (weight trims toward base),
# and tops the effort gauge (travel is light training).  A drain tick lands every
# few legs so a full zone costs a real chunk of energy without being brutal; the
# old per-fire 80*fullHP threshold is replaced by this leg cadence (own-game).
WALK_DRAIN_EVERY = 4      # a drain tick every N marched legs
TRAVEL_ENERGY_DEC = 1     # energy spent per drain tick
TRAVEL_CALORIE_DEC = 1    # calories burned per drain tick
TRAVEL_EFFORT_CAP = 4     # walking tops the effort gauge (pet.strength) up to here
TOWN_REST_ENERGY = 6      # a town rest's top-up when already above half a tank;
#                           the rest itself reaches AT LEAST max_energy // 2
#                           (D1 ruling 2026-07-23 -- see _rest_up)

# the 26 real zones (5 maps: 7/7/3/2/7) are built from data/zones.csv +
# enemies.csv (data.load_maps).  Each run wears ONE biome (own-game law): the
# terrain its GATE BOSS stands in, NOT the mid-zone BackgroundsAndRange scenery
# the device span-hopped through.  habitats.csv habitat id -> a backgrounds.py
# scene key (the old habitat system left with BASIC VPET, so we re-map here):
HABITAT_SCENE = {
    0: "datatunnel",    # Hard Disk -- the net
    1: "mountains",     # Sky -- warm & high; no sky scene, so open mountains
    2: "greenhills",    # Plains
    3: "mountains",     # Canyon -- rugged rock
    4: "forestgate",    # Forest -- the tree path
    5: "frozenpeak",    # Tundra
    6: "islandsea",     # Ocean -- the coast
    7: "lakeside",      # Lake
    8: "underwater",    # Underwater -- the seafloor
    9: "factorynight",  # Evil Castle -- dark iron
    10: "flowerfield",  # Field
    11: "city",         # City
    12: "islandsea",    # Cliffside -- rock over open sea
    13: "greenhills",   # Town (unused as a zone biome, kept for completeness)
    14: "volcano",      # Volcano
    15: "desert",       # Desert
}
DEFAULT_SCENE = "greenhills"


def _boss_biome_hid(zone: Any) -> Any:
    """The zone's ONE biome habitat id: the terrain its gate boss STANDS in --
    the bgs span holding the boss's Location (bosses gate the zone's end).  No
    boss -> the terrain the pet spends the most steps in (dominant span)."""
    spans = sorted(zone.get("bgs", ()))
    if not spans:
        return None
    bosses = zone.get("bosses", ())
    if bosses:
        # the GATE boss (bosses[0] -- the one Adventure.boss actually
        # fights), NOT max(location): zone 6 carries a second, unreachable
        # boss (Apocalymon) whose span sat past Piedmon's, so the run wore
        # a biome its own gate boss never stands in (audit 2026-07-25)
        bl = bosses[0].get("location", 0)
        for lo, hi, hid in spans:
            if lo <= bl <= hi:
                return hid
        return spans[-1][2]                 # past the last span: the gate terrain
    cover = {}  # type: ignore
    for lo, hi, hid in spans:
        cover[hid] = cover.get(hid, 0) + max(0, hi - lo)
    return max(cover, key=lambda h: (cover[h], -h))


def _town_legs(z: Any) -> Any:
    """The zone's town step-spans mapped onto the ~40 interactive legs:
    [(leg_lo, leg_hi, town_id)] -- a mid-zone rest waypoint / visitable hub."""
    ts = max(1, z.get("total_steps", 1))
    out = []
    for lo, hi, tid in z.get("towns", ()):
        a = int(lo / ts * INTERACTIVE_STEPS)
        b = max(a, math.ceil(hi / ts * INTERACTIVE_STEPS))
        out.append((a, min(INTERACTIVE_STEPS - 1, b), tid))
    return out


# THE BIOME LOOT TABLE (item diversity audit 2026-07-23, Joel: "do it
# all").  The authored DVPet tables were per-SLOT -- 1-1 == 2-1 == 5-1,
# so Andromon's Desert, Kimeramon's Seafloor and Etemon's Mountains all
# dug the same Television -- and the catalog filter dropped 2/3 of their
# entries anyway (552 authored -> 182 usable).  Pools now key on the
# zone's BIOME (its scene), dealt from the EXISTING catalog only: no new
# items, no new systems, and the road finally FEEDS you (fish by the
# water, steak in the mountains).  The 3 road items ride every pool --
# they're the run tools.  The FINAL zone of each map digs the RARE TIER
# instead: the endgame used to dig exactly one item (the chip).
_ROAD_KEYS = ("town_transport", "disaster_transport", "life_recovery")
# D5 (2026-07-24, Joel "make them findable"): cookie + cupcake join the
# gentle biomes alongside candy, the third grant-only treat -- which has
# ALWAYS been a road find here, so this only brings its two siblings in
# line.  (memory joined the data biomes the SAME day: the later wild-
# payload ruling gave a found chip a real 5-15 point payload
# (petcare.stash_wild_memory), so the old "a wild chip is a silent dud"
# objection died with it -- it sits in datatunnel/factorynight below,
# truthed 2026-07-25.)
BIOME_FINDS = {
    # the expansion rows (2026-07-26) join their fitting biomes: farmland
    # eggs and meat, forest nuts, mountain cheeses, a pepper by the lava --
    # the road FEEDS you in that biome's own voice, and two of the shy
    # capsules hide out where treasure hunters go.
    "greenhills":   ("fish", "vegetable", "ball", "candy", "cupcake",
                     "meat"),
    "flowerfield":  ("vegetable", "candy", "music_player", "ball", "cookie",
                     "honey", "fruit"),
    "forestgate":   ("poison_mushroom", "vegetable", "candy", "music_player"),
    "mountains":    ("dumbbell", "steak", "grow_capsule",
                     "cheese", "bread", "red_pepper"),
    "frozenpeak":   ("caffeine_pill", "steak", "vitamin"),
    "islandsea":    ("tuna", "fish", "skateboard", "ball", "cupcake",
                     "orange"),
    "lakeside":     ("fish", "tuna", "vegetable", "cookie"),
    "underwater":   ("fish", "tuna", "slim_drink", "capsule_b"),
    "city":         ("video_game", "television", "energy_drink",
                     "cheese_burger", "skateboard", "computer_game", "capsule_c"),
    "datatunnel":   ("energy_drink", "anti_evo_chip", "video_game",
                     "caffeine_pill", "memory", "computer_game",
                     "capsule_c"),
    "factorynight": ("anti_evo_chip", "dumbbell", "energy_drink",
                     "sleeping_pill", "memory", "capsule_d",
                     "supplement"),
    "volcano":      ("steak", "energy_drink", "dumbbell",
                     "red_pepper"),
    "desert":       ("tuna", "energy_drink", "vitamin", "slim_drink",
                     "yellow_pepper", "orange"),
}
FINAL_ZONE_FINDS = ("anti_evo_chip", "x_antibody", "textbook",
                    "dna_crystal", "steak", "hp_chip")

# the road's festival present pool: the ten authored capsule boxes -- eight
# honest, two AngrySurprise pranks, identical until opened (that IS the box)
_FESTIVAL_CAPSULES = ("capsule_a", "capsule_b", "capsule_c", "capsule_d",
                      "capsule_e", "capsule_f", "capsule_g", "capsule_h",
                      "prank_capsule_a", "prank_capsule_b")


def _find_keys(scene: Any, is_final: bool) -> Any:
    """The zone's discoverable loot as CATALOG keys: its biome's pool (or
    the rare tier for a map's final zone), with the road items riding
    along.  (The per-slot authored tables retired 2026-07-23 -- see
    BIOME_FINDS above; dormant rand_items/rand_foods stay in the data.)"""
    pool = (FINAL_ZONE_FINDS if is_final
            else BIOME_FINDS.get(scene) or BIOME_FINDS[DEFAULT_SCENE])
    return list(_ROAD_KEYS) + list(pool)


@lru_cache(maxsize=1)
def _real_zones() -> Any:
    """The 26 zones as run-zones: name (its biome + the gate boss that guards
    it), the one biome scene, a uniform ~40-leg crossing, the zone's OWN wild
    pool (its randoms), its town waypoints (leg-ranges that rest + suppress
    encounters), and its discoverable loot pool (find_keys)."""
    out = []
    for mp in data.load_maps():
        last = max(z["zone"] for z in mp["zones"])
        for z in mp["zones"]:
            hid = _boss_biome_hid(z)
            scene = HABITAT_SCENE.get(hid, DEFAULT_SCENE)
            label = backgrounds.name(scene)
            bosses = z.get("bosses", [])
            name = f"{bosses[0]['name']}'s {label}" if bosses \
                else f"{label} {z['map']}-{z['zone']}"
            out.append({
                "name": name,
                "scene": scene,
                "steps": INTERACTIVE_STEPS,
                "randoms": z.get("randoms", []),
                "bosses": bosses,
                "town_legs": _town_legs(z),
                "find_keys": _find_keys(scene, z["zone"] == last),
                "map": z["map"], "zone": z["zone"],
            })
    return out


# a safe fallback if the world data is missing (pre-setup): one plain zone so
# the panel never crashes on an empty roster.
_FALLBACK_ZONE = {"name": "Green Hills", "scene": DEFAULT_SCENE,
                  "steps": INTERACTIVE_STEPS, "randoms": [], "bosses": [],
                  "town_legs": [], "find_keys": []}
ZONES = tuple(_real_zones()) or (_FALLBACK_ZONE,)


def active_holiday(today: Optional[Any]=None) -> Any:
    """Today's festival name (double bits + more finds on the road), or None.
    Reuses the cup's date/holiday cadence -- ONE source for 'what day is it'."""
    import tuipet.core.tournament as tournament
    return tournament.holiday(today)


def pick_zone(pet: Any) -> Any:
    """A zone when none is chosen (tests, or a default embark): the pet's
    frontier zone -- the newest one it has unlocked.  The zone-pick UI lets the
    player choose any UNLOCKED zone instead (progression phase)."""
    idx = unlocked_indices(pet)
    return ZONES[idx[-1]] if idx else ZONES[0]


# -- progression --------------------------------------------------------------
# pet.adv_progress = zones CONQUERED (a count).  The road runs in DIFFICULTY
# ORDER (balance audit 2026-07-21, Joel's option b): the Monte-Carlo sweep
# over the real Battle engine showed zones.csv order was non-monotonic --
# Mega wilds in map 1's zone 3, an 11% boss at zone 2, the endgame map 5
# EASIER than map 1's back half, the all-Mega zone 16 cliff mid-game.  Win
# rate tracks the rosters' stage ranks, so PROGRESSION sorts by that key --
# self-documenting, roster-untouched, and it re-derives if the data changes.
# Zone IDENTITY (list index) is untouched: score bests, names, and the map
# field all stay keyed as before; only the ORDER you meet them changed.


def _difficulty(z: Any) -> Any:
    """The zone's deterministic difficulty key: mean wild stage rank + gate
    boss rank (the measured win-rate driver)."""
    from tuipet.core.battle import _RANK
    wilds = [e for e in z.get("randoms", ()) if not e.get("boss")]
    wr = (sum(_RANK.get(e.get("stage"), 3) for e in wilds) / len(wilds)
          if wilds else 3.0)
    bs = z.get("bosses") or []
    br = _RANK.get(bs[0].get("stage"), 3) if bs else 3
    return wr + br


PROGRESSION = sorted(range(len(ZONES)),
                     key=lambda i: (_difficulty(ZONES[i]), i))
_ORDER_POS = {zi: pos for pos, zi in enumerate(PROGRESSION)}


# ---------------------------------------------------------------------------
# ZONE SIGNATURES (distribution arc, 2026-07-24 -- Joel ruled D3 "both" and
# D4 "give them distinct loot").
#
# One item that ONLY this zone drops, appended to its biome pool.  A single
# mechanism answers both rulings: it makes every zone's loot unique, which
# is exactly what the eight factorynight zones needed -- they shared one
# scene and therefore dug identical loot, a third of the map reading the
# same.  Signatures are per-ZONE, so the shared scene stops mattering.
#
# The item is matched to the zone's DEPTH: the run's opening stops sign
# common goods, the last stops sign legendary ones, using the same tier
# ladder the shelves read (shop.tier_for_price).  Within a band, items that
# are currently found NOWHERE are handed out first -- so the signature pass
# also closes the "never a find" gap instead of needing its own mechanism.
#
# Deterministic: crc32 over the key, so a zone's signature is PERMANENT (the
# guest-good law -- a place's character must not reshuffle between runs).
# 8 + 8 + 5 + 5 = the 26 zones.  The rare band is exactly 5 because the five
# FINAL_ZONE_FINDS are held back from signing (see _assign_signatures): a
# signature is STRIPPED from every other pool, and signing x_antibody would
# have quietly robbed every map's final zone of the rare tier it exists to
# hand out.  The endgame table outranks the signature pass.
_SIG_BANDS = (("common", 8), ("uncommon", 8), ("rare", 5), ("legendary", 5))


def _assign_signatures() -> Any:
    """Give every zone its own exclusive find.  Returns {zone_index: key}."""
    import zlib
    import tuipet.core.shop as shop
    # Read the BASE tables, never the live ZONES: this pass APPENDS to
    # find_keys, so reading the zones back would make the "unfound first"
    # sort depend on whether the pass had already run -- and a second call
    # would deal a different hand.  Signatures must be permanent.
    already = set(_ROAD_KEYS) | set(FINAL_ZONE_FINDS)
    for _pool in BIOME_FINDS.values():
        already.update(_pool)
    # never a signature: the road trio (they ride EVERY pool already), and
    # every GRANT-ONLY good -- the birthday treats and the Memory are
    # deliberately unbuyable gifts (item diversity audit 2026-07-23, "by
    # design"), and making them road loot would quietly undo that.
    # ...and never the endgame table: a signature is exclusive, so signing
    # one of these would strip it from every map's final zone.
    banned = set(_ROAD_KEYS) | set(FINAL_ZONE_FINDS)
    by_tier = {}  # type: ignore
    for key, v in shop.CATALOG.items():
        if key in banned or v.price is None:
            continue
        by_tier.setdefault(v.tier or "common", []).append(key)
    for tier, keys in by_tier.items():
        # unfound first, then a stable crc32 shuffle
        keys.sort(key=lambda k: (k in already, zlib.crc32(f"sig:{k}".encode())))
    out, pos = {}, 0
    for tier, count in _SIG_BANDS:
        pool = by_tier.get(tier) or []
        for i in range(count):
            if pos >= len(PROGRESSION):
                break
            if not pool:
                pos += 1
                continue
            out[PROGRESSION[pos]] = pool[i % len(pool)]
            pos += 1
    return out


ZONE_SIGNATURE = _assign_signatures()
_SIGNED = set(ZONE_SIGNATURE.values())
for _zi, _z in enumerate(ZONES):
    _mine = ZONE_SIGNATURE.get(_zi)
    # EXCLUSIVE means exclusive: a signature is stripped from every OTHER
    # zone's pool.  Most signatures are drawn from items no biome carried,
    # but the deeper bands run out of those, and a "signature" the zone
    # next door also digs is just a label.
    _z["find_keys"] = [_k for _k in _z["find_keys"]
                       if _k not in _SIGNED or _k == _mine]
    if _mine and _mine not in _z["find_keys"]:
        _z["find_keys"].append(_mine)
    _z["signature"] = _mine

# THE HUMAN SPIRITS WAIT ON THE DEEP ROADS (item expansion 2026-07-26):
# the ten hardest zones by PROGRESSION each hide ONE Human spirit in their
# dig pool -- never sold, legendary-weighted (shop's override), element
# order matched to depth so the Dark spirit guards the very last road.
# Their Beast halves are CUP prizes (tournament.py): roads give Human,
# cups give Beast.
_HUMAN_SPIRITS = ("human_fire_spirit", "human_light_spirit",
                  "human_ice_spirit", "human_wind_spirit",
                  "human_thunder_spirit", "human_earth_spirit",
                  "human_water_spirit", "human_wood_spirit",
                  "human_metal_spirit", "human_dark_spirit")
for _pos, _zi in enumerate(PROGRESSION[-len(_HUMAN_SPIRITS):]):
    if _HUMAN_SPIRITS[_pos] not in ZONES[_zi]["find_keys"]:
        ZONES[_zi]["find_keys"].append(_HUMAN_SPIRITS[_pos])
def zone_index(zone: Any) -> Any:
    """The index of a zone dict in the ordered ZONES, or None (a test zone)."""
    try:
        return ZONES.index(zone)
    except ValueError:
        return None


def frontier(pet: Any) -> Any:
    """The ZONES index of the pet's current frontier zone: the next stop on
    the difficulty road (clamped to the last stop)."""
    prog = max(0, min(int(getattr(pet, "adv_progress", 0) or 0),
                      len(PROGRESSION) - 1))
    return PROGRESSION[prog]


def unlocked_indices(pet: Any) -> Any:
    """The zone indices the pet may embark on, in ROAD order: everything up
    to and including the frontier."""
    prog = max(0, min(int(getattr(pet, "adv_progress", 0) or 0),
                      len(PROGRESSION) - 1))
    return PROGRESSION[:prog + 1]


def is_conquered(pet: Any, zi: Any) -> Any:
    """Has the pet already felled this zone's boss (its road position sits
    below the conquered count)?"""
    pos = _ORDER_POS.get(zi)
    return pos is not None and pos < int(getattr(pet, "adv_progress", 0) or 0)


def _veteran(enemy: Any) -> Any:
    """A conquered zone's foe, replayed: the SAME species carrying a
    trained veteran's Side -- the real hit-formula terms (trainings, a
    winning record), which Battle consumes via enemy['side'].  Returns a
    scaled COPY: zone dicts are shared and cached, never mutated."""
    from tuipet.core.battle import Side
    e = dict(enemy)
    s = Side.wild(e.get("num", 0), boss=bool(e.get("boss")))
    s.trainings_cur, s.trainings_total = VETERAN_TRAININGS
    s.battles, s.wins = VETERAN_RECORD
    e["side"] = s
    e["veteran"] = True
    return e


def is_map_cleared(pet: Any, map_num: Any) -> Any:
    """Are ALL of a map's zones conquered (every one below the frontier)?  This
    is the profile `maps` signal that unlocks the road shop shelf + eggs."""
    idxs = [i for i, z in enumerate(ZONES) if z["map"] == map_num]
    # road-order aware (option b, 2026-07-21): a map is cleared when every
    # one of ITS zones is conquered, wherever they now sit on the road
    return bool(idxs) and all(is_conquered(pet, i) for i in idxs)


def record_win(pet: Any, zone: Any) -> Any:
    """A boss felled: if it was the FRONTIER, the next stop on the road
    unlocks.  Replaying an already-conquered zone advances nothing.
    Returns True if a zone unlocked."""
    zi = zone_index(zone)
    prog = int(getattr(pet, "adv_progress", 0) or 0)
    if (zi is not None and prog < len(PROGRESSION)
            and _ORDER_POS.get(zi) == prog):
        pet.adv_progress = prog + 1
        return True
    return False


