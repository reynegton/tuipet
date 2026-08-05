import asyncio
import json
import logging
import os
import time
import state
from typing import Any, Dict

LOG = logging.getLogger("tuipet.lobby")

def _load_pending() -> Dict[str, Any]:
    try:
        return json.load(open(state.PENDING_PATH))
    except (OSError, ValueError):
        return {}

async def _save_pending() -> None:
    async with state._pending_lock:
        tmp = state.PENDING_PATH + ".tmp"
        with open(tmp, "w") as f:
            json.dump(state.PENDING, f)
        os.replace(tmp, state.PENDING_PATH)

async def _queue_pm(key: str, from_name: str, text: str) -> None:
    q = state.PENDING.setdefault(key, [])
    q.append({"from_name": from_name, "text": text,
              "ts": time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())})
    del q[:-state.MAX_PENDING_PER_ACCT]
    await _save_pending()

async def _flush_pending(client: Any, key: str) -> None:
    q = state.PENDING.get(key)
    if not q:
        return
    sent = 0
    for rec in list(q):
        try:
            await client.ws.send(json.dumps(
                {"t": "pm", "from_id": 0,
                 "from_name": rec.get("from_name", "?"),
                 "text": rec.get("text", "")}))
        except Exception:
            break
        sent += 1
    if not sent:
        return
    del q[:sent]
    if not q:
        state.PENDING.pop(key, None)
    await _save_pending()
    LOG.info("flushed %d queued pm(s) to %s", sent, client.name)
