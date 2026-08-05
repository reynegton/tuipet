import json
import logging
import os
import time
import state
from typing import Any, Dict, List, Optional

LOG = logging.getLogger("tuipet.lobby")

try:
    with open(state.RAID_MULT_BY_NUM_PATH) as _f:
        _RAID_MULT_BY_NUM = {int(k): int(v) for k, v in json.load(_f).items()}
except (OSError, ValueError):
    _RAID_MULT_BY_NUM = {}

def _load_raid() -> Dict[str, Any]:
    try:
        with open(state.RAID_PATH) as f:
            d = json.load(f)
        d.setdefault("boss", None)
        d.setdefault("board", {})
        d.setdefault("history", [])
        d.setdefault("claimed", {})
        d.setdefault("attempts", {})
        return d
    except Exception:
        return {"boss": None, "board": {}, "history": [], "claimed": {},
                "attempts": {}}

def _save_raid() -> None:
    try:
        tmp = state.RAID_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state.RAID, f)
        os.replace(tmp, state.RAID_PATH)
    except OSError:
        LOG.warning("raid: disk refused %s", state.RAID_PATH)

def _raid_pool() -> List[Dict[str, Any]]:
    try:
        with open(state.RAID_POOL_PATH) as f:
            return json.load(f)
    except Exception:
        return [{"num": 0, "name": "Unknown Boss", "energy_max": 65}]

def _raid_mult_for_num(num: Any) -> int:
    try:
        return _RAID_MULT_BY_NUM.get(int(num), 1)
    except (TypeError, ValueError):
        return 1

def _adaptive_hp() -> int:
    if not state.RAID["history"]:
        return state.RAID_HP_FLOOR
    last = state.RAID["history"][-1]
    dealt = sum(int(e.get("damage", 0)) for e in (last.get("board") or {}).values())
    if last.get("defeated"):
        base = int(last.get("max_hp") or dealt or state.RAID_HP_FLOOR) * state.RAID_GROW
    else:
        base = dealt * state.RAID_FIT
    return int(max(state.RAID_HP_FLOOR, min(state.RAID_HP_CAP, base)))

def _raid_stage_next(now: float) -> Dict[str, Any]:
    import random as _r
    pick = _r.choice(_raid_pool())
    hp = _adaptive_hp()
    start = now + state.RAID_COOLDOWN_S
    if state.RAID["boss"] is None and not state.RAID["history"]:
        start = now
    return {"num": int(pick["num"]), "name": str(pick["name"]),
            "hp": hp, "max_hp": hp,
            "start": start, "end": start + state.RAID_WINDOW_S}

def _raid_rotate(now: Optional[float] = None) -> None:
    now = time.time() if now is None else now
    b = state.RAID["boss"]
    if b is not None and b["hp"] > 0 and now <= b["end"]:
        return
    if b is not None:
        state.RAID["history"].append({
            "id": str(int(b["end"])), "boss_name": b["name"], "num": b["num"],
            "defeated": b["hp"] <= 0, "ended": now,
            "max_hp": b.get("max_hp", 0),
            "board": dict(state.RAID["board"]),
        })
        state.RAID["history"] = state.RAID["history"][-state.RAID_HISTORY_KEEP:]
        state.RAID["board"] = {}
    state.RAID["boss"] = _raid_stage_next(now)
    _save_raid()

def _raid_attempts(name: str, now: Optional[float] = None) -> Dict[str, Any]:
    now = time.time() if now is None else now
    day = time.strftime("%Y-%m-%d", time.gmtime(now))
    rec = state.RAID["attempts"].get(name)
    if not rec or rec.get("date") != day:
        rec = {"date": day, "left": state.RAID_ATTEMPTS_PER_DAY}
        state.RAID["attempts"][name] = rec
        if len(state.RAID["attempts"]) > 4096:
            state.RAID["attempts"] = {n: r for n, r in state.RAID["attempts"].items()
                                      if r.get("date") == day}
    return rec

def _raid_rank(board: Dict[str, Any], name: str) -> int:
    top = sorted(board.items(), key=lambda kv: (-kv[1]["damage"],
                                                kv[1].get("ts", 0)))
    return next((i + 1 for i, (who, _v) in enumerate(top) if who == name), 0)

