from __future__ import annotations
import tuipet.data.loaders.data as data
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
from tuipet.app import _hud_fits, _hud_plain, _hud_esc, HUD_W, HUD_GAP, HUD_STEP, HUD_HOLD
from rich.cells import set_cell_size
import tuipet.utils.theme as theme

class HudMixin:
    def _hud(self, markup):
            """Single entry point for the message box.  Any message wider than the box
            is marquee-scrolled (see _hud_marquee) so it is never clipped; messages that
            fit render as-is with their Rich markup.  Re-sending the SAME text is a
            no-op: on_tick re-asserts persistent messages every second, and resetting
            the hold each time froze the marquee on its first window (audit 2026-07)."""
            if markup == getattr(self, "_hud_text", None):
                return
            self._hud_text = markup
            if _hud_fits(markup):
                self._hud_scroll = None
                self.msg_w.update(markup)
            else:
                self._hud_scroll = _hud_plain(markup)   # scroll plain text (overflow msgs carry no markup)
                self._hud_off = 0
                self._hud_hold = HUD_HOLD
                self._hud_tick = 0
                self.msg_w.update(_hud_esc(set_cell_size(self._hud_scroll, HUD_W)))

    def _hud_marquee(self):
            """Advance the message marquee one step.  Called from the 10 Hz frame clock;
            a no-op unless the current message overflows the box."""
            if self._hud_scroll is None:
                return
            self._hud_tick = (self._hud_tick + 1) % HUD_STEP
            if self._hud_tick:
                return                                  # throttle: scroll once per HUD_STEP frames
            if self._hud_hold > 0:
                self._hud_hold -= 1
                return                                  # pause on the head (and at each wrap)
            loop = self._hud_scroll + HUD_GAP
            # the window is cropped in CELLS (see _hud_fits) -- a char slice with a
            # wide glyph inside would spill the box and wrap-clip the tail
            self.msg_w.update(_hud_esc(set_cell_size(
                (loop + loop)[self._hud_off:self._hud_off + HUD_W], HUD_W)))
            self._hud_off += 1
            if self._hud_off >= len(loop):
                self._hud_off = 0
                self._hud_hold = HUD_HOLD               # hold again when it loops back to the head

    def flash(self, text):
            self._hud(text)
            self._flash_t = self.FLASH_HOLD

    def _evolve_msg(self, old_num):
            """'Koromon evoluiu para Agumon (Rookie)!' -- old name -> NEW NAME, stage
            in parentheses.  The old form ('X! evolved to InTraining!') read as if
            the stage were the pet's NAME (Joel, 2026-07-04: 'the babys name is
            intraining????'), because the species name never appeared."""
            _, by = data.load_sprites()
            old = by.get(old_num, {}).get("name") or "It"
            msg = f"[b]{old}[/] evoluiu para [b]{self.pet.name}[/] ({self.pet.stage})!"
            # genuine FIRSTS get named (sweep 2026-07-14): a first-ever Mega and a
            # first-ever species read no bigger than a baby's first bump before.
            # Both checks race nothing: the progress stamps trail on autosave and
            # album_add fires inside save(), so at THIS tick both still say "new".
            extra = []
            if self.pet.stage in data.STAGE_ORDER:
                if data.STAGE_ORDER.index(self.pet.stage) > \
                        persistence.get_progress().get("max_stage", 0):
                    extra.append(f"seu primeiro {self.pet.stage} da história")
            if not persistence.album_has(self.pet.num):
                extra.append("uma espécie NOVA para o álbum")
            if extra:
                msg += f"  [b]★ {' · '.join(extra)}![/]"
            return msg

    def _armed_field(self, p):
            """The strict-max Field whose charge has ARMED a divergence, or None
            -- the HUD's wrapper over evolution.divergence_target (cheap: the
            corpus tables behind it are all lru_cached loads)."""
            import tuipet.core.evolution as evolution
            return p.highest_dna() if evolution.divergence_target(p) is not None else None

    def _need_message(self, p):
            """HUD announcement for the pet's most urgent unmet care need (or '')."""
            name = p.name or "Your pet"
            if p.asleep and p.lights:               # lightsCall: the one asleep call
                msg = f"{name} está tentando dormir — apague as luzes! ([b]O[/])"
            # every call names its key (gameplay polish #19, 2026-07-22): lights
            # always said (S) while hungry/sick/cleaning -- the three commonest
            # calls -- left a new player hunting the 19-key bar mid-alarm
            # the pill is the FEED menu's second row -- free and infinite (the
            # canon meat/pill picker), NOT a bag item; the v0.5.169 hint sent a
            # panicked player to the bag (Joel caught it 2026-07-22)
            elif p.sick:          msg = f"{name} está doente! ([b]F[/] — dê a pílula)"
            # ...and the injury cure is the H KEY (2026-07-26 final ruling:
            # "remove bandage as an item alltogether and just add an h heal
            # hotkey") -- name the door that actually cures, the v0.5.169/178
            # lesson these lines keep re-learning.
            elif p.is_injured():  msg = f"{name} está machucado! ([b]H[/] — cure-o)"
            elif p.hunger == 0:   msg = f"{name} está com fome! ([b]F[/])"
            elif p.strength == 0: msg = f"{name} está sem energia — treine-o! ([b]T[/])"
            elif p.poop >= 3:     msg = f"{name} precisa ser limpo! ([b]C[/])"
            # ...and never nag a SLEEPER to rest (bug report 2026-07-26,
            # v0.5.280: "still getting exhausted! (S — rest) even when mon is
            # sleeping after exhaustion") -- this is the one call whose cure
            # IS the state the pet is already in; the doze is the rest
            elif p.energy <= 0 and not p.asleep:
                msg = f"{name} está exausto! ([b]O[/] — descanse)"
            elif p.discipline_call:
                msg = f"{name} está desobediente! ([b]P[/] — repreenda-o)"
            elif p.is_frail():
                left = max(0, 5 - p.care_mistakes)
                msg = (f"{name} está ficando frágil — "
                       + (f"mais {left} erro{'s' if left != 1 else ''} pode{'m' if left != 1 else ''} ser fatal!"
                          if left else "trate com perfeição!"))
            else:                 return ""
            return f"[{theme.NEG}]\u26a0 {msg}[/]"

