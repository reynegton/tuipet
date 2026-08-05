# LOBBY AUDIT — the online half, end to end (2026-07-25)

Joel: "lets do a full blown lobby audit next."

Scope: the lobby screen (chat, roster, presence, PMs, invites, blocking,
rooms, the ladder), the bout and jogress sessions, `net.py`'s client, the
cloud-save leases, and the relay itself.  Method as before — **run it**:
crafted messages through the real inbox, the bout's paths under network
races, every page measured against the box, and finally **two real bots on
the live relay**.

**Verdict: the lobby held everywhere I pushed it — and the thing that was
broken was the alarm, not the machine.**

---

## 1. F1 — THE LIVE SMOKE HAD BEEN FAILING BY CONSTRUCTION  ✅ FIXED

`tools/pvp_smoke.py` is the only check that covers the online path end to
end: two real accounts, the real relay, the real invite → accept →
commit-reveal bout.  Its own docstring says to run it **after any change
that touches the lobby, the bout engine, net.py or server/server.py**, and
it exists because a payout crash once shipped that no unit test could see.

I ran it.  The bout completed on the live relay — and the tool failed:

```
A result: YOU LOSE…      B result: ★ YOU WIN! ★
AssertionError: both pets must record the bout (got 0)
```

The game was right and the tool was wrong.  That assertion (`battles == 2`)
encodes the PRE-**L17** rule.  L17 shipped **2026-07-20** (v0.5.103):
online PvP is progression-neutral, so `record_battle(online=True)` bills
the body and returns *before* battles/wins/exp/KO6/battle_log — precisely
so a colluding pair cannot farm them.  The tool was last touched
**2026-07-17**.

So from v0.5.103 onward the smoke could only fail, on every lobby, net and
server change since — **including the ones in this session**.  A safety net
that always fails is not a net; it is a thing people learn to step over.

Its contract now matches the shipped rule, and it asserts the *right*
things about an online bout:

- the local record is **untouched** (battles and wins both 0),
- the **body is still billed** (both sides spend energy),
- **both purses land** (winner's prize + consolation, server-side),
- exactly one side reads as the winner.

Re-flown against the live relay: **PVP LIVE SMOKE OK**.

`tests/test_lobby_audit.py` pins the same L17 properties at the unit level,
so the code and the tool can no longer drift apart in silence.

## 2. HELD UNDER PROBING (each one is now pinned)

**The doors a stranger can knock on** — every one answered correctly:

- an `invite_resp` for an invite I never sent is **dropped** (C5's forged
  accept, which once could force a *permanent jogress fusion*);
- a drop **clears the invite ledger**, so a stale accept after reconnect
  lands nowhere;
- an **unknown invite kind** is auto-declined rather than entering a
  session with no branch;
- a **blocked peer's** invite never reaches the prompt, and blocking
  sweeps their existing lines out of the log while `net.py` drops what
  comes next — the mute is a real mute, both halves;
- an invite arriving **mid-sentence** is HELD in the inbox with the status
  saying so, instead of popping a prompt that eats your next keystroke
  (typing "yeah" used to accept a fusion on the *y*).

**The bout's accounting, under the races that actually happen**: a forfeit
files exactly one loss and a late abort crossing it on the wire adds
nothing; an opponent's flight pays exactly once even if the abort repeats;
a pre-bell walk-out costs nothing.

**Every page fits the box** (12×40): lobby, roster folded, action menu, PM
compose, invite prompt, DM thread, ladder, and the bout/jogress pages.  The
ladder measures 12 exactly — round 30's fix has held.

**The cloud-save lease** reads correct by design: the lease belongs to the
newest *launch* (boot-stamped), seniority is decided by the server's
first-seen time rather than by comparing devices' clocks, and a startup
pull refuses a malformed or foreign-format blob rather than wiping a valid
local save.

## 3. SHIPPED

**v0.5.253** — F1 (the smoke's contract) plus `tests/test_lobby_audit.py`
(19 pins).  Suite 2044 → 2063.  Live: two bots, one relay, one bout, OK.
