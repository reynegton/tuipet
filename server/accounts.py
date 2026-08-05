import hashlib
import hmac
import json
import os
import state
from typing import Any, Dict

def _load_accounts() -> Dict[str, Any]:
    try:
        return json.load(open(state.ACCOUNTS_PATH))
    except (OSError, ValueError):
        return {}

def _save_accounts() -> None:
    tmp = state.ACCOUNTS_PATH + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state.ACCOUNTS, f)
    os.replace(tmp, state.ACCOUNTS_PATH)

def _hash(pw: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", pw.encode("utf-8"), salt, state.PBKDF2_ITERS).hex()

def _make_account(name: str, pw: str) -> Dict[str, Any]:
    salt = os.urandom(16)
    return {"name": name, "salt": salt.hex(), "hash": _hash(pw, salt)}

def _verify(pw: str, acc: Dict[str, Any]) -> bool:
    return hmac.compare_digest(_hash(pw, bytes.fromhex(acc["salt"])), acc["hash"])
