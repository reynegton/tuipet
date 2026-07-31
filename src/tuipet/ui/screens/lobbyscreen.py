"""Multiplayer lobby panel — name login, presence, chat, jogress + battle sessions.

Chat-focused layout: a scrolling chat log on the left, a roster sidebar on the
right. Phases:

  name     type a handle, Enter to join  (only when no cached tamer name)
  lobby    chat default; Up/Down pick a player; Enter on empty input opens that
           player's action menu ([B]attle / [J]ogress); invites pop a [Y]/[N]
  jogress  both relay their pet's attribute, each resolves its fusion locally
           (jogress.resolve), shows the result, Enter evolves the pet
  battle   seeded symmetric PvP (proto 2, canon BattleProtocol's peer-symmetric
           exchange with the desync solved): both relay battle cards carrying a
           nonce COMMITMENT, reveal the nonce with the first pick, and derive a
           shared PRNG seed -- then each round both exchange only their FINAL
           attribute pick and each side resolves the identical card-vs-card engine
           locally. Neither peer trusts the other's arithmetic, so the monthly
           ladder's both-reports-must-agree check is real. A peer whose card
           has no "proto" gets the pre-2 host-authoritative relay verbatim
           (the inviter resolves and mirrors absolute results). PvP wins
           record onto the pet (evolution credit) just like PvE.

Decoupled from the app: `on_connect(name, card) -> LobbyClient` lets the app own
the WebSocket worker's lifecycle. Colours come from the live theme.
"""
from __future__ import annotations

import hashlib
import random

from rich.text import Text

import tuipet.data.loaders.data as data
import tuipet.core.jogress as jogress
import tuipet.core.battle as battle
import tuipet.ui.screens.jogressscreen as jogressscreen
import tuipet.ui.components.menu as menu
import tuipet.utils.persistence as persistence
from tuipet.network.net import CHAT_CAP
from tuipet.utils.theme import INK, INK_B, DIM

CHATW = 25
ROSTW = 12
BODY = 8
CHAT_MAX = 400          # server MAX_CHAT: the local input buffer stops here too
# (ATTACK_KEYS left with the pick-a-move battle -- 0.5 BATTLE 2026-07-17)


# ⛔ THE CELL-WIDTH LAW (chat polish 2026-07-14).  The lobby is the ONE place a
# player types arbitrary text, and an emoji or a CJK glyph occupies TWO terminal
# cells while counting as ONE character.  `s[:w].ljust(w)` and `len(s)` measure
# CHARACTERS, so a line like "🔥🔥 emoji 日本語" overflowed its 25-column budget and
# shoved the roster divider `│` right off its column -- the layout visibly tore.
# Every width decision in this file goes through cell_len/set_cell_size/chop_cells.
# the split (modularize 2026-07-17): the login card, the chat surface and
# the bout engine live in their own modules; the old names stay importable
from tuipet.ui.screens.accountscreen import AccountPanel    # noqa: F401
from tuipet.network.lobbybout import BoutMixin, _clamp_card    # noqa: F401
from tuipet.network.lobbychat import (ChatMixin, HINTS_FOLDED, HINTS_OPEN,  # noqa: F401
                        _fit, _wrap, _tail_cells, _hpbar)
from tuipet.i18n.translator import t


