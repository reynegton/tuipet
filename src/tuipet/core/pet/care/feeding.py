import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.utils.sound as sound
from tuipet.core.petbase import FULL_HUNGER, _clamp, PILL_ENERGY_GAIN, PILL_WEIGHT_GAIN

def can_feed(pet):
    """Guard for opening the feed menu (mirrors feed()'s own gates)."""
    if (_g := pet._guard()) is not None:
        return _g
    return None


def feed(pet, food=None, assisted=False):
    """The DSprite feed (BASIC VPET 2026-07-16, cloned from v0.4.x): the
    F menu picks MEAT or PILL; the whole DVPet food catalog -- taste
    tiers, nutrition macros, calories, food evolutions -- left with it.
    Kept as the meat entry so the assistant and old callers still feed."""
    return pet.feed_meat()


def feed_meat(pet, assisted=False):
    """Meat: hunger +1, weight +1.  The source's refusal gates (canon
    gates 2026-07-18, decompile L11676): a sick pet, a pet beside its
    own filth, or a full belly gets the head-shake and NOTHING else --
    the DVPet overeatPenalty (weight+1, mistake+1, bowel shove) left
    with it.  The overeat COUNTER still ticks: the evolution corpus's
    OF gates read it, and a full-belly attempt IS the overfeed signal.
    Feeding a sleeper DISTURBS it first (refusals don't wake it).

    assisted=True is the AI ASSISTANT's serving: canon assistantFeed
    dishes the AI Food Pill (AutoCareHungerFoodID 44), which a SICK
    pet still accepts -- routing the visit through YOUR meat's sick
    refusal made the assistant bill every visit for a head-shake while
    the pet starved (assistant audit 2026-07-19)."""
    if (_g := pet._guard(asleep_blocks=False)) is not None:
        return _g
    if pet.sick and not assisted:
        pet._set_anim("refuse", 1.0)
        return f"{pet.name} está muito doente para comer — tente a pílula."
    if pet.poop:
        pet._set_anim("refuse", 1.0)
        return "Limpe primeiro!"
    if pet.hunger >= FULL_HUNGER:
        # THE OVERFEED PENALTY (D2, 2026-07-23): canon overeatPenalty
        # bills a stuffed pet -- weight piles on and it counts as a
        # care slip.  This branch was "penalty-free", which made
        # feeding the one care verb you could not get wrong; a vpet's
        # food has to be a decision.  The pet head-shakes FIRST, so
        # nothing is charged before you have been warned.  (The bag's
        # own foods refuse at a full belly and the assistant only
        # serves at hunger 0, so this is the single stuffing door.)
        pet.overeat += 1                    # the OF-gate signal (evolution)
        pet._set_weight(pet.weight + 1)
        pet.care_mistakes += 1
        pet._set_anim("refuse", 1.0)
        return f"{pet.name} está muito cheio! (✗ hiperalimentado)"
    # (a HIRED assistant is never blown off -- you paid for that
    # visit; today the empty-belly exemption already covers it,
    # since auto-care only serves at hunger 0)
    if not assisted and pet.manners_refusal("feed"):
        return f"{pet.name} torce o nariz!"
    if pet.asleep:
        pet._disturbed()
    pet._last_meal_starving = pet.hunger == 0          # eat(): wolfed down
    pet.hunger = _clamp(pet.hunger + 1, 0, FULL_HUNGER)
    pet._set_weight(pet.weight + 1)
    # every meal advances the bowel gauge (applyFood: bmGauge += bmLapseInc)
    pet._poop_t = getattr(pet, "_poop_t", 0) \
        + pet._poop_interval * pet._phys().get("poop_lapse", 1) \
        / max(1, pet._phys().get("poop_limit", 64))
    # (checkDirtyEating's filth-meal sickness risk left with the
    # sickness system (BASIC VPET 2026-07-17))
    pet._set_anim("eat", 1.4)
    return "Alimentado com carne."


def feed_pill(pet):
    """The pill (clone rules): cures the sickness, strength +1, energy
    +7, weight +5.  Refused when there is nothing to cure or top up.
    Healing a sleeper DISTURBS it first.  (The classic spell machine
    left 2026-07-17; the DSprite flag is pill-cured ONLY.)  The pill is
    EATEN -- the source's EATING action, same as meat (pill-anim fix
    2026-07-18; the DVPet bandage anim left with it)."""
    if (_g := pet._guard(asleep_blocks=False)) is not None:
        return _g
    if pet.poop:
        # the source refuses the pill beside filth too (canon gates
        # 2026-07-18, decompile L11677)
        pet._set_anim("refuse", 1.0)
        return "Limpe primeiro!"
    if not pet.sick \
            and pet.strength >= 4 and pet.energy >= pet.max_energy:
        pet._set_anim("refuse", 1.0)
        return f"{pet.name} doesn't need it."
    if pet.asleep:
        pet._disturbed()
    pet.sick = False
    pet.strength = _clamp(pet.strength + 1, 0, 4)
    pet._set_energy(pet.energy + PILL_ENERGY_GAIN)
    pet._set_weight(pet.weight + PILL_WEIGHT_GAIN)
    pet._last_meal_starving = False     # a tonic is never wolfed down
    pet._set_anim("eat", 1.4)
    return "Tomou a pílula."


