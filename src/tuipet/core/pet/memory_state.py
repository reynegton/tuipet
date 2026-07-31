import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.i18n.translator import t
from tuipet.core.petbase import *

def save_from_death(pet):
    """PhysicalState.saveFromDeath: yanked back from the brink -- starving,
    a bonus point poorer, RevivalLifeInc of life restored -- and the DEATH
    EVOLUTION fires if a Death-special form will take the body (Devimon /
    Bakemon / Ponchomon / Dexmon...).  With none valid it lives on as-is.
    Returns the old num when a death evolution fired, else None."""
    pet.dead = False
    pet.death_banked = False       # the NEXT death owes a fresh ceremony
    pet.saved_from_death += 1
    pet.hunger = HUNGER_AFTER_SAVED
    pet.sick = False               # the clone's revival fix: a fresh
    #                                 revival must not come back sick
    pet._starve_t = 0.0                          # the 12h clock restarts
    pet.evol_bonus += BONUS_AFTER_SAVED
    # (the RevivalLifeInc runway left with the lifespan clock -- the
    # clone's revive touches no life math at all; DSprite mortality
    # 2026-07-22.  The rescued pet simply lives on under the same
    # hazard roll, starving and a bonus point poorer.)
    old = pet.num
    targets = evolution.death_targets(self)
    if targets:
        pet.evolve_to(targets[0])               # evol(dying=true): the dark rebirth
        # the dark rebirth is a special evolution like jogress: re-anchor
        lines_mod.adopt_line(self, prev=old)
    else:
        # no Death form takes it: it lives on -- the continuous death checks
        # need the fatal counters off the trigger line (a mechanical floor;
        # DVPet's checks are edge events so canon never faces this)
        pet.care_mistakes = min(pet.care_mistakes, 19)
        pet.injuries = min(pet.injuries, 19)
    pet._set_anim("happy", 2.0)                  # the rescue ends in a cheer
    return old if targets else None


def final_care_grade(pet):
    """careBonusOnReset: grade the ending life.  Runs at death AFTER the
    Memory etch (which spends the bonus); the result seeds the next
    generation's evol_bonus."""
    b = pet.evol_bonus
    b = b - pet.care_mistakes if pet.care_mistakes > 0 else b + 1
    m = pet.current_mood()
    if m == "Feliz":
        b += 1
    elif m != "Neutro":
        b -= 1
    # (the obedience legs left with the discipline system: the meter is
    # pinned at 0, so `< BONUS_DEC_OBEDIENCE` docked EVERY graded life
    # -1 while the +1 was unreachable -- a removed system must not bill
    # a live formula (MED audit 2026-07-19))
    if pet.battles and (pet.wins / pet.battles * 100.0) >= BONUS_INC_WIN_RATE:
        b += 1
    # longevity: whole days lived past the growth curve (negative if short).
    # int(x / D), not x // D: canon's Java long division truncates toward
    # ZERO, so a short life loses only its WHOLE missing days (memory
    # audit 2026-07-06 -- floor division over-penalized by one).  The day
    # is the MEMORIAL's day (86400s, "Lived N days"): the 1440 game-min
    # day paid +175..+295 for ANY natural life, swamping the card's +-1
    # fine structure (gameplay audit 2026-07-19)
    b += int((pet.age_seconds - pet._growth_period()) / 86400.0)
    st = BONUS_STAGE.get(pet.stage)
    if st:
        base, attr_bar, battle_bar = st
        b += base
        if pet.stage == "Champion" and not pet._is_failed_form():
            b += 1
        if pet.vaccine + pet.data_power + pet.virus >= attr_bar:
            b += 1
        if pet.battles > battle_bar:
            b += 1
    return max(0, b)


def make_memory(pet):
    """setNewMemory, the dying pet's side: with a care bonus in hand, etch
    Va/D/Vi = floor(power * bonus * 0.01) into the Memory payload; the
    bonus is spent.  Returns None with no bonus (DVPet onDie only enters
    UnlockInheritance when _bonus > 0).  (The chip's lifespan hour left
    with the lifespan clock -- DSprite mortality 2026-07-22.)"""
    if pet.evol_bonus <= 0:
        return None
    b = pet.evol_bonus
    mem = {"name": pet.name, "num": pet.num,
           "vaccine": int(pet.vaccine * b * MEMORY_ATTR_COEF),
           "data": int(pet.data_power * b * MEMORY_ATTR_COEF),
           "virus": int(pet.virus * b * MEMORY_ATTR_COEF)}
    pet.evol_bonus = 0
    return mem


