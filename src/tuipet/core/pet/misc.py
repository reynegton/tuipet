from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
import tuipet.utils.backgrounds as backgrounds
from tuipet.i18n.translator import t
from tuipet.core.petbase import *

def background(pet: Any, file: Optional[Any]=None) -> Any:
    """The home scene frame (or None).  The scene is WIRED TO THE EGG the
    pet hatched from and stands for its whole life -- the real device's
    per-version backgrounds, worn as the DSprite rebuild's rip set
    (habitats left; BASIC VPET 2026-07-16).  file overrides the sheet
    entirely (BackgroundAnim checkBack's special rooms: the
    tournament/PvP/raid arena).  One look per scene: the day-phase frame
    pick and the star-twinkle/ember night art left with the day/night
    system (BASIC VPET 2026-07-17)."""
    if file is not None:
        key = file
    else:
        # the egg decides the default; the E picker may override it
        # (Joel 2026-07-17: "add the e action back to change backgrounds")
        key = pet.bg_pick or backgrounds.scene_for_egg(pet.egg_type)
    frames = data.load_backgrounds().get(key)
    return frames[0] if frames else None


def pick_background(pet: Any, key: str) -> Any:
    """The E picker's commit: '' returns the scene to the egg's own."""
    pet.bg_pick = key
    if not key:
        return "De volta à cena do próprio ovo."
    return f"{backgrounds.name(key)} it is."


def _guard(pet: Any, asleep_blocks: bool=True) -> Any:
    """The shared action gate: dead / still-an-egg / asleep (a sleeping pet
    is DISTURBED, not served).  Returns the refusal string or None."""
    if pet.dead:
        return t("guard_dead", "Descansando agora — aperte N para um novo ovo.")
    if pet.stage == "Egg":
        return t("guard_egg", "Ainda é um ovo.")
    if asleep_blocks and pet.asleep:
        return pet._disturbed()
    return None


def _phys(pet: Any) -> Any:
    return data.load_requirements().get(pet.num, {})


def good_nutrition(pet: Any) -> Any:
    """Always False: the nutrition macros left (BASIC VPET 2026-07-16)."""
    return False


def _species_food(pet: Any) -> Any:
    r = data.load_requirements().get(pet.num, {})
    return (r.get("food_pref", "None"), r.get("food_aversion", "None"),
            r.get("food_intol", []))


def _set_anim(pet: Any, name: str, ttl: Any) -> None:
    pet.anim, pet.anim_ttl = name, ttl


def _poop_size(pet: Any) -> Any:
    """DVPet poop(): pile size from base weight (heavier mons drop bigger)."""
    bw = pet._base_weight()
    if bw >= POOP_INC_WEIGHT_FACTOR:
        return 3
    if bw <= POOP_INC_WEIGHT_FACTOR_SMALL:
        return 1
    return 2