def _raid_award(name: str) -> Optional[Dict[str, Any]]:
    for rec in sorted(state.RAID["history"], key=lambda r: r["id"], reverse=True):
        if name in state.RAID["claimed"].get(rec["id"], []):
            continue
        if name not in rec["board"]:
            continue
        rank = _raid_rank(rec["board"], name)
        if rec["defeated"]:
            bits = state.RAID_RANK_BITS.get(rank, state.RAID_PART_BITS)
            items = state.RAID_RANK_ITEMS.get(rank, state.RAID_PART_ITEMS)
        else:
            pool = int(rec.get("max_hp") or 0)
            mine = int((rec["board"].get(name) or {}).get("damage", 0))
            share = (mine / pool) if pool > 0 else 0.0
            bits = max(state.RAID_CONSOLATION,
                       min(state.RAID_RANK_BITS[3], int(state.RAID_RANK_BITS[3] * share * 5)))
            items = 0
        return {"id": rec["id"], "rank": rank, "defeated": rec["defeated"],
                "boss": rec["boss_name"], "bits": bits, "items": items}
    return None

def _raid_view(name: str, now: Optional[float] = None) -> Dict[str, Any]:
    now = time.time() if now is None else now
    _raid_rotate(now)
    b = state.RAID["boss"]
    top = sorted(state.RAID["board"].items(),
                 key=lambda kv: (-kv[1]["damage"], kv[1].get("ts", 0)))
    you = next(((i + 1, v["damage"]) for i, (who, v) in enumerate(top)
                if who == name), (0, 0))
    return {"t": "raid",
            "boss": dict(b),
            "now": now,
            "top": [(who, v["damage"]) for who, v in top[:10]],
            "you": list(you),
            "attempts": _raid_attempts(name, now)["left"],
            "award": _raid_award(name)}

def _raid_hit(name: str, raw: Any, num: Any, now: Optional[float] = None) -> Dict[str, Any]:
    now = time.time() if now is None else now
    _raid_rotate(now)
    b = state.RAID["boss"]
    if b["start"] > now or b["hp"] <= 0:
        return {"t": "raid_hit", "ok": False, "code": "err_raid_not_standing", "why": "The boss is not standing."}
    rec = _raid_attempts(name, now)
    if rec["left"] <= 0:
        return {"t": "raid_hit", "ok": False, "code": "err_raid_no_attempts", "why": "No attempts left today."}
    rec["left"] -= 1
    try:
        raw = int(raw or 0)
    except (TypeError, ValueError):
        raw = 0
    raw = max(0, min(raw, state.RAID_MAX_RAW))
    dealt = raw * state.RAID_DMG_MULT * _raid_mult_for_num(num)
    b["hp"] = max(0, b["hp"] - dealt)
    entry = state.RAID["board"].setdefault(name, {"damage": 0, "ts": now})
    entry["damage"] += dealt
    if b["hp"] <= 0:
        _raid_rotate(now)
    _save_raid()
    return {"t": "raid_hit", "ok": True, "dealt": dealt}

def _raid_claim(name: str, raid_id: Any, now: Optional[float] = None) -> Dict[str, Any]:
    now = time.time() if now is None else now
    a = _raid_award(name)
    if not a or a["id"] != str(raid_id):
        return {"t": "raid_reward", "ok": False}
    import random as _r
    bits = a["bits"]
    wd = time.gmtime(now).tm_wday
    if wd >= 5:
        bits = int(bits * 1.5)
    items = [_r.choice(state.RAID_ITEM_POOL) for _ in range(a["items"])]
    state.RAID["claimed"].setdefault(a["id"], []).append(name)
    if len(state.RAID["claimed"]) > state.RAID_HISTORY_KEEP * 4:
        keep = {r["id"] for r in state.RAID["history"]}
        state.RAID["claimed"] = {k: v for k, v in state.RAID["claimed"].items() if k in keep}
    _save_raid()
    return {"t": "raid_reward", "ok": True, "bits": bits, "items": items,
            "defeated": a["defeated"], "rank": a["rank"], "boss": a["boss"]}
