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
_ALBUM_SEEN: set[int] = set()

def get_album() -> Any:
    """Set of distinct Monster species ever raised, NAME-CANONICAL (the
    DM20-style zukan).  DVPet's dex sync is by name (checkNaturalUnlocked):
    the 1410+ egg-hatch duplicate rows and their chart twins reveal together
    -- old saves may hold either num, so entries canonicalize on read
    (album/dex audit 2026-07-06)."""
    import tuipet.data.loaders.data as data
    return {data.canonical_num(n)
            for n in _prog().get("album", [])}

def get_wins() -> Any:
    """Lifetime battle wins across all pets/generations."""
    return int(_prog().get("wins", 0))

def album_seen(num: int) -> Any:
    """Has ANY generation been this form -- under EITHER of its name-twin nums?
    (canon Evolution.setUnlocked + checkNaturalUnlocked: the dex reveal state
    the hidden-evolution mask keys on, synced across same-name rows)."""
    import tuipet.data.loaders.data as data
    num = data.canonical_num(num)
    if num in _ALBUM_SEEN:
        return True
    return num in get_album()

def album_add(num: int) -> None:
    if num is None or num < 0:
        return
    import tuipet.data.loaders.data as data
    num = data.canonical_num(num)    # store the name-canonical identity
    if num in _ALBUM_SEEN:
        return
    _ALBUM_SEEN.add(num)
    from .settings_io import load_settings, save_settings
    d = load_settings()
    prog = d.setdefault("progress", {})
    album = set(prog.get("album", []))
    if num in album:
        return                       # already registered -> no write
    album.add(num)
    prog["album"] = sorted(album)
    save_settings(d)

def ladder_award_claimed(season: Any) -> Any:
    """Has this device already granted the season's ladder award?  The server
    keeps its own claim ledger; this local one stops a double-grant when the
    claim message races a re-query (monthly ladder, 2026-07-14)."""
    return season in _prog().get("ladder_claimed", [])

def note_ladder_award(season: Any) -> None:
    from .settings_io import load_settings, save_settings
    d = load_settings()
    lst = d.setdefault("progress", {}).setdefault("ladder_claimed", [])
    if season not in lst:
        lst.append(season)
        save_settings(d)

def album_has(num: int) -> Any:
    """Is this species (name-canonical) already in the cross-pet album?  Lets
    the evolve/hatch moment announce a genuine FIRST -- album_add() itself is
    buried in save() and records silently (sweep 2026-07-14)."""
    if num is None or num < 0:
        return True                  # sentinels are never announceable firsts
    import tuipet.data.loaders.data as data
    num = data.canonical_num(num)
    if num in _ALBUM_SEEN:
        return True
    return num in set(_prog().get("album", []))

def _note_add(key: str, n: Any) -> Any:
    """Bump a lifetime progress counter (the generic behind wins/mega_kills --
    the load-modify-save dance was copied per counter; refactor 2026-07-05)."""
    from .settings_io import load_settings, save_settings
    d = load_settings()
    prog = d.setdefault("progress", {})
    prog[key] = int(prog.get(key, 0)) + int(n)
    save_settings(d)
    return prog[key]

def wins_add(n: int=1) -> Any:
    return _note_add("wins", n)

def record_connection(peer_name: Any) -> None:
    """A completed online link (versus bout or jogress) with another tamer --
    the DM20 connection-battle signal behind the Corona/Luna/Meicoo/DORU
    eggs.  Distinct tamers count once, like the device's friend list."""
    if peer_name:
        _note_set("connections", str(peer_name)[:24])

def mega_kills_add(n: int=1) -> Any:
    """Lifetime Mega/Ultimate-class foes felled (gates the X egg; LINES_SPEC §7)."""
    return _note_add("mega_kills", n)

def armor_add(n: int=1) -> Any:
    """Lifetime armor (Relic) evolutions performed -- the crest-wave
    Relic shop gate (2026-07-17)."""
    return _note_add("armor_evos", n)

def _prog() -> Any:
    from .settings_io import load_settings
    return load_settings().get("progress", {})

def get_eggs_owned() -> Any:
    """Egg indices permanently earned (a met can_perm unlock, stuck forever)."""
    return set(_prog().get("eggs_owned", []))

