import asyncio
import hmac
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import websockets

import state
from accounts import _verify, _make_account, _save_accounts
from cloud import _take_lease, _lease_ok, _store_save
from messaging import _queue_pm, _flush_pending
from ladder import _ladder_report, _ladder_view, _ladder_claim
from raid import _raid_hit, _raid_view, _raid_claim

LOG = logging.getLogger("tuipet.lobby")

def _admin_key() -> Optional[str]:
    k = os.environ.get("TUIPET_ADMIN_KEY", "")
    if k:
        return k.strip()
    try:
        return open(state.ADMIN_KEY_PATH).read().strip()
    except OSError:
        return ""

def _clean(s: Any, limit: int) -> str:
    return str(s or "").replace("\n", " ").replace("\r", " ").strip()[:limit]

def _clamp_pet(p: Any) -> Dict[str, Any]:
    if not isinstance(p, dict):
        return {}
    out: Dict[str, Any] = {}
    for k in ("name", "stage", "attr", "title"):
        v = p.get(k)
        if isinstance(v, (str, int, float)) and not isinstance(v, bool):
            s = _clean(v, state.MAX_NAME)
            if s:
                out[k] = s
    try:
        out["num"] = max(0, min(int(p.get("num") or 0), 10 ** 6))
    except (TypeError, ValueError):
        out["num"] = 0
    return out

async def _send(client: Any, obj: Any) -> None:
    try:
        await client.ws.send(json.dumps(obj))
    except Exception:
        pass

async def _close_quiet(ws: Any) -> None:
    try:
        await ws.close()
    except Exception:
        pass

async def _broadcast(obj: Any, exclude: Optional[int] = None) -> None:
    if state.CLIENTS:
        msg = json.dumps(obj)
        await asyncio.gather(*(
            c.ws.send(msg) for c in state.CLIENTS.values() if c.id != exclude
        ), return_exceptions=True)

def _room_code(raw: Any) -> Optional[str]:
    code = " ".join(str(raw or "").split()).lower()[:state.MAX_ROOM]
    return code or None

async def _broadcast_room(room: Optional[str], obj: Any, exclude: Optional[int] = None) -> None:
    targets = [c for c in state.CLIENTS.values()
               if c.id != exclude and c.room == room]
    if targets:
        msg = json.dumps(obj)
        await asyncio.gather(*(c.ws.send(msg) for c in targets),
                             return_exceptions=True)

def _roster(room: Optional[str] = None) -> Dict[str, Any]:
    by_key: Dict[str, Any] = {}
    for c in state.CLIENTS.values():
        if not c.logged or c.room != room:
            continue
        key = c.name.lower()
        cur = by_key.get(key)
        if cur is None or (c.live and not cur.live):
            by_key[key] = c
    return {"t": "roster", "players": [
        {"id": c.id, "name": c.name, "pet": c.pet, "live": c.live}
        for c in by_key.values()]}

def _account_conns(name: str) -> List[Any]:
    key = name.lower()
    return [c for c in state.CLIENTS.values() if c.logged and c.name.lower() == key]

async def _push_roster() -> None:
    for room in {c.room for c in state.CLIENTS.values()}:
        await _broadcast_room(room, _roster(room))

async def _handle_bug(client: Any, m: Dict[str, Any]) -> None:
    client.bugs_sent += 1
    text = (str(m.get("text") or "")).strip()[:state.MAX_BUG_TEXT]
    if not text or client.bugs_sent > state.MAX_BUGS_PER_CONN:
        await _send(client, {"t": "bug_ok", "ok": False})
        return
    pet_data: Any = m.get("pet") if isinstance(m.get("pet"), dict) else {}
    pet_data = {k: (pet_data[k] if isinstance(pet_data[k], int) else str(pet_data[k])[:24])
           for k in ("num", "name", "stage", "gen") if k in pet_data}
    rec = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()),
        "from": (str(m.get("name") or "").strip() or "anon")[:state.MAX_NAME],
        "version": str(m.get("version") or "")[:24],
        "platform": str(m.get("platform") or "")[:60],
        "pet": pet_data,
        "text": text,
    }
    ok = True
    try:
        if os.path.exists(state.BUGS_PATH) and os.path.getsize(state.BUGS_PATH) > state.MAX_BUG_FILE:
            ok = False
        else:
            with open(state.BUGS_PATH, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec) + "\n")
    except OSError:
        ok = False
    LOG.info("bug from %s (%d chars) ok=%s", rec["from"], len(text), ok)
    await _send(client, {"t": "bug_ok", "ok": ok})

