import asyncio
import itertools
import os
from collections import deque
from typing import Any, Deque, Dict, Optional
import time

HOST = os.environ.get("TUIPET_HOST", "0.0.0.0")
PORT = int(os.environ.get("TUIPET_PORT", "8765"))
ACCOUNTS_PATH = os.environ.get("TUIPET_ACCOUNTS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "accounts.json"))
SAVES_PATH = os.environ.get("TUIPET_SAVES", os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves.json"))
BUGS_PATH = os.environ.get("TUIPET_BUGS", os.path.join(os.path.dirname(os.path.abspath(__file__)), "bugs.jsonl"))
FEED_PATH = os.environ.get("TUIPET_FEED", os.path.join(os.path.dirname(os.path.abspath(__file__)), "lobby_feed.jsonl"))
ADMIN_KEY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "admin.key")
PENDING_PATH = os.environ.get("TUIPET_PENDING", os.path.join(os.path.dirname(os.path.abspath(__file__)), "pending_pms.json"))
LADDER_PATH = os.environ.get("TUIPET_LADDER", os.path.join(os.path.dirname(os.path.abspath(__file__)), "ladder.json"))
RAID_PATH = os.environ.get("TUIPET_RAID", os.path.join(os.path.dirname(os.path.abspath(__file__)), "raid.json"))
RAID_POOL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raid_pool.json")
RAID_MULT_BY_NUM_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raid_stage_mult.json")

MAX_CLIENTS = 200
MAX_NAME = 24
MAX_PW = 128
MAX_CHAT = 400
MAX_MSG_BYTES = 64 * 1024
PBKDF2_ITERS = 100_000
MAX_BUG_TEXT = 2000
MAX_BUGS_PER_CONN = 5
MAX_BUG_FILE = 5 * 1024 * 1024
MAX_ANNOUNCE = 300
MAX_FEED = 2 * 1024 * 1024
MAX_PENDING_PER_ACCT = 50
SAVE_RETENTION_S = 365 * 86400
SAVE_STAMP_SLACK = 120.0
LADDER_PAYOUT = {1: 25000, 2: 10000, 3: 5000}
LADDER_PAIR_CAP = 3
LADDER_CONFIRM_S = 90.0
SMOKE_PREFIX = "smk"
RAID_HP_FLOOR = 5_000_000
RAID_HP_CAP = 440_000_000
RAID_GROW = 1.5
RAID_FIT = 0.9
RAID_COOLDOWN_S = 1440 * 60
RAID_WINDOW_S = 10080 * 60
RAID_ATTEMPTS_PER_DAY = 3
RAID_MAX_RAW = 20
RAID_DMG_MULT = 5000
RAID_RANK_BITS = {1: 5000, 2: 3000, 3: 2000}
RAID_RANK_ITEMS = {1: 3, 2: 2, 3: 1}
RAID_PART_BITS, RAID_PART_ITEMS = 500, 1
RAID_CONSOLATION = 100
RAID_ITEM_POOL = ["energy_drink", "vitamin", "textbook", "dna_crystal", "steak", "cake", "dumbbell", "x_antibody", "ball"]
RAID_HISTORY_KEEP = 5
MAX_ROOM = 32

_ids = itertools.count(1)

class Client:
    id: int
    ws: Any
    name: str
    pet: Dict[str, Any]
    live: bool
    lease: Optional[str]
    logged: bool
    boot: float
    bugs_sent: int
    room: Optional[str]
    _msg_tokens: float
    _msg_refill_t: float
    __slots__ = ("id", "ws", "name", "pet", "live", "lease", "logged", "boot",
                 "bugs_sent", "room", "_msg_tokens", "_msg_refill_t")
    def __init__(self, ws: Any) -> None:
        self.id = next(_ids)
        self.ws = ws
        self.name = f"guest{self.id}"
        self.pet: Dict[str, Any] = {}
        self.live = False
        self.lease: Optional[str] = None
        self.logged = False
        self.boot = 0.0
        self.bugs_sent = 0
        self.room = None
        self._msg_tokens = 50.0
        self._msg_refill_t = time.time()

CLIENTS: Dict[int, 'Client'] = {}
CHAT_BACKLOG: Deque[Any] = deque(maxlen=30)
LEASES: Dict[str, Any] = {}
BOOT_SEEN: Dict[str, Any] = {}
MAX_SEEN_BOOTS = 8
_saves_lock = asyncio.Lock()
_pending_lock = asyncio.Lock()

ACCOUNTS: Dict[str, Any] = {}
SAVES: Dict[str, Any] = {}
PENDING: Dict[str, Any] = {}
LADDER: Dict[str, Any] = {}
RAID: Dict[str, Any] = {}
RAID_MULT_BY_NUM: Dict[int, Any] = {}
