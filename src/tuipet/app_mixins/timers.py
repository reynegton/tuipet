from __future__ import annotations
import tuipet.data.loaders.data as data
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
import tuipet.ui.components.menu as menu
from tuipet.core.petbase import POOPDANCE_AT
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.network.net as net
import tuipet.core.shop as shop
from tuipet.app import _hud_esc, PLAY_LEAD, PLAY_HOP
import random

class TimersMixin:
    def _drain_pms(self) -> None:
            """Private messages land on the always-on sync connection; surface
            them as ✉ flashes in the home message box.  While the LOBBY is open
            its chat already shows them (the server delivers to both connections)
            -- drop the duplicates; in any other sub-screen they stay queued and
            flash when you're back home (presence 2026-07-05)."""
            sync = getattr(self, "_sync", None)
            if sync is None or not getattr(sync, "inbox", None):
                return
            if isinstance(self.mode, lobbyscreen.LobbyPanel):  # type: ignore
                st = self.mode.state  # type: ignore
                if st is None:
                    return                     # login phase: keep them queued
                if not st.connected:
                    # PMs that arrived BEFORE this lobby session's client existed
                    # (queued under another sub-screen, or landing in the connect
                    # window) are in no chat history -- the old clear() burned
                    # them unseen (message audit 2026-07-06).  Seed the fresh
                    # pane; once CONNECTED the lobby client receives its own
                    # copy, so then (and only then) the ghost's are duplicates.
                    for nm, tx in sync.inbox:
                        st.chat.append((nm if nm == "📢" else f"✉{nm}", tx))
                    del st.chat[:-net.CHAT_CAP]
                sync.inbox.clear()
                return
            if self.mode is not None:  # type: ignore
                return                             # queued: flashes back on the home screen
            if self._flash_t > 0:  # type: ignore
                return                             # one ✉ at a time: let the current flash hold
            nm, tx = sync.inbox.pop(0)
            # a PM's sender name AND body are REMOTE strings -- escape their '[' so
            # a message like '[/]' can't unbalance this markup and crash the render
            # (Rich-brackets hard rule, remote-triggered; chat-input audit 2026-07-07).
            # The lobby chat pane is already safe (Text.append renders literally);
            # this flash is the one markup-parsed sink for remote text.
            if nm == "📢":                       # a server announcement, not a peer's ✉
                self.flash(f"📢 [b]{_hud_esc(tx)}[/]")  # type: ignore
            else:
                self.flash(f"✉ [b]{_hud_esc(nm)}[/]: {_hud_esc(tx)}")  # type: ignore
            self.beep("menu", bell=False)  # type: ignore

    def _drain_verdict(self) -> None:
            note = getattr(self, "_verdict_note", "")
            if note and self.mode is None:  # type: ignore
                self._verdict_note = ""
                self.flash(note)  # type: ignore

    def _drain_beep_q(self) -> None:
            """One frame-tick of the pattern queue (counts down; 0 fires)."""
            q = getattr(self, "_beep_q", None)
            if not q:
                return
            self._beep_q = [t - 1 for t in q if t > 0]
            if any(t <= 0 for t in q):
                self.beep("alarm", bell=False)  # type: ignore

    def on_frame(self) -> None:                        # single DVPet interval clock (10 Hz, 0.1s): main view AND sub-screens
            menu.TICK += 1                         # the shared note marquee clock: no screen clips a message
            self._drain_beep_q()                   # the alarm-pattern tail (#8): extra rings land here
            self._hud_marquee()                    # type: ignore
            self._drain_pms()                      # ✉ alerts ride the message box (presence 2026-07-05)
            self._drain_verdict()                  # a parked worker-verdict flashes back home (rounds 19/21/22)
            if self.mode is not None:  # type: ignore
                if hasattr(self.mode, "anim"):  # type: ignore
                    self.mode.anim()  # type: ignore
                    snd = getattr(self.mode, "sfx", None)   # type: ignore
                    if snd:
                        self.beep(snd, bell=False)  # type: ignore
                        self.mode.sfx = None  # type: ignore
                    self.screen_w.update(self._center(self.mode.text()))  # type: ignore
                    self._mode_strip()  # type: ignore
                    painter = self._status_painter()  # type: ignore
                    if painter is not None:
                        painter()
                    else:
                        # the LIVENESS LAW reaches the road (audit 2026-07-25):
                        # panels outside the statusbox registry -- the adventure
                        # march above all -- left the vitals card frozen between
                        # keypresses while energy, bits and hearts moved.  Same
                        # fallback repaint() has always used.
                        self.stats_w.paint(self.pet)  # type: ignore
                    ac = getattr(self.mode, "auto_close", None)  # type: ignore
                    if ac is not None:
                        # a panel finished its own exit beat (the adventure
                        # homecoming fade) and asks to close from anim()
                        self.mode.auto_close = None  # type: ignore
                        self._close_mode(ac[1])  # type: ignore
                return
            sc = self.screen_w  # type: ignore
            if sc.fx:
                sc.advance_fx()
                sc.paint(self.pet)  # type: ignore
                if sc.fx and sc.fx["kind"] == "cheer" and sc.fx["step"] == 0 \
                        and not sc.fx.get("icon") and self.pet.pending_prize:  # type: ignore
                    # a surprise-opener's show just chained into its cheer: the
                    # cheer HOLDS the prize sprite (Joel 2026-07-28) -- attach
                    # at beat 0 so the whole celebration shows what was won
                    sc.fx["icon"] = shop.ICON_KEYS.get(self.pet.pending_prize)  # type: ignore
                    self.pet.pending_prize = ""  # type: ignore
                elif not sc.fx and self.pet.pending_prize:  # type: ignore
                    # ...and a show that ends WITHOUT a chained cheer (the
                    # chocolate egg's eat) gets one, carrying the prize
                    icon = shop.ICON_KEYS.get(self.pet.pending_prize)  # type: ignore
                    self.pet.pending_prize = ""  # type: ignore
                    sc.start_fx("cheer", icon=icon)
                    sc.paint(self.pet)  # type: ignore
                if (not sc.fx and self.pet.pending_lights_out  # type: ignore
                        and not self.pet.asleep):  # type: ignore  # type: ignore
                    # the debt outlived its sleep some OTHER way: drop it, a
                    # dark room around an awake pet serves nobody (audit r2)
                    self.pet.pending_lights_out = False  # type: ignore
                if not sc.fx and self.pet.pending_lights_out:  # type: ignore
                    # the Sleep Pill's room drops HERE, on the beat its eat show
                    # ends (bug report 2026-07-26) -- deliberately NOT part of the
                    # pending_* elif chain below, which is one-branch-per-frame:
                    # the switch must never cost the evolve/gift/dying beat its turn.
                    self.pet.pending_lights_out = False  # type: ignore
                    self.pet.lights = False  # type: ignore
                    sc.paint(self.pet)          # type: ignore
                if sc.fx:
                    # beat-scripted fx sounds: eat's per-bite map + the generic snds map
                    # (refuse head-shakes, the evolve burst, the dnaWash entry, ...)
                    snd = (sc.fx.get("bite_snds", {}).get(sc.fx["step"])
                           or sc.fx.get("snds", {}).get(sc.fx["step"]))
                    if snd:
                        self.beep(snd, bell=False)  # type: ignore
                    if sc.fx["kind"] == "eat":     # live DVPet feeding readout (calorie + P/M/V)
                        self._status_eat()  # type: ignore
                    elif (sc.fx["kind"] == "play" and sc.fx["step"] >= PLAY_LEAD
                            and (sc.fx["step"] - PLAY_LEAD) % PLAY_HOP == 0):
                        self.beep("happy", bell=False)   # type: ignore
                elif getattr(self, "_pending_evolve", None) is not None and self.screen_w.fx is None:  # type: ignore
                    old_num, self._pending_evolve = self._pending_evolve, None  # type: ignore
                    self.screen_w.start_fx("evolve", old_num=old_num)  # type: ignore
                elif getattr(self, "_pending_gift_reveal", None) and self.screen_w.fx is None:  # type: ignore
                    # the present is opened: the surprise reveal lands now (2026-07-24)
                    reveal, self._pending_gift_reveal = self._pending_gift_reveal, None  # type: ignore
                    self._do(reveal)  # type: ignore
                elif self._dying_fx:               # type: ignore
                    self._dying_fx = False
                    hits = getattr(self, "_revive_hits", 0)
                    self._revive_hits = 0
                    from tuipet.core.pet import HITS_TO_SAVE
                    if hits > HITS_TO_SAVE * (self.pet.saved_from_death + 1):  # type: ignore
                        old_num = self.pet.save_from_death()  # type: ignore
                        if old_num is not None:            # the dark rebirth
                            self.flash(f"[b]{self.pet.name}![/] Voltou... diferente.")  # type: ignore
                            self.screen_w.start_fx("evolve", old_num=old_num)  # type: ignore
                        else:
                            self.flash(f"[b]{self.pet.name}[/] se apega à vida!")  # type: ignore
                            self.screen_w.start_fx("cheer")  # type: ignore
                        persistence.save(self.pet)  # type: ignore
                    else:
                        self._death_ceremony(hold=20)  # type: ignore
                else:                              # any other fx just finished -> restore the HUD
                    self.repaint()  # type: ignore
            else:
                if self.pet.hatching:  # type: ignore
                    ht0 = getattr(self.pet, "_hatch_t", 3.0)  # type: ignore
                    done = self.pet.advance_hatch(0.1)  # type: ignore
                    # the hatch chirp marks the WOBBLE ACCELERATING (device-exact,
                    # GML 2026-07-14: the chirp lands as the egg's alarm quickens),
                    # i.e. interval 10 of the 3.0s rock -- was DVPet's t0.6 beat
                    if ht0 > 2.0 >= getattr(self.pet, "_hatch_t", 0.0):  # type: ignore
                        self.beep("hatch")  # type: ignore
                    if done:
                        p = self.pet  # type: ignore
                        self.flash(f"[b]{p.name}[/] chocou!")  # type: ignore
                # (the HeavyRain thunder roll -- the FLASH + the disposition-keyed
                # startle -- left with the weather system; BASIC VPET 2026-07-16)
                p = self.pet  # type: ignore
                # DVPet poopDance: a special-idle roll while the gauge is full --
                # tuipet fires the poop the moment the gauge fills, so the nervous
                # dance rolls while the need APPROACHES (>=80% of the interval)
                # canon rolls ONCE and picks UNIFORMLY among the eligible tells
                # (yawning/poopdance audit 2026-07-06; the old elif hard-favoured
                # the dance whenever both were due)
                if (not p.dead and p.stage != "Egg" and not p.asleep
                        and p.anim in ("idle", "walk")):
                    specials = []
                    if getattr(p, "_poop_t", 0) >= POOPDANCE_AT * p._poop_interval:
                        specials.append("poopdance")
                    if p.near_bedtime():
                        specials.append("yawn")      # the full yawning() stretch fx
                    if specials and random.randrange(40) == 0:
                        sc.start_fx(random.choice(specials))
                sc.advance(self.pet)  # type: ignore
                sc.paint(self.pet)  # type: ignore

    def on_tick(self) -> None:
            # the sim's proxy for "an animation is playing": the poop deferral
            # (canon startPoop state-machine block, restored 2026-07-19) holds
            # the squat through the whole VISIBLE fx, not just the anim ttl
            #
            # (the SUSPEND_GAP_S / _tick_wall gap tracking went with the offline
            # catch-up 2026-07-22: nothing measures lost wall-time any more,
            # because nothing is ever replayed from it.  One tick = one second
            # of pet life, and only while the main view is up.)
            if getattr(self, "pet", None) is not None:
                self.pet._fx_busy = getattr(getattr(self, "screen_w", None), "fx", None) is not None  # type: ignore
            if self.mode is not None:  # type: ignore
                # a sub-screen is open -> pause the life-sim (the canon menu
                # freeze), with NO exception.  The lobby's chat contexts used to
                # tick on (Joel 2026-07-13: "make the lobby tick, alarm and all"),
                # and the comment here also claimed the open road ticked -- it
                # never did: AdventurePanel goes through _open_mode like every
                # other panel, so the road froze with the rest.  Joel 2026-07-22,
                # on the audit finding the lobby was the ONLY live menu: "take it
                # off if lobby is the only one that does it."  One law now -- a
                # pet must not starve, sicken, age or die behind ANY menu.
                return
            prev = (self.pet.num, self.pet.stage)  # type: ignore
            poop0 = self.pet.poop  # type: ignore
            # an evolution must not swap the sprite UNDER a playing animation (the
            # clean-fx incident 2026-07-04: the pet transformed mid-sweep and the
            # evolve strobe played on the already-evolved form) -- hold the check
            # until the screen is quiet; the counters keep and it fires next tick
            self.pet.fx_hold = self.screen_w.fx is not None  # type: ignore
            self.pet.tick(1.0)  # type: ignore
            p = self.pet  # type: ignore
            if p.dead and not p.death_banked and not self._dying_fx:
                # STATE, not a was_dead tick edge (see the mode branch above):
                # any un-ceremonied death gets its dying beat -- including one
                # set between ticks (poison mushroom) or loaded at relaunch
                self.beep("death")            # type: ignore
                self.flash("")  # type: ignore
                self.screen_w.start_fx("dying")   # type: ignore
                self._dying_fx = True
                self._revive_hits = 0
            elif (p.num, p.stage) != prev:
                if prev[1] == "Egg":
                    self.beep("hatch")  # type: ignore
                    star = ("  [b]★ a NEW species for the album![/]"
                            if not persistence.album_has(p.num) else "")
                    self.flash(f"[b]{p.name}[/] chocou!{star}")  # type: ignore
                    # hatch has NO evolve dither -- the egg already shook; the Fresh just appears
                else:
                    # _evolve sounds INSIDE the strobe (fx snds beat 5), like DVPet evolveAnim.
                    # design call (polish 2026-07): an evolution landing mid-fx WAITS for
                    # the current animation instead of truncating it (death still overrides)
                    self.flash(self._evolve_msg(prev[0]))  # type: ignore
                    if self.screen_w.fx is None:  # type: ignore
                        self.screen_w.start_fx("evolve", old_num=prev[0])  # type: ignore
                    else:
                        self._pending_evolve = prev[0]
            elif p.poop > poop0:
                # DVPet playPoopSound keys the byte poop() RETURNS -- the SIZE of the
                # new pile (f==1 small, f>2 large, else normal) -- not the pile count
                # (poop-anim audit 2026-07-05: a small fourth pile barked largePoop)
                sz = (p.poop_sizes[-1] if getattr(p, "poop_sizes", None) else 2)
                poop_snd = "smallPoop" if sz == 1 else ("largePoop" if sz > 2 else "poop")
                if self.screen_w.fx is None:  # type: ignore
                    # DVPet poop(): squat/sway then the pile lands at t18 with its sound
                    self.screen_w.start_fx("poop", poop=poop0)  # type: ignore
                    self.screen_w.fx["snds"] = {18: poop_snd}  # type: ignore
                else:
                    self.beep(poop_snd, bell=False)  # type: ignore
            # AI Assistant rounds (checkAutoCare): play the visit, flash the quit notes
            ev = getattr(p, "assist_event", None)
            if ev and self.screen_w.fx is None:  # type: ignore
                p.assist_event = None
                act, piles, sizes = ev
                self.screen_w.start_fx("assist", pet=p, poop=piles,  # type: ignore
                                       icon="f:44" if act == "feed" else ("f:43" if act == "strength" else None))
                self.screen_w.fx["act"] = act  # type: ignore
                self.screen_w.fx["sizes"] = sizes  # type: ignore
                self.screen_w.fx["helper"] = p.assistant_num  # type: ignore
                if act in ("feed", "strength"):
                    # assistantFeed: the drop-off round is short; the REAL eat anim
                    # (with its own bite sounds / pace / grimace) chains after
                    self.screen_w.fx["steps"] = 12  # type: ignore
                    self.screen_w.fx["chain_eat"] = self.screen_w.fx["icon"]  # type: ignore
                    self.screen_w.fx["pet_ref"] = p  # type: ignore
            note = getattr(p, "assist_note", "")
            if note:
                self.flash(note)  # type: ignore
                p.assist_note = ""
            wn = getattr(p, "wake_note", "")
            if wn:
                # the morning tier used to land as nothing but a 1.6s pose
                # while the roll moved mood a whole tier (gameplay polish #11)
                self.flash(wn)  # type: ignore
                p.wake_note = ""
            # a lifetime-win gate crossed mid-battle: announce it back home
            note = getattr(p, "egg_unlock_note", "")
            if note:
                self.flash(note)  # type: ignore
                # a whole new raisable species earned: the champion fanfare, not
                # the same chirp as picking up an Oats (sweep 2026-07-14)
                self.beep("champion", bell=False)  # type: ignore
                p.egg_unlock_note = ""
            # birthday (setTimeToAge age-up): announce the day's verdict
            if p.birthday_note:
                self.flash(p.birthday_note)  # type: ignore
                self.beep("reward" if "Cupcake" in p.birthday_note or "Cookie" in p.birthday_note else "lose", bell=False)  # type: ignore
                p.birthday_note = ""
            # (the life-burn tell left with the lifespan clock -- DSprite
            # mortality 2026-07-22: there are no burns to announce)
            # tournament alarm (TournamentAlert): the alarmed cup's hour arrived --
            # onset ring, then the same attention bounce as the gift call
            if p.tourney_alert and not getattr(self, "_cup_alert_seen", False):
                self.beep("alarm")  # type: ignore
            self._cup_alert_seen = p.tourney_alert
            if p.tourney_alert and p.anim == "idle" and self.screen_w.fx is None:  # type: ignore
                p._set_anim("happy", 1.2)
            # gift call (DVPet GiftCall): onset chime, then the attention bounce
            # (poses 5/7, like DVPet attention(5,7)) until the present is claimed
            if p.gift and not getattr(self, "_gift_seen", False):
                self.beep("reward", bell=False)  # type: ignore
            self._gift_seen = bool(p.gift)
            if p.gift and p.anim == "idle" and self.screen_w.fx is None:  # type: ignore
                p._set_anim("happy", 1.2)
            # frailty gets its ONSET alarm (gameplay polish #9, 2026-07-22): the
            # one genuinely lethal care state was the only silent one.  Onset
            # only, no 90s re-nag -- unlike hunger there is no key that clears
            # it (mistakes are stage-scoped), so a standing nag would just be
            # torture; the HUD line below stays up for as long as it holds
            frail = p.is_frail()
            if frail and not getattr(self, "_frail_seen", False):
                self.alarm_pattern(3)          # type: ignore
            self._frail_seen = frail
            # care-need call (classic V-pet nag): alert on onset, then every ~90s
            # -- the ring COUNT carries the class by ear (#8: 1 routine / 2 mess
            # / 3 urgent), same alarm.wav throughout
            needs = p.needs_attention()
            if needs and not self._needs:  # type: ignore
                self.alarm_pattern(self._alarm_urgency(p))  # type: ignore
                self._nag_t = 0.0
            elif needs:
                self._nag_t = getattr(self, "_nag_t", 0.0) + 1.0
                if self._nag_t >= 90:
                    self._nag_t = 0.0
                    self.alarm_pattern(self._alarm_urgency(p))  # type: ignore
            self._needs = needs
            # the alarm's on-screen half: announce the active care need in the HUD box,
            # yielding to a fresh action flash and clearing once the need is met
            if self._flash_t > 0:  # type: ignore
                self._flash_t -= 1  # type: ignore
                self._showing_update = False
            elif needs or p.is_frail():   # frailty warns here too: it has no beep, and
                #  needs_care() alone never surfaced _need_message's frail branch
                self._hud(self._need_message(p))  # type: ignore
                self._showing_need = True
                self._showing_update = False
            elif p.tourney_alert:
                self._hud("ALERT — Tournament open! [b]U[/] to enter")  # type: ignore
                self._showing_need = True           # reuse the clear-on-resolve flag
                self._showing_update = False
            elif p.gift:
                self._hud(f"[b]{p.name}[/] has a present for you! ENTER to accept")  # type: ignore
                self._showing_need = True           # reuse the clear-on-resolve flag
                self._showing_update = False
            elif self._showing_need:
                self._hud("")  # type: ignore
                self._showing_need = False
            elif p.num == -1:
                # the egg wait finally says something (gameplay polish #20+#21,
                # 2026-07-22): 19 lit action keys all refused identically while
                # the only help pointer was a 4-second flash any nag could
                # overwrite.  The egg has no needs, so the idle slot is free to
                # hold the pointer for the whole wait.
                if not self._showing_eggwait:  # type: ignore
                    self._hud("o ovo choca sozinho — [b]?[/] ajuda · [b]E[/] guia de ovos")  # type: ignore
                    self._showing_eggwait = True
                self._showing_update = False
            elif self._showing_eggwait:
                self._hud("")  # type: ignore
                self._showing_eggwait = False
            elif 0 < p.poop < 3 and not p.asleep:
                # the sub-alarm tidy nudge (gameplay polish #7, 2026-07-22): the
                # care ALARM deliberately waits for 3 piles (~135 min), but a
                # lone pile sat visible and un-asked-about the whole way there
                # -- "is this a problem or not?".  A quiet idle line answers:
                # yes, and C clears it.  No beep -- the 3-pile alarm keeps its
                # escalation role.
                if not self._showing_tidy:  # type: ignore
                    self._hud("sujeira no chão — [b]C[/] para limpar")  # type: ignore
                    self._showing_tidy = True
                self._showing_update = False
            elif self._showing_tidy:
                self._hud("")  # type: ignore
                self._showing_tidy = False
            elif self._armed_field(p):  # type: ignore
                # a standing choice must stay visible (the Divergence page law:
                # "the door must be visible to be a choice") -- an armed steer
                # set hours ago otherwise fired with zero warning outside the
                # DNA screen (gameplay polish #14, 2026-07-22).  Idle-only:
                # every need, alert and gift outranks it.
                if not self._showing_armed:  # type: ignore
                    self._hud(f"◆ DNA armado — a próxima evolução segue o "  # type: ignore
                              f"caminho {data.pretty_field(self._armed_field(p))} ([b]X[/])")  # type: ignore
                    self._showing_armed = True
                self._showing_update = False
            elif self._showing_armed:
                self._hud("")  # type: ignore
                self._showing_armed = False
            elif self._update_msg and not self._showing_update:  # type: ignore
                self._hud(self._update_msg)     # type: ignore
                self._showing_update = True
            if self.screen_w.fx is None:   # type: ignore
                self.repaint()  # type: ignore

