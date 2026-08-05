from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.core.petbase import *

def _inc_mistake(pet: Any) -> None:
    """PhysicalState.incMistake: EVERY care mistake stings the mood first --
    a Happy pet is knocked DOWN TO 100 (MistakeHappyMoodChange, absolute),
    anyone else loses 50 -- then the counters tick (care-mistake audit
    2026-07-05: the counters ticked silently)."""
    pet.care_mistakes += 1
    pet.mistake_day += 1                        # MistakeIncMissedDayChange


def _tick_mood_discipline(pet: Any, dt: Any) -> None:
    """The filth nag + sickness risk, and the childhood personality
    tracker.  (The mood lapse left with the mood system; the obedience
    lapse, refusal expiry, tantrum clock and praise/scold window aging
    left with the discipline system -- BASIC VPET 2026-07-16.  DVPet has
    NO passive energy decay -- energy only moves via activity and sleep.)"""
    pet._filth_effects(dt)
    # personalityTracker (taste/rank audit 2026-07-06): childhood care is
    # TALLIED through Fresh/InTraining/Rookie -- energy kept above 75% of
    # max builds restlessness, weight off Healthy builds gluttony (the
    # mood-tier disposition leg left with the mood system);
    # randOnChampion cashes the tally in at the Champion evolution
    pet._rank_t = getattr(pet, "_rank_t", 0.0) + dt
    if pet._rank_t >= 59:
        pet._rank_t = 0.0
        if pet.stage in ("Fresh", "InTraining", "Rookie"):
            if pet.energy >= PCHAMP_HI_ENERGY * pet.max_energy:
                pet.energy_rank += 1
            elif pet.energy <= PCHAMP_LO_ENERGY * pet.max_energy:
                pet.energy_rank -= 1
            wc = evolution.weight_category(pet.weight, pet._base_weight())
            if wc == "Over":
                pet.weight_rank += 1
            elif wc == "Under":
                pet.weight_rank -= 1


def _special_idle(pet: Any) -> None:
    """The special-idle families, canon shape (SpriteAnim's 1/1500 rolls;
    personality audit 2026-07-06): the visible TANTRUM while the
    discipline call stands (canon rolls it at 3x the family odds), then
    the personality mood idles -- gated like canon (rested, spirited,
    under-drilled, well) and keyed on the mood TIER: Happy bounces,
    Unhappy fumes, Neutral does nothing.  (The weathering family --
    nice-weather joy, the rain shake, the snow shiver -- left with the
    weather system; BASIC VPET 2026-07-16.)"""
    if getattr(pet, "away", False):
        return                                   # no home idles on the road
    m = pet.current_mood()
    # ("Depressed" was never a current_mood() word -- the derived tiers are
    # Happy/Neutral/Unhappy only, and the sticky depressed STATE never
    # feeds the word -- so the old two-word check carried a dead arm
    # (audit 2026-07-25))
    if m == "Triste":
        # THE SULK COMES FIRST, UNGATED (pose audit 2026-07-25, Joel:
        # "ive yet to see an angry pose to this day on anything. see a
        # lot of happy poses").  It carried three gates a fuming pet
        # can rarely pass at once: the roll's own sick/filth guard --
        # and sick and filthy ARE two of the three states that read
        # Unhappy, so those could never fume at all -- plus a rested
        # gate (a neglected pet is usually drained) and an
        # under-drilled one (effort <= 2, so anyone who trains never
        # saw it).  Measured before the fix: sick 0 sulks/day, filthy
        # 0/day, starving-but-trained 0/day.  A pet that feels bad
        # SHOWS it; the gates below stay on the JOY family, which is
        # what they were written for.
        # (it wears the SMOKE emote -- `unhappy`, the discouraged show,
        # Joel 2026-07-23/25; "angry" is the same pose pair but stays
        # the disturb grumble, emote-free)
        pet._set_anim("tantrum", 2.0)
        return
    # the personality idles: rested + spirited gates for the JOY family
    # (gameplay polish #10, 2026-07-22): a freshly-fed, well-trained pet
    # used to play NO ambient emote for its first ~50-100 min while a
    # neglected one danced -- good care made the mon look MORE inert.
    # Joy plays at any effort, but not while filthy, sick or spent.
    if pet.poop or pet.sick:
        return
    if pet.energy < pet.max_energy / 3 or pet.enthusiasm < 0:
        return
    if m == "Feliz":
        pet._set_anim(random.choice(("play", "happy")), 2.0)


def _check_discipline_call(pet: Any) -> None:
    """A NO-OP: the spontaneous tantrum left with the discipline system."""


def _check_gift_call(pet: Any, dt: Any) -> None:
    """PhysicalState.checkGiftCall + checkGift: every GiftChanceMin game-min,
    a grown, awake, HAPPY pet rolls nextInt(cap - obedience +
    (maxMood - mood) * 0.5 + 70) -- a 0 means it found you a present (the
    better cared-for the pet, the narrower the range).  The pet then calls
    for attention (GiftCall, poses 5/7) until the gift is claimed."""
    pet.gift_t += dt
    if pet.gift_t < GIFT_CHANCE_MIN:
        return
    pet.gift_t = 0.0
    # the Happy-tier gate and the mood term left with the mood system
    # (BASIC VPET 2026-07-16): a WELL pet (not unwell) can find a present,
    # and obedience alone narrows the roll
    if (pet.gift or pet.asleep or pet.stage in ("Egg", "Fresh", "InTraining")
            or pet.current_mood() == "Triste"
            or getattr(pet, "away", False)):   # checkGiftCall gates on _isHome:
        return                                  # presents are found AT HOME
    # a FESTIVAL pet is more generous: the roll narrows by the multiplier
    # so presents come more often, and they reach a tier higher (2026-07-24)
    import tuipet.core.tournament as tournament
    fest = tournament.holiday() is not None
    chance = int(OBEDIENCE_REFUSAL_CAP - pet.obedience + GIFT_CHANCE_FACTOR)
    if fest:
        chance = max(1, chance // GIFT_FESTIVAL_MULT)   # noqa: F405
    if chance > 0 and random.randrange(chance) == 0:
        pet.gift = pet._pick_gift(festival=fest)


