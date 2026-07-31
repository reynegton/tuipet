import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.core.petbase import *

def _filth_effects(pet, dt):
    """checkFilthMoodDec + the filth sickness rolls (canon re-audit 2026-07):
    every FilthMoodDecMin the mess costs species filth_mood x piles; every
    game-min each pile is a sickness risk (chance x piles vs the bound x the
    species multiplier -- the 12000 real-min bound rides the /60 game scale,
    which lands within a hair of the old hand-rolled rate while gaining the
    per-pile scaling the flat roll lacked).
    Away, canon's countFilth() reads 0 (poopable gates on _isHome): the
    home mess can't sicken a pet out on the road (sweep 2026-07-06)."""
    if getattr(pet, "away", False):
        return
    if pet.poop <= 0:
        return
    fm = pet._phys().get("filth_mood", -1)
    if fm:
        pet._filth_mood_t = getattr(pet, "_filth_mood_t", 0.0) + dt
        if pet._filth_mood_t >= FILTH_MOOD_DEC_MIN:
            pet._filth_mood_t = 0.0
    # the sickness roll this docstring always promised (live-play audit
    # 2026-07-25: the wiring was lost -- FILTH_SICK_CHANCE/BOUND and 232
    # species' PoopSickChanceBoundMultiplier sat unread while
    # _tick_mortality rolled a flat SICK_POOP_P whatever the mess).
    # chance x piles vs bound x species multiplier, per game-min: one
    # pile is 3x gentler than the flat roll, a 4-pile sty is worse, and
    # the resistant species (mult 2.0) shrug at half the rate.  At the
    # 3-pile mess the old flat rate matched, they agree exactly.
    if not pet.sick:
        mult = pet._phys().get("poop_sick_mult", 1.0) or 1.0
        p = (FILTH_SICK_CHANCE * pet.poop) / (FILTH_SICK_BOUND * mult)  # noqa: F405
        if random.random() < p * dt:
            pet.sick = True


def _tick_hunger(pet, dt):
    """hunger: the DVPet calorie buffer drains each lapse; emptying it drops
    a hunger heart, then refills.  The care MISTAKE is the call light
    (LINES_SPEC §5, canon on all three devices): hunger empty and unanswered
    for 10 minutes = ONE mistake, then the call is postponed — it no longer
    repeats every calorie cycle while starving."""
    if pet.full_until and pet.world_seconds < pet.full_until:
        return                    # premium-meat satiety (DSprite item)
    # hungerCall: a single mistake per unanswered call, mirroring strengthCall
    if pet.hunger == 0 and not pet.asleep:
        pet._hunger_call_t = getattr(pet, "_hunger_call_t", 0.0) + dt
        # ⚖️ DELIBERATE, *not* a clock-unit slip (cadence audit 2026-07-14).
        # Canon gives you 10 GAME-min to answer the call -- and on the real
        # device, which runs in REAL time, that IS ten real minutes.  Under
        # tuipet's 60x compression the literal port would be TEN REAL
        # SECONDS to notice the alarm and feed, or take a PERMANENT care
        # mistake (20 = death; 5 kills an elder).  Unplayable in a terminal
        # you leave in the background.  So the CONTINUOUS pressures (mood
        # drain, filth, sickness rolls) run at the canon game-min cadence,
        # while the DISCRETE PUNISHMENTS keep a fair human response window.
        if pet._hunger_call_t >= 600.0:                 # 10 real min to answer
            pet._hunger_call_t = -3600.0                # AfterMistakeMinutesPostponed
            pet._inc_mistake()
            pet.mistake_day += 1  # + HungerDecAtZero MissedDayChange
            # (the MistakeHungerLifeDec burn left with the lifespan clock
            # -- DSprite mortality 2026-07-22: mistakes now raise the
            # hazard brackets instead of burning a bar)
            # hungerMistakePenalty: obedience +1 -- or -1 for a glutton.
            # NO scold window: canon opens those for refusals and the
            # discipline tantrum only -- neglect costs mistakes/obedience,
            # it never makes the pet "act up" (discipline audit 2026-07-06;
            # the invented window leaked -10 obedience per miss and fed
            # the refusal spiral)
            pet._set_obedience(pet.obedience
                                + (HUNGER_MISTAKE_OBED_GLUTTON if pet.glutton > 0
                                   else HUNGER_MISTAKE_OBED))
    elif pet.hunger > 0:
        pet._hunger_call_t = 0.0
    pet._cal_t = getattr(pet, "_cal_t", 0.0) + dt
    if pet._cal_t >= pet._hunger_interval:
        pet._cal_t = 0.0
        pet._set_calories(pet.calories + CALORIE_LAPSE_CHANGE
                           + (CALORIE_LAPSE_GERIATRIC_EXTRA if pet.is_geriatric else 0))
        if pet.calories <= -CALORIE_LIMIT:
            if pet.hunger > 0:
                pet.hunger -= 1
            if pet.hunger == 0:
                # starvation (setHunger below zero): the calorie crash sheds weight
                # every further lapse (StarvationCalorieChange -> ActivityWeightChange)
                pet._set_weight(pet.weight - STARVE_WEIGHT_DEC)
            pet.calories = CALORIE_LIMIT


