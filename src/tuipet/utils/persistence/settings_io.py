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

DM_KEEP = 50
from . import progress_io


def __getattr__(name: str) -> Any:
    """`save_failed` is MUTABLE state owned by persistio's writer -- a
    static re-export would freeze it at import; delegate reads instead."""
    if name == "save_failed":
        return _persistio.save_failed
    raise AttributeError(name)

def load_settings(path: Optional[Any]=None) -> Any:
    """App-level prefs that outlive any single pet (e.g. the lobby account).
    Falls back to the .bak rotated by save_settings -- settings hold the album,
    lifetime wins, owned eggs and the banked Memory; one corrupt write must
    not erase a save file's whole history (audit 2026-07)."""
    path = path or SETTINGS_PATH
    for candidate in (path, path + ".bak"):
        try:
            d = json.load(open(candidate))
        except (OSError, ValueError):
            continue
        if _migrate_v401_settings(d):        # .400/.401 egg indices -> .402 bank
            save_settings(d, path)
        return d
    return {}

def get_auto_update() -> Any:
    """Should the game install a newer release for itself at launch?  On by
    default (Joel 2026-07-14) -- a player can turn it off in g options."""
    return bool(load_settings().get("auto_update", True))

def get_cloud_sync() -> Any:
    """The player-facing cloud-save switch (settings only; see sync_enabled)."""
    return bool(load_settings().get("cloud_sync", True))

def set_cloud_sync(on: Any) -> Any:
    d = load_settings()
    d["cloud_sync"] = bool(on)
    save_settings(d)
    return bool(on)

def sync_enabled() -> Any:
    """Cloud sync is completely disabled for this hard fork."""
    # TODO: Estudar a comunicação de rede do servidor gringo original e manter a compatibilidade
    # dos envios/recebimentos para reativar o cloud sync futuramente.
    return False

def set_auto_update(on: Any) -> Any:
    d = load_settings()
    d["auto_update"] = bool(on)
    save_settings(d)
    return bool(on)

def save_settings(d: Any, path: Optional[Any]=None) -> None:
    # every write stamps the CURRENT egg-bank version -- without it, a
    # settings file created THIS session would look like a pre-migration
    # (.400/.401) file on the next load and get wrongly re-translated
    d["egg_order_v"] = EGG_ORDER_V
    _atomic_write_json(path or SETTINGS_PATH, d, keep_bak=True)

def get_blocked() -> Any:
    """Muted lobby peers (names)."""
    return set(load_settings().get("blocked", []))

def set_blocked(names: Any) -> None:
    d = load_settings()
    d["blocked"] = sorted(names)
    save_settings(d)

def get_dms() -> Any:
    """Persisted lobby DM threads -> ({peer: [(from, text), ...]}, unread set).
    Conversations survive leaving the thread/lobby (Joel 2026-07-10)."""
    d = load_settings()
    dms = {p: [tuple(m[:2]) for m in v if isinstance(m, (list, tuple)) and len(m) >= 2]
           for p, v in (d.get("dms") or {}).items()}
    return dms, set(d.get("dm_unread") or [])

def save_dms(dms: Any, unread: Any) -> None:
    d = load_settings()
    d["dms"] = {p: [list(m) for m in v[-DM_KEEP:]] for p, v in dms.items() if v}
    d["dm_unread"] = sorted(n for n in unread if n in d["dms"])
    save_settings(d)

def get_account() -> Any:
    """The cached lobby account: (name, password). (None, "") if unset."""
    a = load_settings().get("account") or {}
    name = (a.get("name") or "").strip()
    return (name or None, a.get("pw") or "")

def set_account(name: str, pw: Any) -> None:
    d = load_settings()
    name = (name or "").strip()[:24]
    d["account"] = {"name": name, "pw": pw or ""}
    save_settings(d)

def erase_all() -> Any:
    """Erase the WHOLE local state: pet save (+bak), settings (progress,
    account, memory, +bak), sound + theme prefs -- and every other file
    carrying the erased pet's data: quarantined save.corrupt.* copies, the
    crash log and the stashed bug reports (persistence audit 2026-07-18:
    'for keeps' left the old pet recoverable on disk).  The cloud copy stays
    with the account server-side; with the login gone, nothing pulls it.
    Options-menu 'Erase all data' (Joel 2026-07-04)."""
    import glob as _glob
    removed = []
    names = ["save.json", "save.json.bak", "settings.json", "settings.json.bak",
             "sound.txt", "theme.txt", "crash.log", "pending_bugs.jsonl",
             "volume.txt"]   # never in this list before the 2026-07-19 shape sweep
    names += [os.path.basename(p) for p in
              _glob.glob(os.path.join(SAVE_DIR, "save.corrupt.*.json"))]
    for fn in names:
        p = os.path.join(SAVE_DIR, fn)
        try:
            os.remove(p)
            removed.append(fn)
        except OSError:
            pass
    progress_io._ALBUM_SEEN.clear()
    import shutil as _sh
    try:
        _sh.rmtree(os.path.join(SAVE_DIR, "sndcache"))   # the scaled-wav cache:
        removed.append("sndcache/")                      # rebuildable, but "for
    except OSError:                                      # keeps" is for keeps
        pass
    # the album's in-process mirror must die with the files, or every species
    # raised BEFORE the erase silently never re-records in the fresh album
    # (album_add early-returns on the cached num; audit 2026-07-13)
    progress_io._ALBUM_SEEN.clear()
    return removed


def get_saved_language() -> str:
    """Gets the persisted user language preference."""
    return load_settings().get("language") or ""

def set_saved_language(lang: str) -> None:
    """Sets and persists the user language preference."""
    d = load_settings()
    d["language"] = lang
    save_settings(d)
