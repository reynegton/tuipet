from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

import tuipet.ui.screens.feedscreen as feedscreen
import tuipet.ui.screens.disciplinescreen as disciplinescreen

import tuipet.data.loaders.data as data
import tuipet.core.training as training
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
from tuipet.core.pet import Pet
import tuipet.ui.screens.lobbyscreen as lobbyscreen
class CareActionsMixin:
    def action_sleep(self) -> None:
            self._do(self.pet.toggle_lights())  # type: ignore

    def action_assist(self) -> None:
            import tuipet.ui.screens.assistscreen as assistscreen
            self._open_mode(assistscreen.AssistPanel(self.pet), self._after_assist)  # type: ignore

    def _after_assist(self, msg: Optional[Any]=None) -> None:
            if msg:
                self.flash(msg)  # type: ignore
            self.repaint()  # type: ignore

    def action_feed(self) -> None:
            if self.screen_w.fx is not None:        # type: ignore
                return
            reason = self.pet.can_feed()            # type: ignore
            if reason:
                self._do(reason); return  # type: ignore
            self._open_mode(feedscreen.FeedPanel(self.pet), self._after_feed)  # type: ignore

    def _after_feed(self, result: Any) -> None:
            # result: ("fed"|"full"|"refused", food, msg); None on cancel.  A refusal
            # plays no food fx -- the refuse pose (State.Refusing) is already on the pet
            if not result:
                self.repaint(); return  # type: ignore
            outcome, food, msg = result
            icon = food.get("key", "f:0")               # the food's REAL icon rides the eat fx
            # eat(): the wolf-down modifier is decided BEFORE the meal (a starving
            # pet that just ate has hunger>0 -- reading it here was always False)
            starving = getattr(self.pet, "_last_meal_starving", False)  # type: ignore
            if outcome == "fed" and self.pet.anim == "eat":  # type: ignore
                self.screen_w.start_fx("eat", icon, pet=self.pet, starving=starving)   # type: ignore
            elif outcome == "healed":
                # the pill is EATEN (decompile EATING state): the same eat fx as
                # meat, on the ripped pill bite strip (pill-anim fix 2026-07-18)
                self.screen_w.start_fx("eat", icon, pet=self.pet)  # type: ignore
            elif outcome == "full":
                self.screen_w.start_fx("spit", icon)  # type: ignore
            self._do(msg)  # type: ignore

    def action_train(self) -> None:
            reason = self.pet.can_train()  # type: ignore
            if reason:
                self._do(reason); return  # type: ignore
            self._open_mode(training.TrainingPanel(self.pet), self._after_train)  # type: ignore

    def _after_train(self, msg: str) -> None:
            if msg:
                self.flash(msg)  # type: ignore
            # DVPet onExerciseFinish: success -> setPraise(true) -> the cheer(true) fx;
            # anything less -> State.Jeering -> jeer(true, _angry).  train_result left
            # the verdict in pet.anim (the sim is paused while the drill is open, so
            # it's still fresh here).  THREE GRADES, THREE TELLS (Joel 2026-07-25):
            # a PERFECT strike cheers, a SOLID hit grumbles the deserved 4/6 jeer,
            # a whiff takes the deeper 10/9 slump -- the boolean used to cheer the
            # middle grade like a perfect one.
            if self.pet.anim == "happy":  # type: ignore
                self.screen_w.start_fx("cheer")  # type: ignore
            elif self.pet.anim == "tantrum":  # type: ignore
                self.screen_w.start_fx("jeer")  # type: ignore
            elif self.pet.anim == "sad":  # type: ignore
                self.screen_w.start_fx("jeer", good=False)  # type: ignore
            elif self.pet.anim == "refuse":  # type: ignore
                # canon canExercise: _refused -> State.Refusing -- the head-shake plays
                # back on the LCD after onPreTrain dumps the menu (spit == refuse(); no icon)
                self.screen_w.start_fx("spit")  # type: ignore
            self.repaint()  # type: ignore

    def action_discipline(self) -> None:
            # praise & scold, RESTORED (canon restoration B, 2026-07-23).
            # The asleep poke follows the care-key law: wake + refuse this
            # press; youth outranks sleep like every other gate.
            import tuipet.ui.screens.disciplinescreen as disciplinescreen
            p = self.pet  # type: ignore
            if (g := p._guard(asleep_blocks=False)) is not None:
                self._do(g); return  # type: ignore
            if p.stage in ("Egg", "Fresh"):
                self._do("Muito novo para lições."); return  # type: ignore
            if p.asleep:
                self._do(p._disturbed()); return  # type: ignore
            self._open_mode(disciplinescreen.DisciplinePanel(p),  # type: ignore
                            self._after_discipline)

    def _after_discipline(self, result: Any) -> None:
            # the lesson's emotional beat rides the HOUSE screen, the same
            # grammar every other verdict uses (_after_cup / _after_battle /
            # the drill's cheer/jeer): a landed PRAISE cheers, a landed SCOLD
            # jeers, and a wrong-moment verb shows only its small pose --
            # nothing happened, so nothing plays (E1, Joel 2026-07-23:
            # "praise and scold should have happy and sad animations").
            msg, show = result if isinstance(result, tuple) else (result, None)
            if msg:
                self.flash(msg)  # type: ignore
            if show and self.screen_w.fx is None and not self.pet.dead:  # type: ignore
                self.screen_w.start_fx(show)  # type: ignore
            self.repaint()  # type: ignore

    def action_heal(self) -> None:
            """The H key: patch a battle injury -- a free care BUTTON like C
            clean (the bandage's final door, Joel 2026-07-26).  A cure plays
            the canon Bandaging show (items.csv i:80); a refusal just speaks."""
            if self.screen_w.fx is not None:        # type: ignore
                return
            msg = self.pet.heal_bandage()  # type: ignore
            if "curado" in str(msg):
                self.screen_w.start_fx("item", icon="i:80", script="Bandaging")  # type: ignore
            self._do(str(msg))  # type: ignore

    def action_clean(self) -> None:
            if self.screen_w.fx is not None:        # type: ignore
                return
            poop = self.pet.poop  # type: ignore
            sizes0 = list(self.pet.poop_sizes)      # type: ignore
            msg = self.pet.clean()  # type: ignore
            if self.pet.anim == "wash":  # type: ignore
                self.screen_w.start_fx("clean", poop=poop)  # type: ignore
                self.screen_w.fx["sizes"] = sizes0  # type: ignore
                self.beep("wash", bell=False)  # type: ignore
            self._do(msg)  # type: ignore


    def action_gift(self) -> None:
        if self.mode is not None or self.screen_w.fx is not None or not self.pet.gift:  # type: ignore
            return
        key = self.pet.gift  # type: ignore
        msg = self.pet.claim_gift()  # type: ignore
        if msg:
            self.screen_w.start_fx("gift", icon=key)   # type: ignore
            # the SURPRISE: hold the reveal until the present is opened at the
            # end of the amble (2026-07-24) -- a tease now, the contents then.
            self._pending_gift_reveal = msg
            self._do("A present! Let's see what it is…")  # type: ignore
