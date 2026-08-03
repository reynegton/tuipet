import asyncio
import json
import logging
import os
import time
import state

LOG = logging.getLogger("tuipet.lobby")

_STAGES = {"Egg", "Fresh", "InTraining", "Rookie", "Champion", "Ultimate", "Mega"}

def _load_saves():
    try:
        return json.load(open(state.SAVES_PATH))
    except (OSError, ValueError):
        return {}

def _prune_saves(now=None):
    now = time.time() if now is None else now
    changed = False
    for k, sv in list(state.SAVES.items()):
        if not isinstance(sv, dict):
            del state.SAVES[k]
            changed = True
            continue
        ts = sv.get("_srv_at")
        if not ts:
            sv["_srv_at"] = now
            changed = True
            continue
        try:
            stale = now - float(ts) > state.SAVE_RETENTION_S
        except (TypeError, ValueError):
            sv["_srv_at"] = now
            changed = True
            continue
        if stale:
            del state.SAVES[k]
            changed = True
    if changed:
        try:
            tmp = state.SAVES_PATH + ".tmp"
            with open(tmp, "w") as f:
                json.dump(state.SAVES, f)
            os.replace(tmp, state.SAVES_PATH)
        except OSError:
            LOG.warning("saves prune: disk refused %s", state.SAVES_PATH)

def _valid_save(save):
    if not isinstance(save, dict):
        return False
    stage = save.get("stage")
    if stage not in _STAGES:
        return False
    if stage != "Egg" and not (save.get("name") or "").strip():
        return False
    return True

async def _store_save(key, save):
    if not _valid_save(save):
        return False
    now = time.time()
    try:
        if float(save.get("_saved_at") or 0) > now + state.SAVE_STAMP_SLACK:
            save["_saved_at"] = now
    except (TypeError, ValueError):
        save["_saved_at"] = now
    save["_srv_at"] = now
    state.SAVES[key] = save
    async with state._saves_lock:
        tmp = state.SAVES_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state.SAVES, f)
        os.replace(tmp, state.SAVES_PATH)
    return True

def _take_lease(client, key, boot):
    cur = state.LEASES.get(key)
    seen = state.BOOT_SEEN.setdefault(key, {})
    if boot and boot not in seen:
        seen[boot] = time.time()
        while len(seen) > state.MAX_SEEN_BOOTS:
            del seen[min(seen, key=seen.get)]
    if cur and boot and cur[0] and cur[0] != boot \
            and seen.get(boot, 0) < seen.get(cur[0], 0):
        client.lease = None
        return
    serial = (cur[1] if cur else 0) + 1
    state.LEASES[key] = (boot, serial)
    client.lease = serial

def _lease_ok(client, key):
    cur = state.LEASES.get(key)
    return cur is not None and cur[1] == getattr(client, "lease", None)
