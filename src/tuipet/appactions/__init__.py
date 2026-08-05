from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import tuipet.ui.screens.albumscreen as albumscreen
import tuipet.ui.screens.assistscreen as assistscreen
import tuipet.ui.screens.backgroundscreen as backgroundscreen
import tuipet.ui.screens.bugscreen as bugscreen
import tuipet.data.loaders.data as data
import tuipet.ui.screens.deathscreen as deathscreen
import tuipet.ui.screens.datacorescreen as datacorescreen
import tuipet.ui.screens.dnascreen as dnascreen
import tuipet.core.egg as egg_mod
import tuipet.ui.screens.eggguidescreen as eggguidescreen
import tuipet.ui.screens.eggselectscreen as eggselectscreen
import tuipet.ui.screens.feedscreen as feedscreen
import tuipet.ui.screens.hallscreen as hallscreen
import tuipet.core.rival as rival
import tuipet.ui.screens.helpscreen as helpscreen
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.network.net as net
import tuipet.utils.persistence as persistence
import tuipet.ui.screens.shopscreen as shopscreen
import tuipet.ui.components.statusbox as statusbox
import tuipet.utils.theme as theme
import tuipet.ui.screens.titlescreen as titlescreen
from tuipet.i18n.translator import t
import tuipet.core.tournament as tournament
import tuipet.ui.screens.tournamentscreen as tournamentscreen
import tuipet.core.training as training
import tuipet.ui.screens.optionsscreen as optionsscreen
from tuipet.appboot import _lobby_uri
from tuipet.core.pet import Pet

from .care_actions import CareActionsMixin
from .nav_actions import NavActionsMixin
from .system_actions import SystemActionsMixin

class ActionsMixin(CareActionsMixin, NavActionsMixin, SystemActionsMixin):
    def _do(self, result: Any) -> None:
        self.flash(result)  # type: ignore
        self.repaint()  # type: ignore
