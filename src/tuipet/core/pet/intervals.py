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

def _hunger_interval(pet: Any) -> Any:
    # checkNeedDecay's glutton jitter: each lapse has a 1-in-LessHungerChance(9)
    # roll shifted by glutton -- in expectation a glutton drains ~11% faster,
    # a picky eater ~11% slower.  Applied as a steady coefficient.
    glut = 1.0 - (pet.glutton * (1.0 / LESS_HUNGER_CHANCE))
    return CALORIE_DECAY_SEC * (pet._phys().get("hunger_decay", 60) / REF_HUNGER_COEF) * glut


def _poop_interval(pet: Any) -> Any:
    """The species' own bowel cadence, with its RANGE compressed (Joel
    2026-07-25, option b -- see POOP_SPREAD_CAP).  The canon ratio
    `poop_limit / poop_lapse` is kept as the ordering, but read as a
    RATE relative to the modal species and then squeezed into
    1x..POOP_SPREAD_CAP, so no pet poops 64 times a game-day."""
    r = pet._phys()
    ratio = r.get("poop_limit", 64) / max(1, r.get("poop_lapse", 1))
    raw = REF_POOP_RATIO / max(1e-9, ratio)          # x faster than modal
    rate = 1.0 + (raw - 1.0) * (POOP_SPREAD_CAP - 1.0) \
        / (POOP_SPREAD_RAW - 1.0)                    # noqa: F405
    return POOP_INTERVAL_BASE / max(1.0, rate)


def _strength_interval(pet: Any) -> Any:
    return STRENGTH_DECAY_BASE * (pet._phys().get("strength_decay", 50) / REF_STRENGTH_COEF)


def _growth_period(pet: Any) -> Any:
    """The growth curve's total: egg + every stage through the current one
    (canon _growthPeriod; the longevity leg credits life lived past it).
    Mega's 9e9 STAGE_DURATION is the "never auto-evolves" sentinel, not a
    duration -- summing it graded every Mega 0 (gameplay audit
    2026-07-19); the curve ends at REACHING the final form."""
    order = ("Fresh", "InTraining", "Rookie", "Champion", "Ultimate", "Mega")
    total = float(pet.EGG_DURATION)
    for st in order:
        d = pet.STAGE_DURATION.get(st, 0)
        if d < 9e8:
            total += d
        if st == pet.stage:
            break
    return total


