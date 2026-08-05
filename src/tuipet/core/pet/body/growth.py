from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.core.petbase import *

def _tick_growth(pet: Any, dt: Any) -> None:
    """Aging + the ambient systems: X-decay, shop restock, toy interest,
    the gift call, the mood record / birthday, the anim clock."""
    # (the Temporary protoform decay left with the X slim)
    pet.age_seconds += dt
    pet.stage_seconds += dt
    # (the shop restock credits left with the rolled-slot shop; the
    # DSprite catalog is a fixed shelf -- BASIC VPET 2026-07-16)
    # setItemInterestLapse: toy boredom fades -1 per timer -- a sunny pet
    # (disposition +1) re-engages in 40 game-min, a sour one takes 80
    if pet.item_interest > 0:
        pet._interest_t = getattr(pet, "_interest_t", 0.0) + dt
        timer = (ITEM_INTEREST_LOW_TIMER if pet.disposition > 0
                 else ITEM_INTEREST_HIGH_TIMER if pet.disposition < 0 else ITEM_INTEREST_TIMER)
        if pet._interest_t >= timer:
            pet._interest_t = 0.0
            pet.item_interest -= 1
    pet._check_gift_call(dt)                   # checkGiftCall: a happy pet may find a present
    # checkMoodRecord: sample the mood tier every MoodRecordMin game-min
    if pet.stage != "Egg":
        pet._mood_rec_t = getattr(pet, "_mood_rec_t", 0.0) + dt
        if pet._mood_rec_t >= MOOD_RECORD_MIN:
            pet._mood_rec_t = 0.0
            m = pet.current_mood()
            pet.daily_mood[m] = pet.daily_mood.get(m, 0) + 1
        # setTimeToAge: every AgeUp (one game day of age) is a BIRTHDAY,
        # judged by the day's MAJOR mood and the missed-day tally
        day = int(pet.age_seconds // DAY_LENGTH)
        if day > pet.last_birthday:
            pet.last_birthday = day
            pet._birthday()
    if pet.anim_ttl > 0:
        pet.anim_ttl -= dt
        if pet.anim_ttl <= 0:
            pet.anim = "sleep" if pet.asleep else "idle"


def _tick_egg(pet: Any) -> None:
    """Egg stage: only the hatch trigger (the 3s crack runs at frame cadence
    via advance_hatch; a 1 Hz countdown here would skip the crack frames)."""
    if not pet.hatching and pet.stage_seconds >= pet.EGG_DURATION:
        pet.hatching = True
        pet._hatch_t = 3.0
        pet._set_anim("hatch", 3.0)


def _birthday(pet: Any) -> None:
    """setTimeToAge's age-up: a mostly-Happy, zero-slip day earns a GOOD
    birthday (+bonus, a Cupcake); a mostly-Unhappy day with slips
    is a BAD one (-bonus, a consolation Candy); anything else is
    normal (a Cookie).  getMajority: a TIE yields no major mood -> normal.
    The slate (missed-days + the mood record) wipes for the new day."""
    counts = pet.daily_mood
    best = max(counts.values()) if counts else 0
    tops = [k for k, v in counts.items() if v == best and best > 0]
    major = tops[0] if len(tops) == 1 else None
    if major == "Feliz" and pet.mistake_day <= MAX_MISTAKE_DAY_BONUS:
        pet.evol_bonus += 1
        pet.add_item("cupcake")            # a REAL bag treat (TUIPET catalog 2026-07-18)
        pet._set_anim("happy", 2.0)                     # Birthday_Good
        pet.birthday_note = f"A wonderful day! {pet.name} earned a Cupcake!"
    elif major == "Triste" and pet.mistake_day >= MIN_MISTAKE_DAY_DEC:
        # (the BonusLifeDec burn left with the lifespan clock --
        # DSprite mortality 2026-07-22; the bad day still costs bonus)
        if pet.evol_bonus > 0:
            pet.evol_bonus -= 1
        pet.add_item("candy")
        pet._set_anim("sad", 2.0)                       # Birthday_Bad
        pet.birthday_note = "A rough day… just a Candy."
    else:
        pet.add_item("cookie")
        pet._set_anim("happy", 1.5)                     # Birthday_Normal
        pet.birthday_note = f"{pet.name} is a day older — have a Cookie."
    pet.mistake_day = 0
    pet.daily_mood = {k: 0 for k in pet.daily_mood}


