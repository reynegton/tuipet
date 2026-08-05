from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import json
import os
import time
from dataclasses import MISSING, asdict, fields
from tuipet.core.pet import Pet
from tuipet.core.petbase import (FRESH_OBEDIENCE, IN_TRAINING_OBEDIENCE,
                      ROOKIE_OBED_DEFAULT)
from tuipet.core.eggmigrate import (  # noqa: F401
    EGG_ORDER_V, _CLASSIC49, _CUT_FALLBACK, _V401_FULL, _V402_FULL,
    _V403_FULL, _V404_FULL, _current_names, _find_occurrence,
    _migrate_egg_index, _migrate_v401_save, _migrate_v401_settings,
    _sane_owned, _table_for)
from tuipet.utils.persistio import (  # noqa: F401
    SAVE_DIR, SAVE_PATH, SETTINGS_PATH, _LOCK_NAME,
    _atomic_write_json, _can_use, _pick_save_dir, acquire_instance_lock,
    release_instance_lock, write_crash_log)
import tuipet.utils.persistio as _persistio

from .settings_io import load_settings, save_settings


def snapshot_prev_gen(pet: Any) -> None:
    """Record the just-ended pet's traits for the 'previous generation' egg
    gates -- and the careBonusOnReset math (death/rebirth audit 2026-07-06):
    the ended life's care ADJUSTS the bonus the next generation inherits.
    Canon never zeroes _bonus on resetToEgg; tuipet carries it through this
    channel instead."""
    if pet is None or getattr(pet, "stage", "Egg") == "Egg":
        return
    # (the careBonusOnReset math moved to Pet.final_care_grade -> the
    # bonus_seed channel -- this copy was a second, PARTIAL grading of the
    # same life that the seed always stomped; memory audit 2026-07-06)
    d = load_settings()
    prog = d.setdefault("progress", {})
    prog["last_gen"] = {
        "field": getattr(pet, "field", "") or "None",
        "attribute": getattr(pet, "attribute", "") or "None",
        "mood": int(getattr(pet, "mood", 0)),
        "obedience": int(getattr(pet, "obedience", 0)),
        "xanti": getattr(pet, "x_antibody", "None") != "None",
        # the DEVICE BAG (item/inventory audit 2026-07-06): canon's resetToEgg
        # never touches bits, the bag, or the beaten-qualifier trophies --
        # they are device-lifetime; the heir inherits them all
        "bits": int(getattr(pet, "bits", 0)),
        "inventory": dict(getattr(pet, "inventory", {}) or {}),
        "trophies": int(getattr(pet, "trophies", 0)),
        "trophies_won": dict(getattr(pet, "trophies_won", {}) or {}),
        # the BANKED DNA is device-lifetime too (DNA polish 2026-07-17):
        # it is bought with bits + the mash minigame, so wiping it at
        # rollover made late-life banking worthless.  The CHARGED
        # distribution (dna_applied) is the pet's own biology and dies
        # with it, exactly as before.
        "dna_owned": dict(getattr(pet, "dna_owned", {}) or {}),
    }
    # the LEGACY roll (sweep 2026-07-14): every retired generation used to
    # vanish -- only this gate snapshot survived, and it was never SHOWN.
    # Bank a small headstone per life for the datacore LEGACY page.
    legacy = prog.setdefault("legacy", [])
    legacy.append({
        "gen": int(getattr(pet, "generation", 1)),
        "name": getattr(pet, "name", "") or "?",
        "stage": getattr(pet, "stage", "?"),
        "age": float(getattr(pet, "age_seconds", 0.0)),
        "cups": int(getattr(pet, "trophies", 0)),
        "dead": bool(getattr(pet, "dead", False)),
        # the HALL OF MEMORY fields (Joel 2026-07-26 "build the hall of
        # memory"): the individual, not just the count -- its form for the
        # portrait, what took it, and its fight record.  Headstones from
        # before this date miss them; the hall shows the grave and says
        # only what it knows.
        "num": int(getattr(pet, "num", 0)),
        "cause": getattr(pet, "death_cause", "") or "",
        "wins": int(getattr(pet, "wins", 0)),
        "battles": int(getattr(pet, "battles", 0)),
    })
    del legacy[:-30]                 # the book keeps the 30 most recent elders
    save_settings(d)

def _heal_bag(inv: Any) -> Any:
    """The bag heal, both eras in one pass: shed the dead staple props
    (strict-DSprite 2026-07-17) and map the retired catalog's keys onto
    their TUIPET heirs 1:1 (shop.LEGACY_KEYS; catalog turnover 2026-07-18
    -- nobody loses goods)."""
    import tuipet.core.shop as shop
    # "bandage" is a dead key AGAIN (Joel 2026-07-26, on seeing the
    # expansion's 10b pocket med: "cut it out, i think its supposed to
    # just be used for the animations for heal") -- the wrap belongs to
    # the H heal's Bandaging show, not to a bag row.  It was live for
    # about an hour of 0.5.283/284, so this heals out at most a couple of
    # 10b purchases (the R3 precedent).  The raw-icon keys are ancient-
    # save cruft; the surviving expansion items wear snake_case keys
    # (futon / toilet / port_potty).
    for dead in ("i:80", "i:81", "i:82", "i:83", "bandage"):
        inv.pop(dead, None)
    # ...and the 2026-07-27 refactor's RETIRED ledger rides the same door:
    # every cut key converts 1:1 to its named heir, same as the 07-18
    # turnover -- nobody loses goods
    for old, new in {**shop.LEGACY_KEYS, **shop.RETIRED}.items():
        n = inv.pop(old, 0)
        if n:
            inv[new] = inv.get(new, 0) + n
    return inv

