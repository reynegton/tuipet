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

from .progress_io import album_add
from .serializer import to_save_dict, pet_from_save

def save(pet: Any, path: Optional[Any]=None) -> None:
    # the .bak generation matters: a corrupt main save used to mean a silent
    # new egg -- and the next autosave then DESTROYED the old pet
    _atomic_write_json(path or SAVE_PATH, to_save_dict(pet), keep_bak=True)
    if getattr(pet, "num", -1) >= 0 and pet.stage != "Egg":
        album_add(pet.num)            # grow the cross-pet album (gates egg unlocks)

def write_save_dict(data: Any, path: Optional[Any]=None) -> None:
    """Atomically write a raw save dict (e.g. one pulled from the cloud) to disk.
    keep_bak: a cloud pull is the ONE writer that replaces the save with bytes
    this device never played -- it must not also burn the local backup."""
    _atomic_write_json(path or SAVE_PATH, data, keep_bak=True)

def local_saved_at(path: Optional[Any]=None) -> Any:
    """The _saved_at of the on-disk save, or 0.0 if there's no readable save."""
    path = path or SAVE_PATH
    try:
        return float(json.load(open(path)).get("_saved_at") or 0.0)
    except (ValueError, OSError, TypeError):
        return 0.0

def quarantine_save(path: str) -> Any:
    """Copy an unreadable save aside (save.corrupt.<ts>.json) before a new game
    rotates over it, so the pet stays recoverable by hand.  Returns the
    quarantine path, or None when the disk refused."""
    import shutil
    try:
        dst = os.path.join(os.path.dirname(path) or ".",
                           "save.corrupt.%s.json" % time.strftime("%Y%m%d-%H%M%S"))
        shutil.copyfile(path, dst)
        return dst
    except OSError:
        return None

def load(path: Optional[Any]=None) -> Any:
    """Return (pet, message); pet is None if no valid save exists.  A corrupt
    main save falls back to the .bak rotated by save() -- at most one autosave
    (~10s) behind, instead of a silent new egg.  When BOTH generations are
    unreadable, the damaged file is quarantined and the message SAYS SO -- a
    corrupt save must never be indistinguishable from a first launch
    (professionalism sweep 2026-07-14)."""
    path = path or SAVE_PATH
    broken = None                    # first candidate that existed but wouldn't load
    for candidate in (path, path + ".bak"):
        if not os.path.exists(candidate):
            continue
        try:
            data = json.load(open(candidate))
        except (ValueError, OSError):
            broken = broken or candidate
            continue
        try:
            pet, msg = pet_from_save(data)
        except Exception:
            # the BELT under the type gate (live-play audit 2026-07-25): this
            # function's contract is fallback/quarantine, NEVER a raise -- a
            # poisoned save that slips any future gate must land in the same
            # .bak -> quarantine chain, not crash the boot in app.py
            pet, msg = None, ""
        if pet is None:
            broken = broken or candidate
            continue
        if candidate != path:
            msg = (msg + "  " if msg else "") + "(recovered from the backup save)"
        return pet, msg
    if broken is None:
        return None, ""              # a true first launch: nothing on disk
    kept = quarantine_save(broken)
    if kept:
        return None, ("Your old save couldn't be read — the damaged file was kept as "
                      f"{os.path.basename(kept)}. Starting fresh.")
    return None, "Your old save couldn't be read. Starting fresh."

def delete(path: Optional[Any]=None) -> None:
    """Remove the save AND its .bak -- a deliberate delete must not come back
    from the backup on the next launch."""
    path = path or SAVE_PATH
    for candidate in (path, path + ".bak"):
        try:
            os.remove(candidate)
        except OSError:
            pass

def exists(path: Optional[Any]=None) -> Any:
    return os.path.exists(path or SAVE_PATH)