def egg_own(idx: int) -> None:
    if idx is not None:
        _note_set("eggs_owned", idx)

def get_titles_owned() -> Any:
    """Honor titles bought (profile-level, survives generations)."""
    return set(_prog().get("titles_owned", []))

def title_own(tid: Any) -> None:
    _note_set("titles_owned", int(tid))

def get_title_worn() -> Any:
    """The WORN honor title id (-1 = none)."""
    try:
        return int(_prog().get("title_worn", -1))
    except (TypeError, ValueError):
        return -1

def set_title_worn(tid: Any) -> None:
    from .settings_io import load_settings, save_settings
    d = load_settings()
    d.setdefault("progress", {})["title_worn"] = int(tid)
    save_settings(d)

def _note_max(key: str, value: Any) -> None:
    from .settings_io import load_settings, save_settings
    d = load_settings()
    prog = d.setdefault("progress", {})
    if int(value) > int(prog.get(key, 0)):
        prog[key] = int(value)
        save_settings(d)

def note_generation(g: Any) -> None:
    _note_max("max_gen", g)

def note_stage_index(i: Any) -> None:
    _note_max("max_stage", i)

def note_xanti() -> None:
    from .settings_io import load_settings, save_settings
    d = load_settings()
    prog = d.setdefault("progress", {})
    if not prog.get("xanti_ever"):
        prog["xanti_ever"] = True
        save_settings(d)

def _note_set(key: str, value: Any) -> None:
    from .settings_io import load_settings, save_settings
    d = load_settings()
    prog = d.setdefault("progress", {})
    cur = set(prog.get(key, []))
    if value in cur:
        return
    cur.add(value)
    prog[key] = sorted(cur)
    save_settings(d)

def map_complete_add(map_index: Any) -> None:
    _note_set("maps", int(map_index))

def zone_best_set(zone_index: Any, score: Any) -> Any:
    """Record an adventure run's SCORE against the zone's standing best
    (arcade arc, 2026-07-21).  Returns True when it's a NEW best -- the
    summary card's brag."""
    from .settings_io import load_settings, save_settings
    d = load_settings()
    prog = d.setdefault("progress", {})
    bests = prog.setdefault("zone_bests", {})
    k = str(int(zone_index))
    if int(score) > int(bests.get(k, 0)):
        bests[k] = int(score)
        save_settings(d)
        return True
    return False

def zone_bests() -> Any:
    """zone_index -> best run score (str-keyed in storage, int-keyed here)."""
    return {int(k): int(v)
            for k, v in (_prog().get("zone_bests", {}) or {}).items()}

def raid_add() -> None:
    """One community raid boss this save contributed to FELL (counted at the
    claim, when the relay confirms defeated=True).  The count re-gates the
    old MapComplete egg rows (BASIC VPET 2026-07-16)."""
    from .settings_io import load_settings, save_settings
    d = load_settings()
    prog = d.setdefault("progress", {})
    prog["raids"] = int(prog.get("raids", 0)) + 1
    save_settings(d)

def tourney_add(trophy_id: Any) -> None:
    _note_set("tourneys", int(trophy_id))

def festival_add(name: str) -> None:
    """Celebrated a festival -- conquered an adventure zone on a holiday day.
    A set of the festival NAMES seen (distinct festivals only, so same-day
    conquers count once); gates the seasonal egg (Draco/Examon, the grand
    festival prize -- festivals were reward-hollow before, 2026-07-20)."""
    _note_set("festivals", str(name))

def _note_put(key: str, value: Any) -> None:
    """Park a one-slot value in the generational progress channel."""
    from .settings_io import load_settings, save_settings
    d = load_settings()
    d.setdefault("progress", {})[key] = value
    save_settings(d)

def _note_take(key: str) -> Any:
    """Pop a one-slot progress value (None when the slot is empty)."""
    from .settings_io import load_settings, save_settings
    d = load_settings()
    v = (d.get("progress") or {}).pop(key, None)
    if v is not None:
        save_settings(d)
    return v