def prev_gen_estate() -> Any:
    """The device-lifetime estate the next generation inherits (bits, the bag,
    the trophy room -- canon resetToEgg preserves them all)."""
    d = load_settings()
    last = (d.get("progress") or {}).get("last_gen") or {}
    # JSON stringifies int dict keys (the trophies_won load trap): coerce
    # them back so prelim-chain lookups keep matching
    tw = {int(k) if str(k).lstrip("-").isdigit() else k: v
          for k, v in (last.get("trophies_won") or {}).items()}
    inv = _heal_bag(dict(last.get("inventory") or {}))
    # memory items never ride the estate bag (2026-07-24): the inherited
    # PAYLOAD travels via the bank channel (take_memory -> _grant re-adds
    # exactly one chip), and a WILD chip's trace is within-life loot that
    # fades with its finder.  Carrying the item without its payload would
    # deal the heir a dud -- the very thing the no-traps rule forbids.
    inv.pop("memory", None)
    return {"bits": int(last.get("bits", 0)),
            "inventory": inv,
            "trophies": int(last.get("trophies", 0)),
            "trophies_won": tw,
            "dna_owned": dict(last.get("dna_owned") or {})}

def to_save_dict(pet: Any) -> Any:
    """The on-disk/cloud save payload: the flat pet plus a wall-clock stamp used
    for offline catch-up AND last-write-wins cloud merge."""
    data = asdict(pet)
    data["_saved_at"] = time.time()
    data["egg_order_v"] = EGG_ORDER_V   # marks post-.402 egg indices (migration guard)
    return data

