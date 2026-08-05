from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.core.petbase import *

def _check_death_caps(pet: Any) -> Any:
    """The discrete mistake/injury caps + the Pen20 elder-frailty rule:
    ONE copy for both tick paths -- these gates were duplicated between the
    sleep tick and _tick_mortality and had to be edited in lockstep
    (refactor 2026-07-05).  True when the pet died."""
    if pet.care_mistakes >= 20:                           # MaxCareMistakes
        pet._die("negligência")
        return True
    # Pen20 (LINES_SPEC §5): at the last stages, 5 slips once the evolution
    # window is open = death -- an elder Perfect/Ultimate demands real care
    if (pet.stage in ("Ultimate", "Mega") and pet.care_mistakes >= 5
            and pet.stage_seconds >= pet.LATE_STAGE_WINDOW):
        pet._die("fragilidade")
        return True
    return False


def _tick_mortality(pet: Any, dt: Any) -> Any:
    """The DSprite mortality (ported back from the clone, Joel 2026-07-22:
    "we gotta do it how dsprite does. life bar must be a dvpet forgotten
    relic"): NO lifespan clock, no burns -- death is ONE per-minute hazard
    roll, d = mistakes bracket + sick whisper + age bracket (v0.4.12
    L440-454, tables verbatim).  A healthy pet with <5 mistakes under age
    15 CANNOT die by the roll.  The discrete nets stand beneath it as
    before: the 20-mistake cap, Pen20 elder frailty (LINES_SPEC §5
    contract) and the 12h starvation clock are tuipet's own, not clock
    machinery.  Returns True when the pet died this tick."""
    if pet._check_death_caps():
        return True
    if pet.hunger == 0 and not pet.asleep:              # awake-only, like hungerCall()
        pet._starve_t = getattr(pet, "_starve_t", 0.0) + dt
        # ⭐ THE UNIT LAW, FOURTH INSTANCE (care audit 2026-07-25) --
        # and the warning for it is twelve lines below this one.
        # `_starve_t` accumulates dt, which is GAME-MINUTES, so the old
        # `12 * 3600` asked for 43,200 of them: THIRTY GAME-DAYS of
        # unbroken starvation.  Measured, the clock reached 2,940 after
        # three game-days while the 20-mistake ladder was already at 13
        # -- so the starvation death could never fire, on a field round
        # 41 deliberately PERSISTED so quit-cycling couldn't dodge it.
        # 12 game-hours is the comment's own number on the body's own
        # clock, the same rescale FILTH_SICK_BOUND took ("12000
        # real-min -> /60 game scale"): hunger decays on this clock, so
        # what starving costs is counted on it too.
        if pet._starve_t >= STARVE_DEATH_MIN:            # noqa: F405
            pet._die("inanição"); return True
    elif pet.hunger > 0:
        pet._starve_t = 0.0
    # ⭐ THE UNIT LAW (audit 2026-07-23): dt is world-SECONDS and one
    # world-second IS one game-minute (SICK_POOP_P is "per minute" and
    # coded p*dt; awake 480 + sleep 960 == DAY_LENGTH 1440).  NEVER
    # divide dt by 60 to "get minutes" -- that is a 60x error, and it
    # is exactly the P0a bug: this guard decayed dt/60.0, so a 1440
    # game-min (1 game-day) vitamin took ~24 REAL HOURS of play to
    # expire and one 500b capsule disarmed the whole injury system.
    # Canon DURATION constants are device real-minutes and must be
    # SCALED (the /60 precedent at FILTH_SICK_BOUND), never copied.
    if getattr(pet, "vitamin_lapse", 0.0) > 0:
        pet.vitamin_lapse = max(0.0, pet.vitamin_lapse - dt)
    # canon injLapse: a wound heals on its own clock (P4 ruling
    # 2026-07-23).  Same unit law -- inj_length is game-minutes, so
    # it burns by dt.  The Bandage skips the wait; time closes it.
    if pet.injured and pet.inj_length > 0:
        pet.inj_length = max(0.0, pet.inj_length - dt)
        if pet.inj_length <= 0:
            pet.injured = False
    # THE DISCIPLINE FADE (D1, 2026-07-23): canon obedienceLapse --
    # manners drain while AWAKE on a disposition-shaded cadence, and
    # each fire ALSO bills the mess (ObedienceChangeFilthScale x
    # piles).  Never while asleep: canon's MinObedienceAsleep equals
    # MaxObedience, which makes the lapse unreachable in sleep, and
    # canon's MinObedienceAsleep equals MaxObedience, which makes the
    # lapse unreachable in sleep -- _tick_life DOES run for a
    # sleeper, so the awake test is explicit.  Cadence is scaled --
    # see OBEDIENCE_LAPSE_MIN.
    pet._obed_t = (getattr(pet, "_obed_t", 0.0) + dt) if not pet.asleep else 0.0
    _lapse = OBEDIENCE_LAPSE_MIN.get(pet._disposition(),      # noqa: F405
                                     OBEDIENCE_LAPSE_MIN[0])   # noqa: F405
    while pet._obed_t >= _lapse:
        pet._obed_t -= _lapse
        pet._set_obedience(pet.obedience + OBEDIENCE_LAPSE_DEC * -1   # noqa: F405
                            + OBEDIENCE_FILTH_SCALE * pet.poop)        # noqa: F405
    # THE TANTRUM (canon restoration B, 2026-07-23 -- adapted
    # checkDisciplineCall): an awake pet AT HOME acts up about once
    # per 5400 game-min (~90 REAL minutes of play -- the label used to
    # read "90 game-min", the P0b mislabel); SCOLD inside the window
    # pays obedience +25, IGNORING it past the window costs a care
    # mistake and -5 (canon: ignored calls cost).  Never on the road,
    # never asleep.
    if (not pet.asleep and not getattr(pet, "away", False)
            and pet.stage not in ("Egg", "Fresh")):
        if pet.discipline_call:
            if pet.world_seconds > getattr(pet, "scold_window", 0.0):
                pet.discipline_call = False
                pet.scold_window = 0.0
                # through the front door: the bare += here skipped the
                # mood sting + the birthday mistake_day tally every
                # other mistake pays (incMistake; audit 2026-07-25)
                pet._inc_mistake()
                pet._set_obedience(pet.obedience - 5)
        elif random.random() < dt / (60.0 * 90.0):
            pet.discipline_call = True
            pet._open_scold()
            pet._set_anim("angry", 2.0)      # the emote-free grumble
    # the DSprite sickness, overweight half (clone rules, 2026-07-17).
    # The FILTH half moved home to _filth_effects (live-play audit
    # 2026-07-25): its flat SICK_POOP_P stood in for the documented
    # chance x piles / bound x species-multiplier roll, leaving the
    # canon scaling and 232 species' PoopSickChanceBoundMultiplier
    # unread.
    if not pet.sick:
        p = 0.0
        bw = pet._base_weight()
        if bw > 0 and pet.weight > bw:
            p += int((pet.weight - bw) // (bw * 0.5)) * SICK_OVERWEIGHT_P
        if p > 0 and random.random() < p * dt:
            pet.sick = True
    # the hazard roll: first matching bracket each from mistakes and age,
    # plus the sick whisper -- summed, rolled once (clone shape: the
    # whisper folds INTO d, it is not a separate death)
    d = 0.0
    for thresh, rate in DEATH_MISTAKES:                   # noqa: F405
        if pet.care_mistakes >= thresh:
            d += rate
            break
    if pet.sick:
        d += DEATH_SICK_P
    if pet.injured:
        d += DEATH_INJ_P                              # noqa: F405  (canon restoration
        #                                               2026-07-23: an untreated wound
        #                                               whispers at sick's scale)
    for thresh, rate in DEATH_AGE:                        # noqa: F405
        if pet.age_days >= thresh:
            d += rate
            break
    if d > 0 and random.random() < d * dt:
        pet._die("old age" if pet.age_days >= GERIATRIC_AGE_DAYS  # noqa: F405
                  else "negligence" if pet.care_mistakes >= 5 else "sickness")
        return True
    return False


def _die(pet: Any, cause: str="") -> None:
    pet.dead = True
    pet.death_cause = cause or pet.death_cause   # first cause wins
    pet.asleep = False
    pet.pending_lights_out = False   # no debts on the departed (audit r2)
    pet.hatching = False
    pet._set_anim("idle", 0)