def _add_filth(pet, size):
    """addFilth (poop/filth audit 2026-07-06): below the cap the pile takes
    the next slot; a FULL room UPGRADES the first pile smaller than the new
    mess instead of dropping it (canon's overflow rule -- the old cap
    silently discarded it).  Cap stays Joel's 4 (real-toy match; canon's
    array is 6 -- with its poopCall threshold at 7, provably dead)."""
    if pet.poop < POOP_MAX_PILES:
        pet.poop += 1
        pet.poop_sizes.append(size)
        return
    for i, s in enumerate(pet.poop_sizes):
        if s < size:
            pet.poop_sizes[i] = size
            break


def _start_poop(pet):
    """DVPet startPoop: drop a sized pile."""
    pet._add_filth(pet._poop_size())


def _do_poop(pet, backlog=False):
    if pet.auto_clean_until and pet.world_seconds < pet.auto_clean_until:
        pet.poop = 0             # the smart potty flushes it (DSprite item)
        pet.poop_sizes = []
        return
    """PhysicalState.poop: relief mood bump, weight shed, and a new sized pile
    added to the filth (capped at the _filth array length).  A big BACKLOG
    (gauge still >= bmMax/2 after the poop) makes the pile one size bigger --
    the only source of size-4 piles -- and sheds an extra half weight."""
    # ⭐ THE WEIGHT FLOOR LAW REACHES THE LAST SINK (2026-07-25).  Every
    # other drain floors at the species BASE -- training (v0.5.17),
    # battles (v0.5.204, "the one sink still grinding to a skeleton"),
    # the march -- and this one never did.  It did not show while a pile
    # arrived every 1.9 game-days; the moment poop went to four a day
    # the budget inverted: at base 40 that is -16g of pooping against
    # +3g of meals, so even a pet fed on the dot wasted to the hard
    # clamp in two game-days and wore the maximum condition penalty
    # (-0.10 hit chance) for its whole life.  A body that eats and
    # relieves itself in balance sits AT its base; only real starvation
    # takes it below, and that branch (the calorie crash) is
    # deliberately unfloored.
    base = pet._base_weight()
    wdec = min(int(base * POOP_WEIGHT_DEC_COEF), POOP_WEIGHT_LIMIT)
    pet._set_weight(max(base, pet.weight - wdec))
    size = pet._poop_size()
    if backlog:
        # ⭐ THE BACKLOG PILE STOPS AT THE BIGGEST ART THAT FITS (Joel
        # 2026-07-25: "fix ... size 4 too").  The filth slots are built
        # to Joel's layout law -- "4 poops == 16x16, and the mon NEVER
        # walks over them" -- and the arenafx table says so outright:
        # the extracted sizes 1-3 (7x7 / 8x7 / 8x8) "fit the slot
        # natively", size 4 is 10 wide against an 8-wide slot.  It was
        # reached ONLY here, and the renderer's safety then squashed it
        # with fit_w, which distorts a real rip into a shape no device
        # ever drew.  Widening the slot would break the 16x16 law, and
        # rescaling ripped art is off the table -- so the upgrade stops
        # at 3.  The size-4 rip stays in the data, unused, exactly as
        # arenafx already assumed it was.
        size = min(POOP_SIZE_FITTING_MAX, size + 1)   # noqa: F405
        pet._set_weight(max(base, pet.weight - math.ceil(wdec / 2)))
    pet._add_filth(size)                    # capped; a full room upgrades a smaller pile


