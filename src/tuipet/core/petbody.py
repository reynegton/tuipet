"""The pet's BODY CLOCK (tier-5, 2026-07-17): the per-tick simulation --
hunger, filth, sleep, growth, recovery, mortality, the care effects and
the assistant's rounds.  Nothing here is player-initiated; it is what
time does to the creature."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import math  # noqa: F401
import random  # noqa: F401
from tuipet.i18n.translator import t  # noqa: F401

import tuipet.utils.backgrounds as backgrounds    # noqa: F401
import tuipet.data.loaders.data as data    # noqa: F401
import tuipet.core.egg as egg_mod    # noqa: F401
import tuipet.core.evolution as evolution    # noqa: F401
import tuipet.core.lines as lines_mod    # noqa: F401
import tuipet.core.shop as shop    # noqa: F401
import tuipet.utils.theme as theme    # noqa: F401
from tuipet.core.petbase import *    # noqa: F401,F403  (constants resolve HERE, per mixin)


import tuipet.core.pet.body.mind as mind
import tuipet.core.pet.body.autocare as autocare
import tuipet.core.pet.body.growth as growth
import tuipet.core.pet.body.digestion as digestion
import tuipet.core.pet.body.mortality as mortality
import tuipet.core.pet.body.sleep as sleep
class BodyMixin:
    """State contract: the Pet dataclass fields; composed into Pet."""

    # ---- per-tick simulation -------------------------------------------------
    def tick(self, dt: Any) -> None:
        """One game-minute of life.  Decomposed into ordered phases (audit
        2026-07); each phase's body is verbatim from the old monolith, and the
        early-return structure (egg / asleep / death) is explicit here."""
        self._tick_clock(dt)
        if self.dead:  # type: ignore
            return
        self._tick_growth(dt)
        if self.stage == "Egg":  # type: ignore
            self._tick_egg()
            return
        self._tick_recovery(dt)
        if self.dead:                # type: ignore
            return
        self._tick_auto_care(dt)     # the assistant serves awake AND asleep (never an egg)
        if self.asleep:  # type: ignore
            self._tick_asleep(dt)
            return
        self._tick_mood_discipline(dt)
        self._tick_hunger(dt)
        self._tick_body(dt)
        self._tick_sleep_pressure(dt)
        if self._tick_mortality(dt):
            return
        # the sick/filth guard moved INTO _special_idle (pose audit
        # 2026-07-25): it sat on the roll itself, so the two states that
        # actually make a pet Unhappy -- sick and filthy -- were the two
        # that could never reach the sulk.  It still gates the JOY family.
        if (self.anim in ("idle", "walk") and self.anim_ttl <= 0  # type: ignore
                and random.random() < 0.03 * dt):
            self._special_idle()
        self._maybe_evolve()  # type: ignore

    def _tick_clock(self, dt: Any) -> None:
        """The world clock: hour rollover (tournament alarm) + weather -- these
        run even over the grave."""
        hr0 = int((self.world_seconds % DAY_LENGTH) / DAY_LENGTH * 24)  # type: ignore
        self.world_seconds += dt  # type: ignore
        hr1 = int((self.world_seconds % DAY_LENGTH) / DAY_LENGTH * 24)  # type: ignore
        if hr1 != hr0 and not self.dead:  # type: ignore
            self.tourney_alert = False    # a ring only lasts its cup's hour
            if self.tourney_alarm >= 0:  # type: ignore
                import tuipet.core.tournament as _tourney
                _tourney.schedule(self)   # a day rollover re-rolls (and clears the alarm)
            if (self.tourney_alarm >= 0 and self.tourney_alarm in (self.tourney_schedule or [])  # type: ignore
                    and (self.tourney_schedule.index(self.tourney_alarm) == hr1)):  # type: ignore  # type: ignore
                # CurrentTime.setSeconds: on the hour of the alarmed cup's slot,
                # clear the alarm and raise TournamentAlert (the attention call)
                self.tourney_alarm = -1
                self.tourney_alert = True

    def _tick_growth(self, dt: Any) -> Any:
        return growth._tick_growth(self, dt)

    def _tick_egg(self) -> Any:
        return growth._tick_egg(self)

    def _tick_recovery(self, dt: Any) -> None:
        """Environment + the recovery lapses (they run asleep or awake)."""
        day = int(self.world_seconds // DAY_LENGTH)  # type: ignore
        if getattr(self, "_exercise_day", -1) != day:    # DVPet checkExerciseTime: daily reset
            self._exercise_day = day
            self.exercise_today = 0

    def _inc_mistake(self) -> Any:
        return mind._inc_mistake(self)

    def _tick_asleep(self, dt: Any) -> Any:
        return sleep._tick_asleep(self, dt)

    def _tick_mood_discipline(self, dt: Any) -> Any:
        return mind._tick_mood_discipline(self, dt)

    def _filth_effects(self, dt: Any) -> Any:
        return digestion._filth_effects(self, dt)

    def _tick_hunger(self, dt: Any) -> Any:
        return digestion._tick_hunger(self, dt)

    def _tick_body(self, dt: Any) -> None:
        """The body's slow clocks: pooping, effort decay, nutrition decay, the
        filth care-mistake, and filth/starvation sickness."""
        # pooping (DVPet poop(): relief mood bump, sheds weight, drops a sized pile)
        self._poop_t = getattr(self, "_poop_t", 0) + dt
        # (a sleeping pet held it above -- only the desperate 2x gauge goes at night)
        if self._poop_t >= self._poop_interval:  # type: ignore
            busy = self.anim not in ("idle", "walk") or getattr(self, "_fx_busy", False)  # type: ignore
            if busy:
                # canon startPoop: the anim STATE MACHINE blocks the squat --
                # the pet HOLDS it until the action ends (restored 2026-07-19,
                # Joel's report: "it poops during feeding... make sure nothing
                # can get glitchy").  The 07-15 audit had dropped this "by
                # architecture"; the app marks the fx window via _fx_busy so
                # the hold covers the whole visible animation.  Canon bills
                # the hold once: PostponePoopMoodChange -1.  The gauge keeps
                # accruing -- a long hold releases as the big backlog pile.
                if not getattr(self, "_poop_held", False):
                    self._poop_held = True
            else:
                self._poop_held = False
                self._poop_t -= self._poop_interval  # type: ignore
                backlog = self._poop_t >= self._poop_interval / 2  # type: ignore
                if backlog:                          # big backlog: bigger pile + extra shed,
                    self._poop_t = 0                 # gauge zeroed (DVPet poop())
                self._do_poop(backlog=backlog)
                self._set_anim("poop", 2.2)          # type: ignore
        # effort decays per species (DVPet calcStrengthDecayLapse): keep training or it slips
        if self.strength > 0:  # type: ignore
            self._str_t = getattr(self, "_str_t", 0.0) + dt
            if not self.asleep and self._str_t >= self._strength_interval:  # type: ignore
                self._str_t = 0.0
                self.strength -= 1  # type: ignore
                if self.strength == 0:  # type: ignore
                    self.mistake_day += 1        # type: ignore
        else:
            # an EMPTY gauge has nothing to decay: the timer idling upward
            # here meant a heal after a long-empty spell was undone ONE TICK
            # later -- and billed a fresh missed-day (gameplay audit
            # 2026-07-19).  A refill starts a whole fresh interval.
            self._str_t = 0.0
        # strengthCall (canon gap closed, audit 2026-07): an EMPTY effort gauge
        # left unattended 10 game-min is a care mistake + obedience -5
        # (strengthMistakePenalty), postponed after one like the other calls
        if self.strength == 0 and not self.asleep:  # type: ignore
            self._str_call_t = getattr(self, "_str_call_t", 0.0) + dt
            if self._str_call_t >= 600.0:                    # 10 real min to answer
                #   (the same deliberate response-window rule as the hunger call)
                self._str_call_t = -3600.0                   # AfterMistakeMinutesPostponed
                self._inc_mistake()
                self._set_obedience(self.obedience - 5)      # type: ignore
                # no scold window on neglect (canon; discipline audit 2026-07-06)
                # -- strength drains to 0 on its own species timer, so this one
                # opened "misbehaving!" windows for free on a loop
        else:
            self._str_call_t = 0.0
        # (the nutrition macro lapse left with the nutrition system;
        # BASIC VPET 2026-07-16)
        # Filth acting-up (LINES_SPEC §5): NO real device counts filth as a care
        # mistake (Pen20 says so explicitly — mistakes are unanswered call lights
        # only), so the DVPet poopCall mistake is retired.  Filth keeps its teeth
        # (sickness rolls + mood drain in _filth_effects); an awake pet left amid
        # the mess past the grace still ACTS UP (scold window), postponed after one.
        FILTH_LIMIT = 3                      # the visible "needs cleaning" level
        if self.poop >= FILTH_LIMIT:  # type: ignore
            if not self.asleep:              # type: ignore
                self._filth_t = getattr(self, "_filth_t", 0) + dt
                if self._filth_t >= 1800:    # uncleaned grace before it acts up
                    self._filth_t = -3600    # AfterMistakeMinutesPostponed grace after one
                    self._open_scold()       # type: ignore
        else:
            self._filth_t = 0                # cleaned / under the limit resets the call timer

    def _near_bedtime(self, n: Any) -> Any:
        return sleep._near_bedtime(self, n)

    def _in_sleep_window(self) -> Any:
        return sleep._in_sleep_window(self)

    def _tick_bedtime(self, dt: Any) -> Any:
        return sleep._tick_bedtime(self, dt)

    def _calc_to_nap(self) -> Any:
        return sleep._calc_to_nap(self)

    def _tick_sleep_pressure(self, dt: Any) -> Any:
        return sleep._tick_sleep_pressure(self, dt)

    def _check_death_caps(self) -> Any:
        return mortality._check_death_caps(self)

    def _tick_mortality(self, dt: Any) -> Any:
        return mortality._tick_mortality(self, dt)

    # (getEffectEnergyGain / the care-effect tick -- careEffect.csv's whole
    # runtime, whose only shipped effect was the Futon's sleep boost -- left
    # with the staple props: strict-DSprite items, 2026-07-17)

    def _add_filth(self, size: int) -> Any:
        return digestion._add_filth(self, size)

    def _start_poop(self) -> Any:
        return digestion._start_poop(self)

    # (_advance_bm cut, LOW audit 2026-07-19: the BM-lurch consumables left
    # with the DVPet item system; nothing live called it)

    def _die(self, cause: str="") -> Any:
        return mortality._die(self, cause)

    def _do_poop(self, backlog: bool=False) -> Any:
        return digestion._do_poop(self, backlog)

    def _sleep_inc(self) -> Any:
        return sleep._sleep_inc(self)

    def _fall_asleep(self) -> Any:
        return sleep._fall_asleep(self)

    def _wake(self) -> Any:
        return sleep._wake(self)

    def _disturbed(self) -> Any:
        return sleep._disturbed(self)

    def _special_idle(self) -> Any:
        return mind._special_idle(self)

    def _check_discipline_call(self) -> Any:
        return mind._check_discipline_call(self)

    def _tick_auto_care(self, dt: Any) -> Any:
        return autocare._tick_auto_care(self, dt)

    def _birthday(self) -> Any:
        return growth._birthday(self)

    def _check_gift_call(self, dt: Any) -> Any:
        return mind._check_gift_call(self, dt)

