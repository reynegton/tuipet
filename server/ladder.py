import json
import logging
import os
import time
import state

LOG = logging.getLogger("tuipet.lobby")

_ladder_pending = {}
_ladder_confirm = {}
_ladder_pair_hour = {}

def _load_ladder():
    try:
        d = json.load(open(state.LADDER_PATH))
        return {"seasons": dict(d.get("seasons", {})),
                "claimed": dict(d.get("claimed", {}))}
    except (OSError, ValueError):
        return {"seasons": {}, "claimed": {}}

def _save_ladder():
    try:
        tmp = state.LADDER_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state.LADDER, f)
        os.replace(tmp, state.LADDER_PATH)
    except OSError:
        LOG.warning("ladder: disk refused %s", state.LADDER_PATH)

def _season_key(now=None):
    return time.strftime("%Y-%m", time.gmtime(now))

def _season_days_left(now=None):
    import calendar
    tm = time.gmtime(now)
    return calendar.monthrange(tm.tm_year, tm.tm_mon)[1] - tm.tm_mday

def _ladder_credit(winner, loser, now=None):
    now = time.time() if now is None else now
    pair = tuple(sorted((winner, loser))) + (time.strftime("%Y-%m-%dT%H", time.gmtime(now)),)
    if _ladder_pair_hour.get(pair, 0) >= state.LADDER_PAIR_CAP:
        return False
    _ladder_pair_hour[pair] = _ladder_pair_hour.get(pair, 0) + 1
    if len(_ladder_pair_hour) > 2048:
        hour = time.strftime("%Y-%m-%dT%H", time.gmtime(now))
        for k in [k for k in _ladder_pair_hour if k[2] != hour]:
            del _ladder_pair_hour[k]
    season = state.LADDER["seasons"].setdefault(_season_key(now), {})
    season[winner] = season.get(winner, 0) + 1
    _save_ladder()
    return True

def _ladder_report(name, won, opp, now=None):
    now = time.time() if now is None else now
    if not opp or opp == name:
        return
    if (name.lower().startswith(state.SMOKE_PREFIX)
            or opp.lower().startswith(state.SMOKE_PREFIX)):
        return
    key = (name, opp) if won else (opp, name)
    mine = _ladder_pending if won else _ladder_confirm
    theirs = _ladder_confirm if won else _ladder_pending
    ts = theirs.get(key)
    if ts is not None and now - ts <= state.LADDER_CONFIRM_S:
        theirs.pop(key, None)
        _ladder_credit(key[0], key[1], now)
        return
    mine[key] = now
    if len(mine) > 512:
        for k in sorted(mine, key=mine.get)[:256]:
            mine.pop(k, None)

def _ladder_award(name, now=None):
    now = time.time() if now is None else now
    cur = _season_key(now)
    for season in sorted(state.LADDER["seasons"], reverse=True):
        if season >= cur or name in state.LADDER["claimed"].get(season, []):
            continue
        top = sorted(state.LADDER["seasons"][season].items(), key=lambda kv: (-kv[1], kv[0]))
        for rank, (who, wins) in enumerate(top[:3], start=1):
            if who == name:
                return {"season": season, "rank": rank, "wins": wins,
                        "bits": state.LADDER_PAYOUT[rank]}
    return None

def _ladder_view(name, now=None):
    now = time.time() if now is None else now
    season = _season_key(now)
    table = state.LADDER["seasons"].get(season, {})
    top = sorted(table.items(), key=lambda kv: (-kv[1], kv[0]))
    you = next((i + 1 for i, (who, _w) in enumerate(top) if who == name), 0)
    return {"t": "ladder", "season": season, "days_left": _season_days_left(now),
            "top": top[:10], "you": [you, table.get(name, 0)],
            "award": _ladder_award(name, now)}

def _ladder_claim(name, season):
    a = _ladder_award(name)
    if not a or a["season"] != season:
        return {"t": "ladder_reward", "ok": False}
    state.LADDER["claimed"].setdefault(season, []).append(name)
    _save_ladder()
    return {"t": "ladder_reward", "ok": True, "season": a["season"],
            "rank": a["rank"], "wins": a["wins"], "bits": a["bits"]}