def shop_unlock_add(key: str) -> None:
    """Canon unlockItem/unlockFood (shop/economy audit 2026-07-06): finding a
    consumable in the wild UNLOCKS its home-shop listing for good -- device-
    lifetime in canon (the bag survives resetToEgg), so the per-save progress
    channel here.  The nine Relics are the payload: found once, buyable
    (4000b) forever after."""
    from .settings_io import load_settings, save_settings
    d = load_settings()
    got = d.setdefault("progress", {}).setdefault("shop_unlocks", [])
    if key not in got:
        got.append(key)
        save_settings(d)

def shop_unlocks() -> Any:
    from .settings_io import load_settings, save_settings
    d = load_settings()
    return set((d.get("progress") or {}).get("shop_unlocks") or [])

def bank_memory(mem: Any) -> None:
    """Park the departed's inheritance data in the generational channel (DVPet
    keeps items across resetToEgg; tuipet's per-save channel is progress, the
    same place the last_gen egg gates live).  One slot, like the device."""
    _note_put("memory", dict(mem))

def bank_bonus_seed(n: Any) -> None:
    """Park the departed's care grade (careBonusOnReset) for the next egg."""
    _note_put("bonus_seed", int(n))

def take_bonus_seed() -> Any:
    return int(_note_take("bonus_seed") or 0)

def peek_memory() -> Any:
    return _prog().get("memory") or None

def take_memory() -> Any:
    """Pop the banked memory (the heir now carries it on its own save)."""
    return _note_take("memory") or None

def get_progress() -> Any:
    """Assemble the full progress view egg.evaluate() consumes."""
    prog = _prog()
    last = prog.get("last_gen", {}) or {}
    return {
        "album": get_album(),        # name-canonical (the egg gates match on it)
        "wins": int(prog.get("wins", 0)),
        "mega_kills": int(prog.get("mega_kills", 0)),
        "max_gen": int(prog.get("max_gen", 1)),
        "max_stage": int(prog.get("max_stage", 0)),
        "xanti_ever": bool(prog.get("xanti_ever", False)),
        "maps": set(prog.get("maps", [])),
        "raids": int(prog.get("raids", 0)),
        "tourneys": set(prog.get("tourneys", [])),
        "last_field": last.get("field", "None"),
        "last_attr": last.get("attribute", "None"),
        "last_obed": int(last.get("obedience", 0)),
        "last_xanti": bool(last.get("xanti", False)),
        "connections": len(prog.get("connections", [])),
        "festivals": set(prog.get("festivals", [])),
        "armor_evos": int(prog.get("armor_evos", 0)),
    }

def add_pending_bug(rec: Any) -> Any:
    """Stash a bug that could not be sent (offline) to retry next launch.
    True when it is safely on disk -- the caller PROMISES the player it will
    send later, so a failed stash must not be reported as a save (swallowed-
    failure sweep 2026-07-13)."""
    import os as _os
    import json as _json
    try:
        _os.makedirs(SAVE_DIR, exist_ok=True)
        with open(_os.path.join(SAVE_DIR, "pending_bugs.jsonl"), "a", encoding="utf-8") as f:
            f.write(_json.dumps(rec) + "\n")
        return True
    except OSError:
        return False

def peek_pending_bugs() -> Any:
    """Read the stashed bugs WITHOUT deleting them (bug audit 2026-07-19:
    the old take-then-send cleared the stash up front, so quitting mid-
    flush lost every unsent report -- the round-5 PM-flush lesson).  The
    flush rewrites the survivors when it is done."""
    import os as _os
    import json as _json
    p = _os.path.join(SAVE_DIR, "pending_bugs.jsonl")
    try:
        return [_json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    except (OSError, ValueError):
        return []

def write_pending_bugs(recs: Any) -> Any:
    """Atomically rewrite the stash to exactly `recs` ([] removes the file).
    True when it landed on disk."""
    import os as _os
    import json as _json
    p = _os.path.join(SAVE_DIR, "pending_bugs.jsonl")
    try:
        if not recs:
            if _os.path.exists(p):
                _os.remove(p)
            return True
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            for r in recs:
                f.write(_json.dumps(r) + "\n")
        _os.replace(tmp, p)
        return True
    except OSError:
        return False

