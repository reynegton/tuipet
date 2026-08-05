from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from .helpers import *
from .home_screen import *
from .egg_screen import *
from .shop_screen import *
from .combat_screen import *
from .menus_screen import *

class _SubView:
    """Painters read app.mode; this lends `app` out with the EMBEDDED panel
    as the mode, so a host screen can hand its card to the sub's painter
    (the cup's bouts ran with no visible HP: painter_for dispatches on the
    top-level mode only, and BattlePanel is never top-level)."""
    __slots__ = ("_app", "mode")

    def __init__(self, app: Any, mode: Any) -> None:
        self._app, self.mode = app, mode

    def __getattr__(self, k: Any) -> Any:
        return getattr(self._app, k)


def _registry() -> Any:
    """Panel class -> painter.  Built lazily: importing every screen at
    module import would be a cycle magnet."""
    from tuipet.ui.screens import (assistscreen, backgroundscreen, battlescreen, bugscreen,
                   deathscreen, datacorescreen, disciplinescreen, dnascreen,
                   eggguidescreen, eggselectscreen, feedscreen, helpscreen,
                   lobbyscreen, optionsscreen, raidscreen, shopscreen,
                   titlescreen, tournamentscreen)
    import tuipet.core.training as training_mod
    return (
        (titlescreen.TitlePanel, title),
        (disciplinescreen.DisciplinePanel, discipline),
        (eggselectscreen.EggSelectPanel, eggselect),
        (tournamentscreen.TournamentPanel, tournament),
        (training_mod.TrainingPanel, training),
        (battlescreen.BattlePanel, battle),
        (dnascreen.DNAPanel, dna),
        (backgroundscreen.BackgroundPanel, scenes),
        (feedscreen.FeedPanel, feed),
        (shopscreen.ShopPanel, shop),
        (eggguidescreen.EggGuidePanel, eggguide),
        (datacorescreen.datacorePanel, datacore),
        (raidscreen.RaidPanel, raid),
        (lobbyscreen.LobbyPanel, lobby),
        (helpscreen.HelpPanel, help_),
        (optionsscreen.OptionsPanel, options),
        (bugscreen.BugReportPanel, bug),
        (deathscreen.DeathPanel, death),
        (assistscreen.AssistPanel, assist),
    )


def painter_for(mode: Any) -> Any:
    """The painter for a mode instance, or None (home screen -> vitals).

    SUB CHAINS RESOLVE FIRST (modularize 2026-07-22, Joel: "why are
    adventure battles and cup battles different?? the status box in cup
    shows so much more"): the cup used to hand its card to its embedded
    BattlePanel by itself while every OTHER host (the road's wilds, the
    town cup two layers deep, the raid volley) fell through to generic
    vitals -- same fight, different card.  The dispatcher now walks
    mode.sub recursively and lends the card to the DEEPEST registered
    panel, so one battle painter serves every fight wherever it runs.
    Resolution happens per paint, so a sub opening/closing re-routes on
    the next frame."""
    if mode is None:
        return None
    sub = getattr(mode, "sub", None)
    if sub is not None:
        subfn = painter_for(sub)
        if subfn is not None:
            return lambda app: subfn(_SubView(app, sub))
    for cls, fn in _registry():
        if isinstance(mode, cls):
            return fn
    return None