def pet_from_save(data: Any, strict: bool=False) -> Any:
    """Build (pet, message) from a save dict (disk or cloud). Returns (None, '')
    on malformed data.

    NOTHING is applied for time spent away: a closed game is a STOPPED clock
    (Joel 2026-07-22, "we gotta remove it").  The bounded offline catch-up
    that used to run here -- age, growth, hunger, poop, sleep -- is gone with
    the `catch_up` flag that gated it; see the module header.

    strict=True (the cloud probe) REJECTS foreign-format saves outright --
    a save whose name/stage disagree with its dex was written by a different
    tuipet (the 2026-07-04 incident: an outdated client pushed a rebuild-era
    save with stage 'Child' and an empty name; the probe let it clobber the
    local pet).  strict=False (the local load) REPAIRS instead: the pet is
    re-derived from its dex and re-bound to its line, so a corrupted file
    becomes a playable pet rather than a silent fresh-egg wipe."""
    if not isinstance(data, dict):
        return None, ""
    data = dict(data)                            # don't mutate the caller's dict
    _migrate_v401_save(data)                     # egg-bank reorder + ver6 cut
    # egg_type must be an INT: the 2026-07-18 'guide' incident wrote the
    # carousel's sentinel string into a save (the crash handler then saved
    # the poisoned pet, and every launch died in the egg renderer).  A
    # non-int heals to egg 0 -- a classic Botamon egg beats a dead app.
    if not isinstance(data.get("egg_type"), int):
        try:
            data["egg_type"] = int(data.get("egg_type"))
        except (TypeError, ValueError):
            data["egg_type"] = 0
    # still POPPED (it is not a Pet field), but no longer READ: the elapsed
    # time it stamped drove the offline catch-up, removed 2026-07-22.  The
    # stamp itself stays on disk -- cloudsync's local_saved_at() reads it to
    # decide which SAVE is newer, which is a sync question, not a sim one.
    data.pop("_saved_at", None)
    # JSON stringifies int dict keys: trophies_won comes back str-keyed,
    # silently breaking cup prelim chains (audit 2026-07; habitat_record
    # left with the habitat system).  Coerce them back on every load.
    for k in ("trophies_won",):
        v = data.get(k)
        if isinstance(v, dict):
            data[k] = {int(kk) if str(kk).lstrip("-").isdigit() else kk: vv
                       for kk, vv in v.items()}
    # _lights_t serializes float("-inf") as Infinity -- json emits it fine, but
    # guard against a stringified copy from older tooling
    if isinstance(data.get("_lights_t"), str):
        data["_lights_t"] = float("-inf")
    # the bag heal: dead staple props shed + retired catalog keys mapped to
    # their TUIPET heirs (catalog turnover 2026-07-18)
    if isinstance(data.get("inventory"), dict):
        _heal_bag(data["inventory"])
    # THE TYPE GATE, whole-roster edition (live-play audit 2026-07-25): the
    # 13-field wrong-type list missed ~20 fields that crashed tick() or the
    # first render, and two pre-construction migrations (the manners heal's
    # float(), the wager settle's compare) raised on strings BEFORE any
    # check ran -- so load()'s promised .bak/quarantine fallback never got
    # the chance.  Every save value must match its dataclass default's
    # shape (numbers for numbers, dict for dict, ...); one generic sweep
    # over fields(Pet), no list to forget -- a defense is only as good as
    # its worst consumer (visual audit 2026-07-25).  Values a heal above
    # already coerced (egg_type, _lights_t, trophies_won keys) arrive here
    # healed; anything else malformed rejects into the fallback chain.
    for f in fields(Pet):
        if f.name not in data or data[f.name] is None:
            # None is TOLERATED, not rejected: the foreign-save repair
            # contract (the 2026-07-04 'Child' incident) loads real saves
            # carrying line_id: None and heals them downstream -- the gate
            # judges wrong TYPES, absence-shaped values pass through
            continue
        proto = (f.default if f.default is not MISSING
                 else f.default_factory() if f.default_factory is not MISSING
                 else 0)                    # `num` is the one default-less field
        if isinstance(proto, bool):
            want = (bool, int)
        elif isinstance(proto, (int, float)):
            want = (int, float)  # type: ignore
        else:
            want = type(proto)  # type: ignore
        if not isinstance(data[f.name], want):
            return None, ""
    # THE MANNERS HEAL, once per save (D1/P3, 2026-07-23).  _set_obedience
    # was a NO-OP for the whole BASIC VPET era, so every pet on disk sits
    # at the dataclass default 0 -- "worst-raised pet alive" through no
    # fault of its tamer.  Seed those saves to the stage's canon starting
    # manners the first time they load under the live meter.  The marker
    # makes it ONCE: without it, a genuinely neglected pet could reset its
    # gauge by restarting.  (Same shape as the egg_order_v migration.)
    if not data.get("obed_v") and not data.get("dead"):
        seed = {"Fresh": FRESH_OBEDIENCE, "InTraining": IN_TRAINING_OBEDIENCE}
        if float(data.get("obedience") or 0) <= 0:
            data["obedience"] = seed.get(data.get("stage"), ROOKIE_OBED_DEFAULT)
        data["obed_v"] = 1
    valid = {f.name for f in fields(Pet)}
    kwargs = {k: v for k, v in data.items() if k in valid}
    # (the full_health backfill left with the classic battle -- the 0.5 HP
    # race fights from a flat 5, so trained HP has no consumer; 0.5 BATTLE
    # 2026-07-17)
    try:
        pet = Pet(**kwargs)
    except TypeError:
        return None, ""
    # (the 13-field wrong-type list that stood here was superseded by THE
    # TYPE GATE above: same rejection, every field, checked BEFORE the
    # migrations that used to crash on the poison -- live-play audit
    # 2026-07-25.  It still guards sync_down_at_startup's probe.)
    msg = ""
    if pet.num >= 0 and pet.stage != "Egg":
        import tuipet.data.loaders.data as _data
        _, by_num = _data.load_sprites()
        rec = by_num.get(pet.num)
        if rec is None:
            # a dex this build has never heard of: the cloud must not push it,
            # but a LOCAL save survives a data refresh untouched (robustness
            # contract -- test_load_unknown_num)
            if strict:
                return None, ""
        elif pet.stage != rec["stage"] or pet.name != rec["name"]:
            if strict:
                return None, ""              # foreign format: never accept from the cloud
            # local repair: identity comes from the dex; the line re-binds by name
            import tuipet.core.lines as _lines
            croot, lid = _lines.canonical_root(pet.num)
            pet._become(croot if croot is not None else pet.num)
            pet.line_id = lid
            pet.stage_seconds = 0.0
            msg = "(save repaired — the pet's records were from another version)"
        elif not getattr(pet, "line_id", ""):
            # pre-line save: a consistent pet with no line_id would ride the
            # corpus engine forever; re-anchor by membership (truly off-chart
            # forms keep '' as before)
            import tuipet.core.lines as _lines
            _lines.adopt_line(pet)
    if getattr(pet, "dna_wager_pending", 0) > 0 and not pet.dead:
        # a paid mash was in flight at quit/crash: SETTLE it as the spoiled
        # mash it was (rate 0 -- the stabilizer band still honors a >=500
        # stake).  The stake stays spent, like the tournament's documented
        # forfeit; the charge now always buys its outcome
        # (SUSPECT S2 ruling 2026-07-20)
        amt = int(pet.dna_wager_pending)
        field = pet.dna_minigame_award(amt, 0)
        note = (f"(the interrupted DNA wager settled: {amt} on a spoiled mash"
                + (f" → {field} banked" if field != "None" else "") + ")")
        msg = (msg + "  " + note).strip()
    return pet, msg