class LobbyPanel(BoutMixin, ChatMixin):
    def __init__(self, pet, on_connect, name=None, pw=""):
        self.pet = pet
        self.on_connect = on_connect
        self.client = None
        self.state = None
        self.captures_text = True      # chat input — q is a typed character, never quit
        self.entry = None              # AccountPanel while logging in
        self._last_name = name or ""
        self.buf = ""
        self.sel = 0
        self.scroll = 0                # chat scrollback: lines back from live
        self.rost_hidden = False       # → folds the player box (chat takes the
        #                                full width, ↑↓ scroll the log); ← restores
        self.action_for = None
        self.pm_to = None              # (id, name): the input line is a PM compose
        self.invite_prompt = None
        self._sent_invites = set()     # (pid, kind) awaiting a response: an
        #                                invite_resp with no entry here is a
        #                                forgery and is dropped (a crafted
        #                                accept used to force this client into
        #                                a session -- including a PERMANENT
        #                                jogress fusion; audit 2026-07-19)
        self.dm_peer = None            # (id, name): the open DM thread
        self.dm_scroll = 0             # DM scrollback offset (0 = live tail)
        self.sfx = None
        # jogress session
        self.partner = None
        self.partner_species = None
        self.jphase = None
        self.jresult = None
        self.jshow = None             # the offline fusion scene, replayed here
        self.fail_reason = None
        self.j_confirmed = False           # two-phase commit: my yes is in
        self.j_partner_confirmed = False   # ...and theirs
        self.j_peer_two_phase = False      # the peer speaks the confirm protocol
        self.bshow = None             # the round's volley replay (BattlePanel shim)
        # battle session
        self.is_host = False
        self.battle = None
        self.opp_card = None
        self.bphase = None            # "card" | "choose" | "wait" | "over"
        self.bt_my_choice = None
        self.bt_opp_choice = None
        self.my_hp = self.my_max = 0
        self.opp_hp = self.opp_max = 0
        self.bt_log = ""
        self.bt_outcome = ""
        self.bt_reward = None
        self.bt_payload = None        # ("done", X) payload when the bout ends
        # seeded symmetric PvP (proto 3: the precomputed 0.5 race)
        self.bt_nonce = None          # my seed nonce (committed in my card msg)
        self.bt_peer_commit = None    # sha256 hex the peer committed to
        self.bt_peer_nonce = None     # revealed with the peer's first pick
        self.bt_my_card = None        # the exact clamped card I shipped (engine input)
        if name and pw:
            self._connect(name, pw)
        else:
            self.phase = "login"
            self.entry = AccountPanel(name=name or "")
            self.status = t("lob_msg_login", "Log in to the lobby.")
    def _connect(self, name, pw):
        self._last_name = name
        self.client = self.on_connect(name, pw, self._card())
        self.state = self.client.state
        import tuipet.utils.persistence as persistence
        self.state.blocked = persistence.get_blocked()
        # DM threads + unread badges reload from the last session -- leaving a
        # PM (or the lobby) never loses the conversation (Joel 2026-07-10).
        # Seed-only merge: anything already live in this state wins.
        saved_dms, saved_unread = persistence.get_dms()
        for peer, thread in saved_dms.items():
            self.state.dms.setdefault(peer, thread)
        self.state.unread |= saved_unread
        self.phase = "lobby"
        self.status = t("lob_msg_conn", "Connecting…")

    # ---- presence card ---------------------------------------------------
    def _card(self):
        _, by = data.load_sprites()
        info = by.get(self.pet.num, {})
        card = {"name": getattr(self.pet, "name", None) or info.get("name") or "Egg",
                "stage": self.pet.stage, "num": self.pet.num,
                "attr": getattr(self.pet, "attribute", "") or info.get("attribute") or "None"}
        # the worn honor rides the presence card (prestige sink 2026-07-14) --
        # the server stores and rebroadcasts the card verbatim, and clients
        # that predate titles simply ignore the extra field
        worn = data.title_name(persistence.get_title_worn())
        if worn:
            card["title"] = worn
        # the saved lock rides the presence card (lock rework 2026-07-23:
        # a lock now swings ±0.20 in a duel -- nobody should accept one
        # blind).  Same compat rule as title: the server rebroadcasts
        # verbatim, clients that predate it ignore the field.
        card["form"] = getattr(self.pet, "saved_hit_type", "normal") or "normal"
        return card
    def _session_gate(self, kind):
        """PURE session eligibility for a REMOTE invite.  can_battle is a
        player-poke: its guard DISTURBS a sleeper (wake + mood hit + disturb
        count) and rolls a refusal -- a stranger's invite must never touch
        the pet (asleep sweep 2026-07-06).  Mirrors the gates without the
        side effects; the SEND side keeps the poke (the player pressed it)."""
        p = self.pet
        if getattr(p, "dead", False):
            return t("lob_msg_rest", "It rests now.")     # the home screens teach N (the lobby's
            #                              N just types into chat -- round 30)
        if p.asleep:
            return t("lob_msg_asleep", "zzz… asleep")
        if kind == "jogress":
            # remote=True: no disturb, no refusal roll, no refuse ANIM --
            # a stranger's invite must never touch the pet (audit 2026-07-19)
            return jogress.can_jogress(p, remote=True)
        if p.stage in ("Egg", "Fresh"):
            return t("lob_msg_young", "Too young to battle.")
        # the same condition gates the SEND side enforces (can_battle), in
        # their pure form -- a starving/sick/drained pet used to auto-accept
        # bouts it could never send (gameplay audit 2026-07-19)
        return p.battle_condition()
    def _others(self):
        """Everyone else ONLINE, lobby regulars first, then the playing
        ghosts (presence 2026-07-05: the roster carries the whole server)."""
        others = self.state.others() if self.state else []
        return sorted(others, key=lambda p: (not p.get("live", True),
                                             str(p.get("name", "")).lower()))
    def _pet_of(self, pid):
        """'Agumon · Champion · lock mega' for a roster id ('' when
        unknown); a worn honor title trails as '· ★Bit Baron' (the
        marquee absorbs the length).  The LOCK shows so a challenge is
        never accepted blind (lock rework 2026-07-23: ±0.20 duel swing);
        presences from older clients simply omit it."""
        for pl in (self.state.roster if self.state else []):
            if pl["id"] == pid:
                pet = pl.get("pet") or {}
                nm, st = pet.get("name"), pet.get("stage")
                fm = str(pet.get("form") or "")
                lock = f" · lock {fm}" if fm else ""
                t = str(pet.get("title") or "")[:24]
                tail = f" · ★{t}" if t else ""
                return f"{nm} · {st}{lock}{tail}" if nm and st else (nm or "")
        return ""

    # ---- per-tick refresh (the 0.1s interval clock calls this) -----------
    def anim(self):
        self._mq = getattr(self, "_mq", 0) + 1   # drives long-field marquees
        if getattr(self, "phase", None) == "login" and getattr(self, "entry", None):
            self.entry.anim()                    # the login note's marquee clock
        # session replays advance first (they render whatever the wire does)
        if self.bshow is not None:
            b = self.bshow
            if b.i < len(b.timeline) - 1:
                b.anim()                        # advances + emits the volley sfx
                if getattr(b, "sfx", None):
                    self.sfx = b.sfx
                    b.sfx = None
            else:
                self.bshow = None               # volley done -> choose/over shows
        if self.jshow is not None and self.jphase == "result":
            self.jshow.anim()                   # converge -> flash -> fused bounce
        lad = getattr(self.client, "ladder", None) if self.client else None
        if lad and lad.get("award"):
            a = lad["award"]
            season = str(a.get("season") or "")
            sent = getattr(self, "_ladder_claims_sent", None) or set()
            if (season and season not in sent
                    and not persistence.ladder_award_claimed(season)):
                # ask the server; the payout waits for its ladder_reward ack
                # (server audit 2026-07-18: self-paying off the view let a
                # lost claim / second device re-collect -- raid_claim pattern).
                # The spam guard is SESSION-LOCAL: the old persistent note
                # here was a take-then-send -- a claim lost to a dropped
                # socket left the award orphaned forever, blocked by our own
                # note while the server still owed it (round 30).  The
                # durable note waits for the ack below.
                claim = getattr(self.client, "ladder_claim", None)
                if claim:
                    sent.add(season)
                    self._ladder_claims_sent = sent
                    claim(season)
        rew = getattr(self.client, "ladder_reward", None) if self.client else None
        if rew is not None:
            self.client.ladder_reward = None           # consumed once
            if rew.get("ok"):
                persistence.note_ladder_award(str(rew.get("season") or ""))
                self.pet.bits = min(self.pet.bits + int(rew.get("bits") or 0), 99999999)
                self.sfx = "champion"
                self.status = t("lob_msg_ladder_claim", "season {season}: rank {rank} — +{bits}b claimed!").format(season=rew.get('season'), rank=rew.get('rank'), bits=rew.get('bits'))
        s = self.state
        if not s:
            return
        if self.phase == "dm" and self.dm_peer:
            # the thread is OPEN on screen: an arriving PM is read the moment
            # it lands -- net.py badges every PM blind, and the badge used to
            # survive the very conversation you watched arrive (round 30)
            s.unread.discard(self.dm_peer[1])
        for m in list(s.inbox):
            msg_type = m.get("t")
            if msg_type == "invite":
                if m.get("kind") not in ("jogress", "battle"):
                    # the relay forwards kind verbatim: an unknown kind used
                    # to reach _enter_session, set a dangling partner and
                    # enter NO branch -- desync, not a session (audit
                    # 2026-07-13); auto-decline like the blocked path
                    self.client.respond(m.get("from_id"), m.get("kind"), False)
                    s.inbox.remove(m)
                    continue
                if m.get("from_name") in s.blocked:
                    self.client.respond(m.get("from_id"), m.get("kind"), False)
                    s.inbox.remove(m)
                    continue
                gate = self._session_gate(m.get("kind"))
                if gate:
                    # the pet can't honour this session (an egg, asleep...):
                    # auto-decline instead of prompting -- accepting used to
                    # start a bout the replay couldn't even render
                    # (egg-battle audit 2026-07-06)
                    self.client.respond(m.get("from_id"), m.get("kind"), False)
                    self.status = gate
                elif self.phase != "lobby" or self.invite_prompt is not None or self.action_for is not None:
                    self.client.respond(m.get("from_id"), m.get("kind"), False, busy=True)  # in a session
                elif self.buf or self.pm_to is not None:
                    # mid-sentence: the popped prompt would EAT the next
                    # keystroke -- typing "yeah" ACCEPTED a jogress on the y
                    # (lobby audit 2026-07-07).  Hold the invite in the inbox
                    # until the input line clears; the status says it's waiting.
                    self.status = t("lob_msg_inv_type", "{name} invites — finish typing").format(name=m.get('from_name', '?'))
                    continue
                else:
                    self.invite_prompt = m
                    self.sfx = "menu"
                s.inbox.remove(m)
            elif t == "invite_resp":
                s.inbox.remove(m)
                rk = (m.get("from_id"), m.get("kind"))
                if rk not in self._sent_invites:
                    continue        # a response to an invite never sent: forged
                self._sent_invites.discard(rk)
                if m.get("accept"):
                    if self.phase == "lobby":
                        self._enter_session(m.get("from_id"), m.get("from_name", "?"), m.get("kind"), host=True)
                    else:                                  # already busy -> free the accepter
                        self.client.relay(m.get("from_id"), {"kind": m.get("kind"), "abort": True})
                elif m.get("busy"):
                    self.status = t("lob_msg_busy", "{name} is busy.").format(name=m.get('from_name', '?'))
                else:
                    self.status = t("lob_msg_declined", "{name} declined.").format(name=m.get('from_name', '?'))
            elif t == "relay":
                s.inbox.remove(m)
                self._on_relay(m)
        if s.login_failed:
            self.entry = AccountPanel(name=self._last_name, note=s.login_failed)
            self.phase = "login"
            s.login_failed = None
        elif s.error:
            self.status = f"! {s.error}"
            s.error = None
        elif s.connected and self.status == "Connecting…":
            self.status = HINTS_OPEN
        # drop -> the client retries on its own; say so instead of stranding a banner
        if getattr(s, "reconnecting", False):
            self._seen_ids = None                  # a refilled roster is not a wave of joins
            self._sent_invites.clear()             # connection ids died with the drop
            if self.phase == "lobby":
                self.status = self._down_status()
            self._was_down = True
        elif s.connected and getattr(self, "_was_down", False):
            self._was_down = False
            if self.phase == "lobby":
                self.status = "Reconnected."
        # join/leave notices in the chat log (client-side roster diff)
        if s.connected:
            room = getattr(s, "room", None)
            if room != getattr(self, "_seen_room", None):
                # a room switch swaps the whole scope: not a wave of joins/leaves
                self._seen_room = room
                self._seen_ids = None
                if self.phase == "lobby":
                    self.status = (t("lob_msg_room", "room: {room} · /leave exits").format(room=room) if room
                                   else t("lob_msg_back_main", "Back in the main lobby."))
            # announce LIVE lobby presences only, and by NAME: a home-screen
            # sync ghost's reconnect churn (a fresh connection id on every
            # drop) spammed the chat with "roxi joined / roxi left" while
            # roxi was never in the lobby (Joel 2026-07-17).  Ghosts still
            # sit in the sidebar as "playing" -- silently; and a live
            # player's quick reconnect keeps its NAME, so no false wave.
            live = {pl["name"] for pl in s.roster
                    if pl.get("live", True) and pl["id"] != s.me_id}
            old = getattr(self, "_seen_ids", None)
            if old is not None:
                for nm in sorted(live - old):
                    s.chat.append(("", t("lob_msg_joined", "{nm} joined").format(nm=nm)))
                for nm in sorted(old - live):
                    s.chat.append(("", t("lob_msg_left", "{nm} left").format(nm=nm)))
                del s.chat[:-CHAT_CAP]      # the one cap, shared with net.py
            self._seen_ids = live
        # partner vanished mid-session
        if self.partner and not any(p["id"] == self.partner[0] for p in s.roster):
            if self.phase == "jogress" and self.jphase == "waiting":
                self.fail_reason, self.jphase = t("lob_msg_part_left", "Partner left."), "failed"
            elif self.phase == "jogress" and self.jphase == "result":
                self._return_to_lobby(t("lob_msg_part_left_nofuse", "Partner left — no fusion."))
            elif self.phase == "battle" and self.bphase not in (None, "over"):
                if self.bphase == "fight" and self.battle is not None:
                    self._opp_fled()     # a committed fight: their forfeit, my win
                else:
                    self.bt_outcome = t("lob_msg_opp_left", "Opponent left.")
                    self.bt_payload = ("battle_msg", t("lob_msg_opp_left_void", "Opponent left — battle void."))
                    self.bphase = "over"

    # ---- session orchestration ------------------------------------------
    def _enter_session(self, pid, pname, kind, host):
        if self.invite_prompt is not None:
            # a CROSSED invite (both players invited each other): entering the
            # session must consume the other prompt, or it survives the whole
            # bout and re-offers a dead invite back in the lobby (session
            # audit 2026-07-07)
            inv = self.invite_prompt
            self.invite_prompt = None
            self.client.respond(inv.get("from_id"), inv.get("kind"), False, busy=True)
        self.partner = (pid, pname)
        if kind == "jogress":
            card = self._card()
            opts = jogress.options(self.pet)
            self.client.relay(pid, {"kind": "jogress", "attr": card["attr"],
                                    "num": card["num"], "name": card["name"],
                                    # canon JogressProtocol.sendPlayerInfo ships the
                                    # jogressMatch string (reachable fusion NAMES +
                                    # pairable attributes) and the growth stage --
                                    # they drive the mutual both-or-neither match
                                    # (session audit 2026-07-07)
                                    "stage": self.pet.stage,
                                    "fusions": [o["name"] for o in opts],
                                    # exact-door companions I need (canon
                                    # one-sided jogress, audit 2026-07-17)
                                    "wants": [o["partner_num"] for o in opts
                                              if not o["partners"]],
                                    "attrs": jogress.pairable_attrs(self.pet),
                                    # canon JogressProtocol ships the REAL sick
                                    # state: fusing with a sick partner is a 90%
                                    # catch (jogress audit 2026-07-06)
                                    "sick": bool(getattr(self.pet, "sick", False)),
                                    # two-phase commit capability (consent audit
                                    # 2026-07-07): both players confirm at the
                                    # result screen before either pet fuses
                                    "confirm2": True})
            self.phase, self.jphase = "jogress", "waiting"
            self.status = t("lob_msg_fusing", "Fusing with {name}…").format(name=pname)
        elif kind == "battle":
            self.is_host = host
            self.phase, self.bphase = "battle", "card"
            card = battle.battle_card(self.pet)
            # the engine input must be the card AS THE PEER WILL SEE IT, so
            # clamp my own card exactly like _battle_begin clamps theirs
            self.bt_my_card = _clamp_card(card)
            # commit-reveal seed handshake: the nonce is COMMITTED before either
            # side has seen the other's (cards cross in flight), and revealed
            # with the first pick -- so neither client can grind the shared
            # seed for a favourable initiative coin flip.  Spiritually canon:
            # BattleProtocol exchanged a SHA-256 checksum at setup too.
            self.bt_nonce = random.getrandbits(64)
            commit = hashlib.sha256(str(self.bt_nonce).encode()).hexdigest()
            self.client.relay(pid, {"kind": "battle", "t": "card",
                                    "card": card, "commit": commit})
            self.status = t("lob_msg_battle_vs", "Battle vs {name}…").format(name=pname)
    def _return_to_lobby(self, status=""):
        """End the current session and drop back into the chat lobby (not out of it).
        Any pet change (a fusion) is pushed so the roster shows your new form."""
        had_partner = self.partner is not None
        self.partner = self.partner_species = self.jresult = None
        self.jphase = self.fail_reason = None
        self.j_confirmed = self.j_partner_confirmed = self.j_peer_two_phase = False
        self.jpartner_sick = False
        self.jshow = self.bshow = None
        self.battle = self.opp_card = self.bphase = None
        self.bt_my_choice = self.bt_opp_choice = None
        self.bt_log = self.bt_outcome = ""
        self.bt_reward = self.bt_payload = None
        self.bt_nonce = self.bt_peer_commit = self.bt_peer_nonce = None
        self.bt_my_card = None
        self.is_host = False
        self.phase = "lobby"
        self.status = status or t("lob_msg_back_lob", "Back in the lobby.")
        if had_partner and self.client:
            self.client.update_pet(self._card())
    def _on_relay(self, m):
        if not self.partner or m.get("from_id") != self.partner[0]:
            return
        payload = m.get("payload") or {}
        kind = payload.get("kind")
        if payload.get("abort"):                       # partner cancelled / got busy
            if self.phase == "jogress" and self.jphase == "waiting":
                self.fail_reason, self.jphase = t("lob_msg_part_left_fuse", "Partner left the fusion."), "failed"
            elif self.phase == "jogress" and self.jphase == "result":
                self._return_to_lobby(t("lob_msg_part_left_nofuse", "Partner left — no fusion."))   # pre-commit: nobody fuses
            elif self.phase == "battle" and self.bphase not in (None, "over"):
                if self.bphase == "fight" and self.battle is not None:
                    self._opp_fled()     # a committed fight: their forfeit, my win
                else:
                    self.bt_outcome = t("lob_msg_opp_left", "Opponent left.")
                    self.bt_payload = ("battle_msg", t("lob_msg_opp_left_void", "Opponent left — battle void."))
                    self.bphase = "over"
            return
        if kind == "jogress" and self.phase == "jogress" and payload.get("t") == "confirm":
            # two-phase commit: the partner said yes; fuse only when BOTH have
            self.j_partner_confirmed = True
            if self.jphase == "result" and self.j_confirmed:
                self._commit_fusion()
            return
        if kind == "jogress" and self.phase == "jogress" and payload.get("t") == "decline":
            if self.jphase in ("waiting", "result"):
                self._return_to_lobby(t("lob_msg_part_dec", "Partner declined — no one fused."))
            return
        if (kind == "jogress" and self.phase == "jogress"
                and self.jphase == "waiting" and payload.get("t") is None):
            self.j_peer_two_phase = bool(payload.get("confirm2"))
            self.partner_species = payload.get("name")
            self.jpartner_sick = bool(payload.get("sick"))   # contagion at the fuse
            reason = jogress.can_jogress(self.pet)      # honour asleep / too-young, like offline
            self.jresult = None if reason else jogress.resolve_online(self.pet, payload)
            if self.jresult:
                self.jphase = "result"
                self.sfx = "jogress"
                # the REAL fusion scene (lobby audit 2026-07-04: the old
                # lobby printed text while the fusion deserved its converge +
                # flash) -- both parents' actual sprites play the panel's beats
                if self.jresult.get("companion"):
                    self.jshow = None       # the text page: it lends, not fuses
                else:
                    self.jshow = jogressscreen.JogressPanel(
                        self.pet, self.pet.num,
                        payload.get("num") or self.pet.num,
                        self.jresult["num"])
            else:
                self.fail_reason = reason or t("lob_msg_no_reso", "No resonance with that partner.")
                self.jphase = "failed"
                # tell the partner so it can't hang at its result screen waiting
                # for a confirm we'll never send (resolve_online is symmetric, so
                # this only bites on a mid-handshake state change -- a pet that
                # dozed off or lost DP after inviting; jogress audit 2026-07-08)
                if self.partner:
                    self.client.relay(self.partner[0], {"kind": "jogress", "abort": True})
        elif kind == "battle" and self.phase == "battle":
            bt = payload.get("t")
            # each relay type is only honoured in the phase that expects it
            # (session audit 2026-07-07): an unguarded 'card' mid-fight
            # re-ran _battle_begin and RESET both HP bars; a stray 'result'
            # outside the guest's wait re-applied a stale round
            if bt == "card" and self.bphase == "card":
                self._battle_begin(payload.get("card") or {}, payload.get("commit"))
            elif bt == "pick" and self.bphase in ("card", "wait", "fight"):
                # proto 3 (0.5 BATTLE 2026-07-17): no picks in this world --
                # the "pick" message carries only the revealed seed nonce
                if self.bt_peer_nonce is None:
                    self.bt_peer_nonce = payload.get("nonce")
                    self._maybe_build()

    # ---- battle ----------------------------------------------------------
    def key(self, k):
        if self.phase == "login":
            return self._key_login(k)
        if self.phase == "jogress":
            return self._key_jogress(k)
        if self.phase == "battle":
            return self._key_battle(k)
        if self.phase == "dm":
            return self._key_dm(k)
        if self.phase == "ladder":
            return self._key_ladder(k)
        return self._key_lobby(k)
    def _down_status(self):
        """The banner while the client retries.  "Lost" only when a session
        EXISTED: a first-ever failed connect (offline, wrong server) used to
        claim a drop that never happened (QOL sweep 2026-07-23)."""
        return (t("lob_msg_conn_lost", "Connection lost — reconnecting…")
                if getattr(self.client, "_had_welcome", False)
                else t("lob_msg_cant_reach", "Can't reach the lobby — retrying…"))

    def _key_ladder(self, k):
        # q/g trimmed (grammar sweep 2026-07-18): they were unexplained
        # extra closes that shadowed q=quit / g=options muscle memory
        if k == "tab" and self._ladder_stalled():
            # the timed-out page promises "TAB retry" -- deliver it; with
            # data on screen TAB stays the way back (QOL sweep 2026-07-23)
            if self.client:
                self.client.ladder_get()
            self._ladder_asked = getattr(self, "_mq", 0)
            return None
        if k in ("escape", "tab"):
            self.phase = "lobby"
        return None

    def _ladder_stalled(self):
        """No reply ~5s after the ask (the 10 Hz clock) -- offline right as
        TAB was pressed used to strand 'fetching…' forever."""
        lad = getattr(self.client, "ladder", None) if self.client else None
        return lad is None and (getattr(self, "_mq", 0)
                                - getattr(self, "_ladder_asked", 0)) > 50
    def _text_ladder(self):
        """The monthly rankings: online PvP wins, top ten, your rank, and the
        days left in the season.  Data is the server's ladder message; a page
        opened before the reply shows a fetching line and fills in live."""
        t_obj = Text()
        lad = getattr(self.client, "ladder", None) if self.client else None
        if not lad:
            t_obj.append(t("lob_lad_hdr", "  LADDER\n\n"), style=INK_B)
            if self._ladder_stalled():
                t_obj.append(t("lob_lad_err_1", "  couldn't reach the ladder —\n"), style=DIM)
                t_obj.append(t("lob_lad_err_2", "  TAB retry · ESC back\n"), style=DIM)
            else:
                t_obj.append(t("lob_lad_fetching", "  fetching the rankings…\n"), style=DIM)
            return t_obj
        t_obj.append(t("lob_lad_season", "  LADDER  season {season}\n").format(season=lad.get('season', '?')), style=INK_B)
        # no blank separator rows: header + tagline + top-8 + you + season is
        # EXACTLY the 12-row LCD -- the old blanks pushed "you: rank" and
        # "season resets" (the page's whole point) off the box (round 30)
        t_obj.append(t("lob_lad_rule", "  one win = one rung · online only\n"), style=DIM)
        top = list(lad.get("top") or [])[:8]
        you_rank, you_wins = (lad.get("you") or [0, 0])[:2]
        if not top:
            t_obj.append(t("lob_lad_empty_1", "  no wins recorded yet — the rungs\n"), style=INK)
            t_obj.append(t("lob_lad_empty_2", "  are empty.  Go start the race!\n"), style=INK)
        me = str(getattr(self.client, "name", "") or "").lower()
        for i, (who, wins) in enumerate(top, start=1):
            # the server logs you in under the CANONICAL capitalisation; a
            # typed-case name missed its own row on an exact compare
            mine = bool(me) and str(who).lower() == me
            t_obj.append(f"  {'▸' if mine else ' '}{i:>2}. {str(who)[:16]:<16} {int(wins):>3}W\n",
                     style=INK_B if mine else INK)
        if you_rank:
            t_obj.append(t("lob_lad_you", "  you: rank {rank} · {wins} win(s)\n").format(rank=you_rank, wins=you_wins),
                     style=INK_B)
        else:
            t_obj.append(t("lob_lad_unranked", "  you: unranked — win online to climb\n"), style=DIM)
        d = int(lad.get("days_left") or 0)
        t_obj.append(t("lob_lad_res_today", "  season resets today\n") if d == 0 else
                 t("lob_lad_res_days", "  season resets in {d} day(s)\n").format(d=d), style=DIM)
        return t_obj
    def _key_login(self, k):
        r = self.entry.key(k)
        if r is not None and r[0] == "done":
            if r[1] is None:
                return ("done", None)            # Esc -> leave the lobby
            self._connect(*r[1])
        return None
    def _key_lobby(self, k):
        if self.invite_prompt is not None:
            inv = self.invite_prompt
            if k in ("y", "Y"):
                self.client.respond(inv.get("from_id"), inv["kind"], True)
                self.invite_prompt = None
                self._enter_session(inv.get("from_id"), inv.get("from_name", "?"), inv["kind"], host=False)
            elif k in ("n", "N", "escape"):
                self.client.respond(inv.get("from_id"), inv["kind"], False)
                self.status, self.invite_prompt = t("lob_msg_declined_self", "Declined."), None
            return None
        if self.action_for is not None:
            pid, pname, plive = self.action_for
            if k in ("b", "B") and plive:
                err = self.pet.can_battle()      # an egg was free to INVITE (egg-battle audit 2026-07-06)
                if err:
                    self.status, self.action_for = err, None
                    return None
                self.client.invite(pid, "battle"); self._sent_invites.add((pid, "battle")); self.status = t("lob_msg_inv_bat", "Battle invite → {name}").format(name=pname); self.action_for = None
            elif k in ("j", "J") and plive:
                err = jogress.can_jogress(self.pet)
                if err:
                    self.status, self.action_for = err, None
                    return None
                self.client.invite(pid, "jogress"); self._sent_invites.add((pid, "jogress")); self.status = t("lob_msg_inv_jog", "Jogress invite → {name}").format(name=pname); self.action_for = None
            elif k in ("p", "P") and not plive:
                self.client.ping(pid)
                self.status = t("lob_msg_pinged", "Pinged {name} — asked them to hop in the lobby!").format(name=pname)
                self.action_for = None
            elif k in ("v", "V"):
                self.phase, self.dm_peer, self.buf = "dm", (pid, pname), ""
                self.dm_scroll = 0             # a fresh thread opens live
                self.state.unread.discard(pname)
                self._save_dms()               # the read badge sticks
                self.action_for = None
            elif k in ("x", "X"):
                import tuipet.utils.persistence as persistence
                b = self.state.blocked
                if pname in b:
                    b.discard(pname); self.status = t("lob_msg_unblocked", "Unblocked {name}.").format(name=pname)
                else:
                    b.add(pname)
                    # net.py filters them out from here on, but everything they
                    # ALREADY said stayed on screen -- so "Blocked X." was only
                    # half true and the spam you muted was still sitting there.
                    # A mute means MUTE: sweep their lines out of the log too.
                    st = self.state
                    st.chat[:] = [(nm, tx) for nm, tx in st.chat if nm != pname]
                    st.unread.discard(pname)
                    self.status = t("lob_msg_blocked", "Blocked {name}.").format(name=pname)
                persistence.set_blocked(b)
                self.action_for = None
            elif k in ("m", "M"):
                # compose a private message: the input line retargets
                self.pm_to = (pid, pname)
                self.buf = ""
                self.status = t("lob_msg_pm_comp", "PM → {name} — ENTER send, ESC cancel").format(name=pname)
                self.action_for = None
            elif k == "escape":
                self.action_for = None
            return None
        if k == "tab":
            # the MONTHLY LADDER (2026-07-14): online wins, fresh race each
            # month.  TAB because every letter belongs to the chat input.
            if self.client:
                self.client.ladder_get()       # refresh; the page renders live
            self._ladder_asked = getattr(self, "_mq", 0)   # the fetch clock
            self.phase = "ladder"
            return None
        if k == "escape":
            if self.scroll:                    # scrolled log: snap to live first
                self.scroll = 0
                return None
            if self.pm_to is not None:
                self.pm_to, self.buf = None, ""
                self.status = t("lob_msg_pm_canc", "PM cancelled.")
                return None
            self._save_dms()                   # leaving the lobby keeps the threads
            return ("done", None)
        if k == "pageup":
            # chat scrollback (polish 2026-07-07): CHAT_CAP lines of history
            # existed but only the last 8 ever showed
            self.scroll += BODY - 1            # _text_lobby clamps to the log
            return None
        if k == "pagedown":
            self.scroll = max(0, self.scroll - (BODY - 1))
            return None
        if k == "right" and not self.rost_hidden:
            # fold the player box: the chat gets the full width (Joel 2026-07-10)
            self.rost_hidden = True
            self.status = HINTS_FOLDED
            return None
        if k == "left" and self.rost_hidden:
            self.rost_hidden = False
            self.status = HINTS_OPEN
            return None
        if k == "up":
            if self.rost_hidden:
                self.scroll += 1               # older; _text_lobby clamps to the log
            else:
                self.sel = max(0, self.sel - 1)
            return None
        if k == "down":
            if self.rost_hidden:
                self.scroll = max(0, self.scroll - 1)
            else:
                self.sel = min(max(0, len(self._others()) - 1), self.sel + 1)
            return None
        if k == "enter":
            self.scroll = 0                    # speaking snaps the view live
            down = self.state is not None and not self.state.connected
            if self.pm_to is not None:
                if self.buf.strip():
                    self.client.pm(self.pm_to[0], self.buf.strip(), self.pm_to[1])
                    self.status = (t("lob_msg_pm_q_off", "✉ queued for {name} — offline").format(name=self.pm_to[1])
                                   if down else t("lob_msg_pm_sent", "✉ sent to {name}").format(name=self.pm_to[1]))
                self.pm_to, self.buf = None, ""
            elif self.buf.strip():
                txt = self.buf.strip()
                self.buf = ""
                if txt.startswith("/"):
                    self._slash(txt)
                else:
                    self.client.chat(txt)
                    if down:
                        # the line vanishes from the input and only reappears
                        # on the server echo -- SAY it's queued, or a laggy
                        # send reads as a lost message (QOL sweep 2026-07-23)
                        self.status = t("lob_msg_off_q", "Offline — queued, sends on reconnect.")
            elif down and getattr(self.state, "reconnecting", False):
                # an empty ENTER while down = "try again NOW"
                if self.client is not None and hasattr(self.client, "retry_now"):
                    self.client.retry_now()
                    self.status = t("lob_msg_retry", "Retrying now…")
            else:
                others = self._others()
                if others and not self.rost_hidden:   # no acting on an unseen pick
                    p = others[min(self.sel, len(others) - 1)]
                    self.action_for = (p["id"], p["name"], p.get("live", True))
            return None
        return self._edit(k)
    def _edit(self, k):
        if k == "backspace":
            self.buf = self.buf[:-1]
        elif k == "space":
            self.buf += " "
        elif len(k) == 1 and k.isprintable():
            self.buf += k
        # cap at the server's MAX_CHAT (chat-input audit 2026-07-07): the buffer
        # was unbounded -- a long paste grew it without limit (the server clips
        # the SENT text at 400, but the local buffer never stopped growing)
        self.buf = self.buf[:CHAT_MAX]
        return None

    # ---- render ----------------------------------------------------------
    def _care_cue(self):
        """The care alarm's on-screen half while the lobby TICKS (2026-07-13:
        the lobby is no longer a pause room -- app.on_tick runs the life-sim
        through chat, so the strip must carry the nag or the pet starves
        silently behind the chat window).  Compact by design: name(10) +
        the loudest need, <= 38 plain cols with the ESC hint."""
        import tuipet.utils.theme as theme
        p = self.pet
        if not p.needs_attention():
            return ""
        if p.asleep and p.lights:
            w = t("lob_alarm_lights", "lights!")
        elif p.sick:
            w = t("lob_alarm_sick", "sick!")
        elif p.hunger == 0:
            w = t("lob_alarm_hungry", "hungry!")
        elif p.strength == 0:
            w = t("lob_alarm_effort", "effort empty!")
        elif p.poop >= 3:
            w = t("lob_alarm_messy", "messy!")
        elif p.energy <= 0:
            w = t("lob_alarm_exh", "exhausted!")
        else:
            w = t("lob_alarm_mis", "misbehaving!")
        return (f"[{theme.NEG}]⚠ {(p.name or '?')[:10]} {w}[/] [dim]·[/] "
                + menu.hints(("ESC", t("lob_hint_home", "home"))))
    def strip(self):
        """The message box under the LCD = the lobby's CONTEXT layer (hint
        overhaul 2026-07-10): session scenes keep their prompts, every other
        phase pops the hints for exactly what the keys do right now."""
        if self.bshow is not None:
            return f"[dim]{t('lob_hint_skip', 'SPACE skip')}[/]"
        if self.jshow is not None and self.jphase == "result":
            name = (self.jresult or {}).get("name", "?")
            if self.jshow.phase == "fused":
                # every variant <= 40 with the longest dex name (menu-bounds
                # budget): 2+19+11 / 2+19+19 / 2+19+13
                if self.j_confirmed and not self.j_partner_confirmed:
                    return t("lob_msg_wait", "→ [b]{name}[/]  [dim]· waiting…[/]").format(name=name)
                if self.j_peer_two_phase:
                    return t("lob_msg_fuse_esc", "→ [b]{name}[/] [dim]· ENTER fuse · ESC[/]").format(name=name)
                return t("lob_msg_fuse", "→ [b]{name}[/]  [dim]· ENTER fuse[/]").format(name=name)
            return t("lob_msg_dna_conn", "DNA… connect!  [dim]· ENTER skip[/]")
        if self.phase in ("jogress", "battle"):
            return ""                      # session text phases prompt in-LCD
        if self.phase == "login":
            # ESC at login leaves the lobby entirely -> "out", the app's
            # leave-to-home word (grammar sweep 2026-07-18)
            return menu.hints(("TAB", t("lob_hint_field", "field")), ("ENTER", t("lob_hint_go", "go")), ("ESC", t("lob_hint_out", "out")))
        if self.phase == "ladder":
            return menu.hints(("TAB", t("lob_hint_lobby", "lobby")), ("ESC", t("lob_hint_back", "back")))
        if self.phase == "dm":
            cue = self._care_cue()      # the DM thread live-ticks too
            if cue:
                return cue
            if getattr(self, "_dm_overflow", False):
                # history above the window: advertise the log keys (the
                # saved-note variant would blow the 40-col budget with them)
                return menu.hints(("ENTER", t("lob_hint_send", "send")), ("PgUp", t("lob_hint_log", "log")),
                                  ("ESC", t("lob_hint_back", "back")))
            return menu.hints(("ENTER", t("lob_hint_send", "send")), ("ESC", t("lob_hint_back", "back"))) + \
                t("lob_hint_saved", "  [dim]— thread saved[/]")
        if self.invite_prompt is not None:
            return menu.hints(("Y", t("lob_hint_acc", "accept")), ("N", t("lob_hint_dec", "decline")))
        if self.action_for is not None:
            _, pname, plive = self.action_for
            if self.state and pname in self.state.blocked:
                # mirror the in-LCD line: a blocked name offers the way back
                # out, nothing else (round 30: the two surfaces disagreed)
                return menu.hints(("X", t("lob_hint_unblock", "unblock")), ("ESC", t("lob_hint_back", "back")))
            if plive:
                # exactly 40 plain cols -- M was a working key advertised
                # NOWHERE (round 30)
                return menu.hints(("B", t("lob_hint_battle", "battle")), ("J", t("lob_hint_jog", "jog")), ("V", t("lob_hint_dm", "DM")),
                                  ("M", t("lob_hint_pm", "PM")), ("X", t("lob_hint_block", "block")))
            return menu.hints(("P", t("lob_hint_ping", "ping")), ("V", t("lob_hint_dm", "DM")), ("M", t("lob_hint_pm", "PM")),
                              ("X", t("lob_hint_block", "block")))
        if self.pm_to is not None:
            return menu.hints(("ENTER", t("lob_hint_send_env", "send ✉")), ("ESC", t("lob_hint_canc", "cancel")))
        # the pet's alarm outranks everything social -- it only fires in the
        # phases the app live-ticks (lobby/dm), which are exactly the phases
        # that reach here past the session/login/prompt returns above
        cue = self._care_cue()
        if cue:
            return cue
        # the open room: a fresh ✉ pops its own nudge ahead of the key chrome
        unread = sorted(self.state.unread) if self.state else []
        if unread and not self.rost_hidden:
            who = unread[0][:12] + ("…" if len(unread) > 1 else "")
            return t("lob_msg_unread", "[b]✉ {who}[/][dim] unread — V on their name[/]").format(who=who)
        if self.rost_hidden:
            return menu.hints(("←", t("lob_hint_players", "players")), ("↑↓", t("lob_hint_scroll", "scroll")),
                              ("ESC", t("lob_hint_live", "live/leave")))
        return menu.hints(("→", t("lob_hint_fold", "fold")), ("↑↓", t("lob_hint_pick", "pick")),
                          ("ENTER", t("lob_hint_act", "act")), ("PgUp", t("lob_hint_log", "log")))
    def text(self):
        if self.phase == "login":
            return self._text_login()
        if self.phase == "jogress":
            return self._text_jogress()
        if self.phase == "battle":
            return self._text_battle()
        if self.phase == "dm":
            return self._text_dm()
        if self.phase == "ladder":
            return self._text_ladder()
        return self._text_lobby()
    def _text_login(self):
        return self.entry.text()