def _feed(kind: str, **kw: Any) -> None:
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime()), "kind": kind}
    rec.update(kw)
    try:
        if os.path.exists(state.FEED_PATH) and os.path.getsize(state.FEED_PATH) > state.MAX_FEED:
            os.replace(state.FEED_PATH, state.FEED_PATH + ".1")
        with open(state.FEED_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except OSError:
        pass

async def _handle_admin(client: Any, m: Dict[str, Any]) -> None:
    key = _admin_key()
    if not key or not hmac.compare_digest(str(m.get("key") or ""), key):
        LOG.info("admin REFUSED conn=%s cmd=%r", client.id, m.get("cmd"))
        await _send(client, {"t": "error", "code": "err_admin_nope", "msg": "Nope."})
        return
    cmd = m.get("cmd")
    if cmd == "who":
        roster = [{"name": c.name, "live": c.live,
                   "pet": (c.pet or {}).get("name", ""),
                   "stage": (c.pet or {}).get("stage", "")}
                  for c in state.CLIENTS.values() if c.logged]
        await _send(client, {"t": "admin_ok", "cmd": "who",
                             "online": len(roster), "roster": roster})
    elif cmd == "announce":
        text = _clean(m.get("text"), state.MAX_ANNOUNCE)
        if not text:
            await _send(client, {"t": "admin_ok", "cmd": "announce", "sent": 0})
            return
        out = {"t": "announce", "text": text}
        state.CHAT_BACKLOG.append(out)
        await _broadcast(out)
        _feed("announce", text=text)
        LOG.info("announce (%d chars) to %d conns", len(text), len(state.CLIENTS))
        await _send(client, {"t": "admin_ok", "cmd": "announce",
                             "sent": sum(1 for c in state.CLIENTS.values() if c.logged)})
    else:
        await _send(client, {"t": "error", "code": "err_admin_unknown", "msg": "Unknown admin cmd."})

def _consume_token(client: Any) -> bool:
    now = time.time()
    elapsed = now - client._msg_refill_t
    client._msg_tokens = min(50.0, client._msg_tokens + elapsed * 10.0)
    client._msg_refill_t = now
    if client._msg_tokens >= 1.0:
        client._msg_tokens -= 1.0
        return True
    return False

async def handler(ws: Any) -> None:
    if len(state.CLIENTS) >= state.MAX_CLIENTS:
        await ws.send(json.dumps({"t": "error", "code": "err_lobby_full", "msg": "Lobby is full."}))
        return
    client = state.Client(ws)
    state.CLIENTS[client.id] = client
    logged_in = False
    try:
        async for raw in ws:
            if len(raw) > state.MAX_MSG_BYTES:
                LOG.info("oversize frame dropped: %dB conn=%s", len(raw), client.id)
                continue
            try:
                m = json.loads(raw)
                t = m.get("t")
            except (ValueError, AttributeError):
                continue

            if not _consume_token(client):
                await _send(client, {"t": "error", "code": "err_rate_limited", "msg": "Slow down."})
                continue

            if t == "login":
                name = _clean(m.get("name"), state.MAX_NAME)
                pw = str(m.get("pw") or "")[:state.MAX_PW]
                if not name:
                    await _send(client, {"t": "login_failed", "code": "err_login_name_req", "msg": "Name required."})
                    return
                key = name.lower()
                acc = state.ACCOUNTS.get(key)
                if acc:
                    if not await asyncio.to_thread(_verify, pw, acc):
                        await asyncio.sleep(0.4)
                        await _send(client, {"t": "login_failed", "code": "err_login_wrong_pw", "msg": "Wrong password for that name."})
                        return
                    name = acc["name"]
                else:
                    if not pw:
                        await _send(client, {"t": "login_failed", "code": "err_login_pick_pw", "msg": "Pick a password to claim this name."})
                        return
                    state.ACCOUNTS[key] = await asyncio.to_thread(_make_account, name, pw)
                    _save_accounts()
                    LOG.info("registered account %s", name)
                
                sync_only = bool(m.get("sync_only"))
                try:
                    boot = float(m.get("boot") or 0)
                except (TypeError, ValueError):
                    boot = 0.0
                if not sync_only:
                    stale = [c for c in state.CLIENTS.values()
                             if c is not client and c.live and c.name.lower() == key]
                    if any(c.boot > boot for c in stale):
                        await _send(client, {"t": "login_failed",
                                             "code": "err_newer_session",
                                             "msg": "Signed in on a newer session."})
                        return
                    for c in stale:
                        state.CLIENTS.pop(c.id, None)
                        await _send(c, {"t": "error", "code": "err_newer_session", "msg": "Signed in from a newer session."})
                        asyncio.ensure_future(_close_quiet(c.ws))
                        LOG.info("evicted stale session id=%s name=%s", c.id, c.name)
                    client.boot = boot
                client.name = name
                client.pet = _clamp_pet(m.get("pet"))
                client.live = not sync_only
                if sync_only:
                    _take_lease(client, key, boot)
                logged_in = True
                client.logged = True
                await _send(client, {"t": "welcome", "id": client.id, "name": client.name,
                                     "save": state.SAVES.get(key)})
                if not sync_only:
                    for f in state.CHAT_BACKLOG:
                        await _send(client, {**f, "replay": True})
                    await _flush_pending(client, key)
                await _push_roster()
                LOG.info("login id=%s name=%s sync_only=%s (%d online)",
                         client.id, client.name, sync_only, len(state.CLIENTS))
                _feed("join", name=client.name, ghost=sync_only)

            elif t == "bug":
                await _handle_bug(client, m)

            elif t == "admin":
                await _handle_admin(client, m)

            elif not logged_in:
                await _send(client, {"t": "error", "code": "err_login_first", "msg": "Log in first."})

            elif t == "pet":
                client.pet = _clamp_pet(m.get("pet"))
                if client.live:
                    await _push_roster()

            elif t == "save":
                key = client.name.lower()
                ok, why = False, None
                if _lease_ok(client, key):
                    ok = await _store_save(key, m.get("save"))
                    if not ok:
                        why = "invalid"
                else:
                    why = "lease"
                    LOG.info("stale-lease save dropped: %s conn=%s", client.name, client.id)
                ack = {"t": "saved", "ok": ok}
                if why:
                    ack["why"] = why
                await _send(client, ack)

            elif t == "ladder_report":
                _ladder_report(client.name, bool(m.get("won")), str(m.get("opp") or "")[:24])

            elif t == "ladder_get":
                await _send(client, _ladder_view(client.name))

            elif t == "ladder_claim":
                await _send(client, _ladder_claim(client.name, str(m.get("season") or "")))
                await _send(client, _ladder_view(client.name))

            elif t == "raid_get":
                await _send(client, _raid_view(client.name))
            elif t == "raid_hit":
                r = _raid_hit(client.name, m.get("damage"),
                              (client.pet or {}).get("num"))
                await _send(client, r)
                await _send(client, _raid_view(client.name))
            elif t == "raid_claim":
                await _send(client, _raid_claim(client.name, m.get("raid")))
                await _send(client, _raid_view(client.name))

            elif t == "chat":
                text = _clean(m.get("text"), state.MAX_CHAT)
                if text and client.live:
                    out = {"t": "chat", "from_id": client.id,
                           "from_name": client.name, "text": text}
                    if client.room is None:
                        state.CHAT_BACKLOG.append(out)
                    await _broadcast_room(client.room, out)
                    _feed("chat", name=client.name, text=text, room=client.room)

            elif t == "room":
                if not client.live:
                    continue
                code = _room_code(m.get("code"))
                if code != client.room:
                    client.room = code
                    await _send(client, {"t": "room_ok", "room": code})
                    if code is None:
                        for f in state.CHAT_BACKLOG:
                            await _send(client, {**f, "replay": True})
                    await _push_roster()
                    _feed("room", name=client.name, room=code or "(main)")
                else:
                    await _send(client, {"t": "room_ok", "room": code})

            elif t == "pm":
                text = _clean(m.get("text"), state.MAX_CHAT)
                if not text:
                    continue
                target = state.CLIENTS.get(m.get("to"))
                if target is not None and target.logged:
                    name = target.name
                else:
                    name = _clean(m.get("to_name"), state.MAX_NAME)
                key = name.lower() if name else ""
                if not key or key not in state.ACCOUNTS:
                    await _send(client, {"t": "error", "code": "err_no_such_player", "msg": "No such player."})
                    continue
                out = {"t": "pm", "from_id": client.id,
                       "from_name": client.name, "text": text}
                conns = _account_conns(name)
                for c in conns:
                    await _send(c, out)
                if not any(c.live for c in conns):
                    await _queue_pm(key, client.name, text)
                await _send(client, {"t": "pm_ok",
                                     "to_name": state.ACCOUNTS[key]["name"], "text": text})

            elif t in ("invite", "invite_resp", "relay"):
                if not client.live:
                    continue
                target = state.CLIENTS.get(m.get("to"))
                if target is None or not target.live:
                    await _send(client, {"t": "error", "code": "err_player_left", "msg": "That player just left."})
                    continue
                out = {"t": t, "from_id": client.id, "from_name": client.name}
                if t == "relay":
                    out["payload"] = m.get("payload")
                else:
                    out["kind"] = m.get("kind")
                    if t == "invite_resp":
                        out["accept"] = bool(m.get("accept"))
                        if m.get("busy"):
                            out["busy"] = True
                await _send(target, out)
    except websockets.ConnectionClosed:
        pass
    finally:
        state.CLIENTS.pop(client.id, None)
        if logged_in:
            await _push_roster()
            _feed("leave", name=client.name, ghost=not client.live)
        LOG.info("gone  id=%s (%d online)", client.id, len(state.CLIENTS))

async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    LOG.info("tuipet lobby on ws://%s:%d (%d accounts)", state.HOST, state.PORT, len(state.ACCOUNTS))
    async with websockets.serve(handler, state.HOST, state.PORT, max_size=state.MAX_MSG_BYTES):
        await asyncio.Future()

def run() -> None:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
