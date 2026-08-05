from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import textwrap
import tuipet.utils.backgrounds as backgrounds
import tuipet.data.loaders.data as data
import tuipet.core.egg as egg_mod
import tuipet.utils.persistence as persistence
import tuipet.utils.theme as theme
from tuipet.core.arena import bar, hearts
from tuipet.core.petbase import DISOBEY_BELOW
from tuipet.i18n.translator import t

CARD_W = 26
DIV = "[dim]" + "─" * CARD_W + "[/]"

from .helpers import *

def _zone_display(name: str, avail: Any) -> Any:
    """A zone's display name shortened to `avail` visible cols: the full
    name when it fits, else its gate BOSS (zone names are "{Boss}'s
    {biome}", and the boss IS the destination), else a plain clip."""
    if len(name) <= avail:
        return name
    return name.split("'s ", 1)[0][:avail]


def _frontier_name(pet: Any, avail: Any) -> Any:
    """The frontier zone's display name (the stats column is 26 wide,
    zone names run to 32)."""
    import tuipet.core.adventure as adventure
    return _zone_display(adventure.ZONES[adventure.frontier(pet)]["name"], avail)


def _where(pet: Any) -> Any:
    """The @ line's PLACE, <=16 cols: on the road it's the current zone's
    BIOME, the home scene otherwise -- both read as a place the pet stands.

    Zone names are "{Boss}'s {biome}"; the @ line shows the biome half, NOT
    the boss (@-habitat fix 2026-07-24, Joel "does it display the correct
    habitat name while in adventure?").  The boss is the Quest line's
    OBJECTIVE -- clipping the @ to it made the road read "@WarGreymon", a
    monster's name where a place belongs, and stacked two bosses on adjacent
    rows.  The biome (<=13 cols) is the habitat, and matches the home scene
    the @ shows off the road."""
    if getattr(pet, "away", False):
        zone = getattr(pet, "away_where", "") or "?"
        return zone.split("'s ", 1)[-1][:16]        # the biome half, not the boss
    return backgrounds.name(pet.bg_pick
                            or backgrounds.scene_for_egg(pet.egg_type))[:16]


def adventure_line(pet: Any) -> Any:
    """The home card's quest readout -- LIVE from pet.adv_progress (zones
    conquered of the 26), plus the FRONTIER zone's name (Joel 2026-07-21:
    "show the frontier zone name on the card") -- the road the pet walks
    next.  8-col label + 18 content cols; '★ all cleared' at the end.
    Single source for the adventure readout (status-box liveness rule)."""
    import tuipet.core.adventure as adventure
    total = len(adventure.ZONES)
    prog = max(0, min(int(getattr(pet, "adv_progress", 0) or 0), total))
    if prog >= total:
        return f"{t('status_quest', 'Quest').ljust(8)}[{theme.POS}]★ {t('status_all_cleared', 'all {total} cleared').format(total=total)}[/]"
    if prog <= 0:
        return f"{t('status_quest', 'Quest').ljust(8)}[dim]▸ {_frontier_name(pet, 16)}[/]"
    count = f"{prog}/{total} "
    return f"{t('status_quest', 'Quest').ljust(8)}{count}[dim]▸ {_frontier_name(pet, 16 - len(count))}[/]"


def home_lines(pet: Any) -> Any:
    import tuipet.core.lines as _lines    # DMX level: exp vs canon thresholds
    T = theme
    word = pet.status_word()
    deco = care_deco(pet, word)
    age = age_compact(pet.age_seconds)
    xm = f" [b {T.ACCENT}]X[/]" if pet.x_antibody != "None" else ""
    lvl = _lines._pet_level(pet)
    return [
        f"[b]{pet.name[:22]}[/]{xm}",
        f"[dim]{pet.stage}{(' · ' + pet.attribute) if pet.attribute else ''}[/]",
        DIV,
        f"{t('status_hunger', 'Hunger').ljust(8)}{hearts(pet.hunger)}",
        f"{t('status_effort', 'Effort').ljust(8)}{hearts(pet.strength)}",
        f"{t('status_energy', 'Energy').ljust(8)}{bar(pet.energy_pct(), 12, T.ENERGY)}",
        DIV,
        # (the HP fragment was the retired classic battle's trained-HP --
        # home-card audit 2026-07-17.  The Va/Da/Vi Power ledger and the DMX
        # Level, once datacore-only, now ride the two battle rows below --
        # both were live progression the main card never showed, home-card
        # surfacing 2026-07-24 "evaluate what we can fit".)
        f"{t('status_weight', 'Weight').ljust(8)}{pet.weight}g · [{T.COIN}]{pet.bits}b[/]",
        # care mistakes decide the evolution road (every line's CM gates)
        # and 20 is lethal.  Stage-scoped: they reset on evolve.
        (f"{t('status_care', 'Care').ljust(8)}[{T.POS}]{t('status_care_spotless', 'spotless')}[/]" if pet.care_mistakes == 0 else
         f"{t('status_care', 'Care').ljust(8)}[{T.NEG if pet.care_mistakes >= 10 else T.CARE}]"
         f"✗{pet.care_mistakes} {t('status_care_this_stage', 'this stage')}[/]"),
        f"DP      [{T.ACCENT}]{'◆' * getattr(pet, 'dp', 0)}[/][dim]{'◇' * (4 - getattr(pet, 'dp', 0))}[/]",
        # battle progression, once datacore-only: wins/level/trophies on one
        # row, the Va/Da/Vi attribute powers on the next.  Level folds in free
        # (DMX 1-10, capped by stage); the powers colour by attribute --
        # Vaccine green, Data blue, Virus red -- and are uncapped, so a big
        # number is real, not a glitch (chips + wins both feed them).
        # LIFE/POS/NEG are the theme roles that deliver that trio (theme
        # audit 2026-07-28): the row shipped with D on ACCENT, and accent
        # IS the neg hex on mono and amber -- Data and Virus rendered as
        # literal twins there, near-twins on grey (both red-family).
        f"{t('status_battle', 'Battle').ljust(8)}{pet.wins}W/{pet.battles} [dim]Lv[/]{lvl} [{T.COIN}]★{pet.trophies}[/]",
        f"{t('status_power', 'Power').ljust(8)}[{T.LIFE}]V{pet.vaccine}[/] [{T.POS}]D{pet.data_power}[/] "
        f"[{T.NEG}]Vi{pet.virus}[/]",
        adventure_line(pet),
        # the @ line is WHERE THE MON STANDS (liveness law, Joel 2026-07-21
        # "shouldnt the @ say what zone the mon is in during adventure?"):
        # the run's zone while it's away on the road, the home scene otherwise
        f"@{_where(pet)} [dim]{age}[/]",
        # (the Life bar left as a DVPet relic -- DSprite mortality, Joel
        # 2026-07-22: death is the hazard roll, there is no meter to show;
        # the elder tell is the aged shuffle sprite)
        status_line(word, deco),
    ]


