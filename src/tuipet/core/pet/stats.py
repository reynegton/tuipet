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

def stomach_capacity(pet: Any) -> Any:
    """Canon getStomachCapacity: the SPECIES stomach (monster.csv), shrunk
    linearly through old age toward MinStomachCapacity(7) -- an elder
    fills up on smaller meals (food audit 2026-07-15).  The shrink runs
    over the first GERIATRIC_REMAIN seconds PAST the elder line (age-based
    since the DSprite mortality port 2026-07-22)."""
    cap = data.load_requirements().get(pet.num, {}).get("stomach_capacity", 10)
    if pet.is_geriatric:
        diff = min(GERIATRIC_REMAIN,
                   max(0.0, pet.age_seconds - GERIATRIC_AGE_DAYS * AGE_DAY))
        cap = max(MIN_STOMACH_CAPACITY, cap - int(diff * GERIATRIC_STOMACH_COEF))
    return cap


def _base_weight(pet: Any) -> Any:
    return data.load_requirements().get(pet.num, {}).get("base_weight", 20)


def _set_weight(pet: Any, value: Any) -> None:
    """PhysicalState.setWeight (weight audit 2026-07-06): clamp to
    baseWeight +- round(baseWeight x WeightLimitMultiple 0.75); slamming
    into either wall fires weightLimitPenalty (mood -10, obedience -0 at
    difficulty 0, spirit -1); inside the band the floor is 1."""
    value = int(round(value))
    base = pet._base_weight()
    span = round(base * WEIGHT_LIMIT_MULTIPLE)
    if value < base - span:
        pet.weight = base - span
        pet._weight_limit_penalty()
    elif value > base + span:
        pet.weight = base + span
        pet._weight_limit_penalty()
    else:
        pet.weight = max(1, value)


def _weight_limit_penalty(pet: Any) -> None:
    """PhysicalState.weightLimitPenalty: hitting the body's hard wall."""
    pet._set_obedience(pet.obedience - WEIGHT_LIMIT_OBED_PENALTY)
    pet._set_enthusiasm(pet.enthusiasm - WEIGHT_LIMIT_ENTH_PENALTY)


def _set_calories(pet: Any, value: Any) -> None:
    """DVPet setCalories: the buffer clamps at +-CalorieLimit -- and an
    OVERFLOW while rising bumps the BM gauge (AboveMaxCaloriesBMGaugeChange:
    overeating hastens the poop; proportional to the species poop_limit
    like feed's own gauge line).  Canon's falling-underflow hunger-lapse
    push is absorbed by tuipet's crash-refill restructure (the refill IS
    the delay).  The per-pet calorieMax/MinMod metabolism rolls and the
    Over/Under CalorieLimitModWeight are all 0 at difficulty 0: data-dead."""
    value = int(round(value))
    if value > CALORIE_LIMIT and value > pet.calories:
        pet._poop_t = (getattr(pet, "_poop_t", 0.0)
                        + pet._poop_interval * ABOVE_MAX_CAL_BM
                        / max(1, pet._phys().get("poop_limit", 64)))
    pet.calories = _clamp(value, -CALORIE_LIMIT, CALORIE_LIMIT)


def _set_obedience(pet: Any, value: Any) -> None:
    """LIVE again (canon restoration B, 2026-07-23, Joel: "whatever
    is canon bring back"): the gauge clamps 0..100 and every canon
    write-site that spent the strip as an inert citation -- clean's
    reward, the lights mistake, the weight-limit penalty, the
    surrender effects, the stage seeds -- resumes paying.  What it
    does NOT touch: refusals (the soft-refusal calibration is a
    standing rule) and LINES_SPEC gates.

    SCALE = canon MAX_OBEDIENCE 150 (P3 ruling 2026-07-23, from the
    plan audit).  v0.5.206 clamped 0..100 while EVERY constant that
    writes here -- the clean reward, the lights slip, the surrender
    set (15), the seeds (Fresh 75 / InTraining 50 / Rookie 50-25-0)
    -- is calibrated against 150, so the low clamp quietly distorted
    all of them."""
    pet.obedience = _clamp(int(value), 0, MAX_OBEDIENCE)  # noqa: F405


def _set_enthusiasm(pet: Any, value: Any) -> None:
    """A NO-OP: the spirit meter left with the enthusiasm system (BASIC
    VPET 2026-07-16, converging on the clone sim).  The canon write-sites
    stay as inert citations and die with their own systems; the meter is
    pinned at 0."""


def _set_energy(pet: Any, value: Any) -> None:
    """DVPet setEnergy, canon order (mood re-audit 2026-07-06): a drop INTO
    the red bills mood AND obedience scaled by the depth (dec - newEnergy)
    and FATIGUES an uninjured pet -- being pushed past empty is the
    over-exertion mechanic, not a flat sting.  Then the perfect-conditions
    bounce may save the step, and the clamp runs last (BOTTOMING OUT at
    the floor burns MinEnergyLifePenalty of life per hit)."""
    raw = int(round(value))
    if raw < pet.energy and raw < 0:
        pet._set_obedience(pet.obedience - (NEGATIVE_ENERGY_OBEDIENCE_DEC - raw))
        # (the over-exertion fatigue left with the fatigue system; the
        # perfect-conditions bounce left with the day/night system)
    # (MinEnergyLifePenalty at the -maxEnergy floor left with the
    # lifespan clock -- DSprite mortality 2026-07-22; the mood and
    # obedience stings above are the whole toll now)
    pet.energy = _clamp(raw, -pet.max_energy, pet.max_energy)


def energy_pct(pet: Any) -> Any:
    return max(0, pet.energy) * 100 // pet.max_energy if pet.max_energy else 0


