import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.i18n.translator import t
from tuipet.core.petbase import *

def age_days(pet):
    """The clone's age scale (v0.4.12 age_days): whole REAL days lived."""
    return int(pet.age_seconds // AGE_DAY)


def ideal_temp(pet):
    return data.load_requirements().get(pet.num, {}).get("ideal_temp", (40, 60))


def needs_care(pet):
    """The PHYSICAL half of the care call -- what the '!' rail icon shows:
    an awake, hatched pet that is starving, effort-empty, sick, HURT,
    filthy or exhausted, or a SLEEPER with the lights burning (canon
    lightsCall, the one call that fires asleep).  The discipline family
    (praise/scold/tantrum) is NOT here -- it wears the teach bulb
    instead, so the two icons carry separate meanings (Joel 2026-07-11:
    '!' and the bulb always showed as a pair, never separate).

    INJURY BELONGS HERE (training audit 2026-07-25).  The canon
    restoration said the wound "rides the same care-alarm cascade as
    sickness" and wired it into `_alarm_urgency` -- but that function
    only decides HOW LOUD an already-triggered alarm rings, and the
    trigger is this predicate, which never learned the second ailment.
    So a pet that was ONLY hurt rang nothing, raised no '!', and never
    reached the HUD line written to name its cure: the alert existed
    and could not fire.  Injury is a live, lethal-adjacent state with a
    free cure one key away; it calls for you like sickness does."""
    if pet.dead or pet.stage == "Egg":
        return False
    if pet.asleep:
        return bool(pet.lights)             # lightsCall: it wants the dark
    return (pet.hunger == 0 or pet.strength == 0 or pet.sick
            or pet.injured or pet.poop >= 3 or pet.energy <= 0)


def needs_attention(pet):
    """The FULL alarm predicate (HUD beep/nag + mood-lapse gate): physical
    needs OR an open discipline moment.  Split 2026-07-11: the '!' icon
    draws on needs_care() only; this union keeps the alarm and the
    mood-recovery block exactly as before (sleep-screens audit
    2026-07-06 semantics unchanged)."""
    # (the discipline half -- the teach bulb -- left with the discipline
    # system; BASIC VPET 2026-07-16)
    return pet.needs_care()


def near_bedtime(pet):
    """sleepNotNap: nod-off sits inside the real-sleep edge -- the yawning
    special idle's eligibility (and lights-out now means SLEEP).  Routed
    through the model-aware _near_bedtime so LINE pets (the wall-clock
    sleepers -- every hatch) roll their pre-bed yawn too; the pressure
    path inside is verbatim what stood here."""
    return pet._near_bedtime(
        SLEEP_NOT_NAP_MIN - pet.restless * SLEEP_NOT_NAP_RESTLESS)


def condition(pet):
    """CONDITION 0..3: how well-kept the pet is RIGHT NOW.  Care pays into
    SKILL, not just survival (2026-07-14): the training drills read this
    tier and widen their timing zones/windows for a well-kept pet -- a
    starved, exhausted one trains with a trembling paw.  The mean of
    three care gauges (mood left with its system), floored to a tier; a
    sick or injured pet never scores above 1."""
    score = (pet.hunger / 4.0
             + pet.strength / 4.0
             + max(0.0, pet.energy) / float(max(1, pet.max_energy))) / 3.0
    tier = max(0, min(3, int(score * 4)))
    return tier


def current_mood(pet):
    """DERIVED (no mood meter): the word keys off LIVE state.  Unhappy
    when unwell or unfed; HAPPY when perfectly kept -- condition tier 3
    with nothing else wrong, the same "bright" bar the walk poses use.
    The old derivation stopped at Neutral, so every Happy consumer (the
    good birthday, the battle power doubling, the happy idle, the grade's
    +1) was unreachable for the life of the app (MED audit 2026-07-19)."""
    w = pet.status_word()
    if w in ("sick", "starving", "needs cleaning"):
        return "Triste"
    if w == "ok" and pet.condition() == 3:
        return "Feliz"
    return "Neutro"


def is_fatigued(pet):
    """Always False: the fatigue system left (BASIC VPET 2026-07-16)."""
    return False


def is_injured(pet):
    """The second ailment, RESTORED (canon restoration 2026-07-23 --
    the 2026-07-16 strip took a feature the real hardware has).
    Battles wound (record_battle's adapted BattleInjury roll); the
    Bandage cures; sick and injured can coexist, two meds apart."""
    return pet.injured


def is_frail(pet):
    """The frailty WARNING (Joel 2026-07-13, after MetalGreymon died with
    8 unseen mistakes): an Ultimate/Mega carrying 3+ care mistakes is
    closing on the 5-slip elder death (_check_death_caps) -- surface it
    BEFORE it lands.  Warning only; the death rule is unchanged."""
    return pet.stage in ("Ultimate", "Mega") and pet.care_mistakes >= 3


def is_freezing(pet):
    """Always False: ambient temperature left with the weather system
    (BASIC VPET 2026-07-16).  Kept as an API pin -- screens poke it."""
    return False


def is_overheating(pet):
    """Always False (same removal as is_freezing)."""
    return False


def _is_failed_form(pet):
    """isFilthyEvol: the current form is a SpecialEvolution=Failed one."""
    r = data.load_requirements().get(pet.num, {})
    return (r.get("special") or "None") == "Falhou"


def status_word(pet):
    from tuipet.i18n.translator import t
    if pet.dead:
        return t("status_passed_away", "passed away")
    if pet.is_geriatric:
        return t("status_elderly", "elderly")
    if pet.asleep:
        return t("status_asleep", "asleep")
    if pet.sick:
        return t("status_sick", "sick")
    if pet.is_fatigued():
        return t("status_fatigued", "fatigued")
    if pet.is_injured():
        return t("status_injured", "injured")
    if pet.hunger == 0:
        return t("status_starving", "starving")
    if pet.poop >= 3:
        return t("status_needs_cleaning", "needs cleaning")
    # an empty tank OUTRANKS the softer tells (Joel 2026-07-23: "0 energy,
    # status is ok instead of sleepy") -- same tier the HUD nag uses
    if pet.energy <= 0:
        return t("status_exhausted", "exhausted")
    # sleepy keys on the pet's own bedtime window now (the night phase
    # left with the day/night system -- BASIC VPET 2026-07-17)
    if pet._in_sleep_window() and not pet.asleep and pet.energy < pet.max_energy // 2:
        return t("status_sleepy", "sleepy")
    # (the happy/unhappy words left with the MOOD system -- and the
    # meter itself is BURIED outright as of 2026-07-27 (Joel: "there
    # shoukdnt be a mood system at all... we have manners"); the
    # branches below could once only fire for a legacy save frozen
    # at a pre-slim extreme.  Pruned 2026-07-24, Joel "prune the vestigial
    # happy/unhappy branches"; a well-kept pet just reads "ok".)
    return t("status_ok", "ok")


