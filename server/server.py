"""tuipet lobby server — a standalone WebSocket relay with named accounts."""
from __future__ import annotations

import sys
import state
import accounts
import cloud
import messaging
import ladder
import raid
import core

# Forward imports to state so that if tests monkeypatch `server`, they patch `state`!
for mod in (accounts, cloud, messaging, ladder, raid, core):
    for k, v in mod.__dict__.items():
        if not k.startswith("__"):
            setattr(state, k, v)

sys.modules[__name__] = state

if __name__ == "__main__":
    core.run()
