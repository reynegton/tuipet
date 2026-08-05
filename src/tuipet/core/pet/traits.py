from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.i18n.translator import t
from tuipet.core.petbase import *

def _rand_personality_traits(pet: Any) -> Any:
    """PhysicalState.randPersonalityTraits: each trait rolls Random.nextInt(3) ->
    {0:-1, 1:0, 2:+1} (only assigned while still neutral) -- and SEEDS the
    matching tracker rank at +-42 so the Champion re-roll starts from the
    rolled temperament, not from zero (taste/rank audit 2026-07-06)."""
    def roll(cur: Any) -> Any:
        if cur != 0:
            return cur
        r = random.randint(0, 2)
        return -1 if r < 1 else (1 if r > 1 else 0)
    pet.restless = roll(pet.restless)
    pet.glutton = roll(pet.glutton)
    pet.disposition = roll(pet.disposition)
    pet.energy_rank = pet.restless * PCHAMP_RANK      # randPersonalityTraits seeds
    pet.weight_rank = pet.glutton * PCHAMP_RANK
    pet.mood_rank = pet.disposition * PCHAMP_RANK


def _rand_on_champion(pet: Any) -> None:
    """PhysicalState.randOnChampion: at the CHAMPION evolution the
    temperament is RE-ROLLED from the tracked childhood ranks -- a pup
    kept energetic turns restless, one kept fat turns gluttonous, one
    kept happy turns sunny (threshold +-42, no randomness)."""
    pet.restless = (1 if pet.energy_rank >= PCHAMP_RANK
                     else -1 if pet.energy_rank <= -PCHAMP_RANK else 0)
    pet.glutton = (1 if pet.weight_rank >= PCHAMP_RANK
                    else -1 if pet.weight_rank <= -PCHAMP_RANK else 0)
    pet.disposition = (1 if pet.mood_rank >= PCHAMP_RANK
                        else -1 if pet.mood_rank <= -PCHAMP_RANK else 0)


def _disposition(pet: Any) -> Any:
    return pet.disposition          # DVPet _disposition: fixed personality trait


def _glutton(pet: Any) -> Any:
    return pet.glutton


def _restless(pet: Any) -> Any:
    return pet.restless


def personality(pet: Any) -> Any:
    if pet.num == -1 or pet.stage == "Egg":
        return "Não chocado"
    trio = _PERSONALITY[(pet._disposition(), pet._glutton())]
    rst = pet._restless()
    return trio[0 if rst == 0 else (1 if rst == 1 else 2)]


def _personality_mood(pet: Any, e: Any) -> Any:
    """consumablePersonalityMoodChange: +-10 per personality tag the
    consumable shares/clashes with the pet (disposition/restless/glutton)."""
    total = 0
    for trait, key in ((pet.disposition, "t_disposition"),
                       (pet.restless, "t_restless"), (pet.glutton, "t_glutton")):
        fv = int(e.get(key, 0) or 0)
        if fv != 0:
            total += PERSONALITY_MOOD_MATCH if fv == trait else PERSONALITY_MOOD_UNMATCH
    return total


