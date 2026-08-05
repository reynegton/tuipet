from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

import tuipet.ui.screens.bugscreen as bugscreen
import tuipet.ui.screens.helpscreen as helpscreen
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.ui.screens.optionsscreen as optionsscreen
import tuipet.ui.screens.titlescreen as titlescreen

import tuipet.data.loaders.data as data
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
from tuipet.core.pet import Pet
import tuipet.ui.screens.lobbyscreen as lobbyscreen
class SystemActionsMixin:
    def action_new(self) -> None:
            import tuipet.ui.screens.eggselectscreen as eggselectscreen
            gen = self.pet.generation + 1
            self._open_mode(eggselectscreen.EggSelectPanel(self.pet),  # type: ignore
                            lambda et: self._hatch_new(et, gen))  # type: ignore

    def action_help(self) -> None:
            self._open_mode(helpscreen.HelpPanel(self.pet), lambda _=None: self.repaint())  # type: ignore

    def action_bug(self) -> None:
            self._open_mode(bugscreen.BugReportPanel(self.pet), self._after_bug)  # type: ignore

    def _after_bug(self, result: Optional[Any]=None) -> None:
            if isinstance(result, tuple) and result and result[0] == "bug":
                name = persistence.get_account()[0] or ""
                self.run_worker(self._send_bug(result[1], self._bug_meta(), name),  # type: ignore
                                name="bug", exclusive=False)
                self._hud("Sending your report\u2026")  # type: ignore
            self.repaint()  # type: ignore

    def action_quit(self) -> None:
            persistence.save(self.pet)
            self.exit()  # type: ignore

    def action_options(self) -> None:
            """The OPTIONS menu gathers the app-level switches (theme / sound /
            account / update / keys / new egg / erase) under one key -- g/m/n gave
            the action bar its breathing room back (Joel 2026-07-04)."""
            if self.mode is not None:  # type: ignore
                return
            self._open_mode(optionsscreen.OptionsPanel(  # type: ignore
                self.pet, lambda: self.sound, self._toggle_sound,  # type: ignore
                on_theme_change=self._restyle,  # type: ignore
                bindings=self.BINDINGS,  # type: ignore
                update_hint=lambda: getattr(self, "_update_msg", ""),
                verdict=self._verdict),  # type: ignore
                self._after_options)

    def _after_options(self, result: Any) -> None:
            self._restyle()                             # type: ignore
            if result and result[0] == "restart":
                # the update's restart offer: save, leave Textual cleanly, and
                # main() re-execs the NEW code once the terminal is restored
                self.autosave()  # type: ignore
                self._restart_after_exit = True
                self.exit()  # type: ignore
                return
            if result and result[0] == "new":
                self.action_new()
                return
            if result and result[0] == "account":
                self.run_worker(self._switch_account(result[1], result[2]),  # type: ignore
                                name="switch", exclusive=False)
                return
            if result and result[0] == "erase":
                self._stop_sync()                       # type: ignore
                persistence.erase_all()
                self.pet = Pet.new_egg()                # placeholder until the carousel picks
                # a fresh start IS a new game: without this flag the post-title flow
                # skipped the egg-select carousel and kept the placeholder egg
                # (Joel 2026-07-05: "automatically selected an egg for me??")
                self._new_game = True
                self._open_mode(titlescreen.TitlePanel(), self._after_title)  # type: ignore
                self.flash("Todos os dados apagados — um novo começo.")  # type: ignore
                return
            self.repaint()  # type: ignore

