from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.core.petbase import *
from tuipet.i18n.translator import t

def _tick_asleep(pet: Any, dt: Any) -> None:
    """The sleep branch: lights neglect, deep-sleep regen, the awakeLapse
    clock with the restless jitter, asleep death checks, desperate poop."""
    # lightsCall (DVPet): sleeping with the room light ON is neglect.
    # AfterMistakeMinutesPostponed is -60, NOT a latch: the mistake REPEATS
    # every 120 lit minutes (a fully lit night is ~4 mistakes); the
    # obedience ding lands ONCE per night (_lightsOffMistake flag).
    if pet.lights:
        pet._lights_t = getattr(pet, "_lights_t", 0.0) + dt
        if pet._lights_t >= LIGHTS_MISTAKE_SEC:
            pet._lights_t = LIGHTS_MISTAKE_POSTPONE
            if not getattr(pet, "_lit_obed_hit", False):
                pet._lit_obed_hit = True
                pet._set_obedience(pet.obedience + LIGHTS_MISTAKE_OBED)
            pet._inc_mistake()
    # Pen20 DP: sleep restores jogress power -- 3 game-hours = a full meter
    if pet.dp < DP_MAX:
        pet._dp_t = getattr(pet, "_dp_t", 0.0) + dt
        if pet._dp_t >= DP_SLEEP_MIN:
            pet._dp_t -= DP_SLEEP_MIN
            pet.dp += 1
    # (the asleep enthusiasmLapse left with the spirit system;
    # BASIC VPET 2026-07-16)
    # sleepDecay/setAwakeLapse (canon re-audit 2026-07): the wake clock steps
    # by the species AwakeLapseInc; a LIT room stalls it half the time
    # (LightsOnAwakeLapseUnchangedChance -- lit rest is poor rest); the
    # MoreSleepChance jitter lets a mellow pet lie in and a restless one
    # skip ahead, its bonus routed through the ACCUMULATORS like canon
    # (the old code paid energy directly, misreading NapEnergyMin -- a
    # cadence -- as an amount).
    phys = pet._phys()
    awake_inc = phys.get("awake_inc", 1)

    def _inc_sleep_minutes(gain: Any) -> None:
        # incSleepMinutes: the meter fills by AwakeLapseInc; a crossing pays
        pet._sleep_min = getattr(pet, "_sleep_min", 0.0) + awake_inc * dt
        if pet._sleep_min >= SLEEP_MIN_TO_GAIN:
            pet._sleep_min -= SLEEP_MIN_TO_GAIN
            pet._set_energy(pet.energy + gain)

    def _nap_energy(mult: int=1) -> None:
        # checkNapEnergy: the nap's own accumulator pays NapEnergyGain (1)
        pet._nap_e = getattr(pet, "_nap_e", 0.0) + awake_inc * dt * mult
        if pet._nap_e >= NAP_ENERGY_INC:
            pet._nap_e -= NAP_ENERGY_INC
            pet._set_energy(pet.energy + 1)

    step = awake_inc * dt
    if pet.lights and random.randrange(100) < LIGHTS_ON_AWAKE_STALL:
        step = 0.0
    r = random.randrange(MORE_SLEEP_CHANCE) + pet.restless * AWAKE_RESTLESS_COEF
    bonus = False
    if r < 0:
        step = max(0.0, step - dt)
    elif r > MORE_SLEEP_CHANCE - 1:
        step += dt
        bonus = True
    if pet.nap:
        # canon: a nap PAYS DOWN bedtime pressure (sleepLapse -= inc) -- the
        # old '+=' inverted it -- and, held past ChangeNapToSleepMinutes
        # (+restless coef), the nap BECOMES the night: pressure clears, the
        # accumulator residue rolls into the sleep meter, nap=false
        pet.sleep_lapse = max(0.0, pet.sleep_lapse - awake_inc * dt)
        pet._nap_cycle = getattr(pet, "_nap_cycle", 0.0) + dt
        # a doze taken PAST EMPTY recovers at the drained cadence
        # (NegativeEnergyGain's spirit -- real sleep already doubles for
        # a drained pet; the recovery-doze rework, Joel 2026-07-23)
        _nap_energy(2 if bonus or pet.energy < 0 else 1)
        if (pet._nap_cycle >= CHANGE_NAP_TO_SLEEP + pet.restless * NAP_TO_SLEEP_RESTLESS
                and pet._in_sleep_window() is not False):   # a line pet's day-doze
            #                          never becomes the night; bedtime does that
            pet._sleep_min = (getattr(pet, "_sleep_min", 0.0)
                               + max(0.0, getattr(pet, "_nap_e", 0.0) - 1))
            pet._nap_cycle = pet._nap_e = 0.0
            pet.sleep_lapse = 0.0
            pet.nap = False
    else:
        _inc_sleep_minutes(NEGATIVE_ENERGY_GAIN if pet.energy < 0
                           else getattr(pet, "_sleep_energy_gain", 3))
        if bonus:
            _inc_sleep_minutes(BONUS_SLEEP_ENERGY)
    pet.awake_lapse += step
    iw = pet._in_sleep_window()
    if iw is not None and not pet.nap:
        if iw is False:                      # LINES_SPEC §5: 7:00 sharp, no jitter
            pet._wake()
    elif pet.awake_lapse >= pet.awake_limit:
        # the FUTON deepens the hold (item expansion 2026-07-26): a
        # futon-backed doze rests to the FULL tank, not half
        if pet.nap and not pet.lights and pet.energy < (
                pet.max_energy if getattr(pet, "futon_doze", False)
                else pet.max_energy // 2):
            # THE RECOVERY DOZE (Joel 2026-07-23: "nap system is fucked
            # up. 0 energy... naps after a few seconds, one bar fills,
            # wakes up... its a care mistake if im not babysitting"):
            # a drained pet's doze no longer ends on checkNap's fixed
            # hour still spent -- it HOLDS in the dark until half the
            # tank is back, then wakes rested enough to stand.  One
            # consolidated nap instead of a wake/drain churn the player
            # had to babysit.  Lights on still rouses it (toggle_lights),
            # and a lit room never holds the doze.
            pet.awake_lapse = pet.awake_limit
        else:
            pet._wake()                     # nap wakes take the nap roll inside
    # hungerDecay: asleep the stomach drains only ABOVE the floor
    # (SleepMinHungerDecay=3) -- one heart overnight, then it holds
    if pet.hunger > SLEEP_MIN_HUNGER_DECAY:
        pet._tick_hunger(dt)
    # canon runs these in bed too: the filth nag+risk, and
    # poopWaitMoodCheck -- the HELD gauge (only a sleeper holds it) nags
    # (the mood lapse / call drain / depression left with the mood system)
    pet._filth_effects(dt)
    if pet._poop_t >= pet._poop_interval:
        pet._poop_wait_t = getattr(pet, "_poop_wait_t", 0.0) + dt
        if pet._poop_wait_t >= 1.0:                 # PoopWaitMin 1 game-min (was 60.0)
            pet._poop_wait_t = 0.0
    # death does not wait for morning: the caps, the filth/overweight
    # sickness rolls and the sick-death whisper run in bed too, exactly as
    # the "filth risk runs in bed" note promises -- _tick_mortality's own
    # gates freeze ONLY the starvation clock while asleep
    if pet._tick_mortality(dt):
        return
    # startPoop: even asleep, a truly DESPERATE gauge (>= 2x max) goes --
    # this must live in the sleep branch (the awake poop block below is
    # unreachable while asleep; latent until the canon day bands landed)
    pet._poop_t = getattr(pet, "_poop_t", 0) + dt
    if pet._poop_t >= pet._poop_interval * 2:
        pet._poop_t = 0                 # gauge zeroed (DVPet poop())
        pet._do_poop(backlog=True)
        pet._set_anim("poop", 2.2)


def _near_bedtime(pet: Any, n: Any) -> Any:
    """checkMaxHoursBeforeSleep's clock half: asleep aside, is nod-off
    within `n` game-minutes?  Pressure pets read the sleep clock
    (sleepLimit - sleepLapse <= n, canon verbatim); line pets read the
    wall clock to their fixed bedtime."""
    iw = pet._in_sleep_window()
    if iw is not None:
        if iw:
            return True
        bt = lines_mod.bedtime_minutes(pet)
        return bt is not None and (bt - pet.world_seconds % DAY_MINUTES) % DAY_MINUTES <= n
    return pet.sleep_limit - pet.sleep_lapse <= n


def _in_sleep_window(pet: Any) -> Any:
    """Line pets sleep by the CLOCK: True/False = inside/outside the form's
    fixed bedtime→7:00 window; None = not a line pet (pressure model)."""
    bt = lines_mod.bedtime_minutes(pet) if lines_mod.active(pet) else None
    if bt is None:
        return None
    mod = pet.world_seconds % DAY_MINUTES
    if bt > pet.WAKE_MINUTE:                     # the usual wrap past midnight
        return mod >= bt or mod < pet.WAKE_MINUTE
    return bt <= mod < pet.WAKE_MINUTE           # a midnight sleeper (24:00 -> 0)


def _tick_bedtime(pet: Any, dt: Any) -> None:
    """LINES_SPEC §5: the fixed per-form bedtime replaces the pressure clock.
    Inside the window the pet drops off by itself (a disturb postpones the
    re-sleep); lights-out OUTSIDE the window is a shallow nap, like checkNap.
    The nightly ritual: at bedtime the room is still lit — turning the lights
    off within the grace is the care; a lit sleeper logs the once-per-night
    lights mistake exactly as before."""
    if pet.asleep:
        return
    if pet._in_sleep_window():
        pet._bed_postpone_t = getattr(pet, "_bed_postpone_t", 0.0) - dt
        if pet._bed_postpone_t > 0:
            return                                # a disturb bought some grumbling time
        pet._fall_asleep()
        # the night is the window, not an energy budget: rested checks and
        # the sleep meter size off the real span (bedtime -> 7:00)
        bt = lines_mod.bedtime_minutes(pet)
        pet.awake_limit = (pet.WAKE_MINUTE - bt) % DAY_MINUTES
        pet.sleep_limit = DAY_MINUTES - pet.awake_limit
    elif not pet.lights:
        # the daytime doze waits out the same calcToSleepNapLapse as the
        # pressure model (sleep audit 2026-07-06)
        pet._to_nap_t = getattr(pet, "_to_nap_t", 0.0) + dt
        if pet._to_nap_t < pet._calc_to_nap():
            return
        pet._to_nap_t = 0.0
        # a daytime doze: same once-per-game-hour mood bonus guard as checkNap
        if pet.world_seconds - getattr(pet, "_nap_bonus_t", -9e9) >= 60:
            pet._nap_bonus_t = pet.world_seconds
        pet.asleep, pet.nap = True, True
        # the doze's own length: checkNap's fixed hour (awakeLimit -
        # minutesHour) -- without this the doze inherited the whole
        # previous NIGHT's awake_limit and slept the day away
        pet.awake_lapse = max(0.0, pet.awake_limit - 60.0)
        pet._lights_t = 0.0
        pet._lit_obed_hit = False
        pet._set_anim("yawn", 1.8)
    else:
        pet._to_nap_t = 0.0


def _calc_to_nap(pet: Any) -> Any:
    """calcToSleepNapLapse: how long the pet sits in the DARK before it
    nods off -- an energetic pet resists (~40 game-min), a drained one
    folds in 20; restless +-1.  (The obedience +1 left with the
    discipline system: the pinned-0 meter billed EVERY pet the extra
    doze minute while the >=75 discount was unreachable -- MED audit
    2026-07-19.)"""
    r = pet.restless * TO_SLEEP_NAP_RESTLESS
    return (TO_NAP_HIGH_ENERGY if pet.energy > pet.max_energy / 2
            else TO_NAP_LOW_ENERGY) + r


def _tick_sleep_pressure(pet: Any, dt: Any) -> None:
    """bedtime is a PRESSURE clock, not the sun (setSleepLapse): SleepLapseInc
    per game-min while awake; at the limit the pet drops off by itself --
    babies (inc 9) nap constantly, adults run a free ~24h rhythm.
    checkNap fires only after the DOZE-OFF WAIT (toNapSleepLapse; sleep
    audit 2026-07-06 -- the old instant nap skipped it): lights out, the
    pet sits a calcToSleepNapLapse while, THEN dozes (real sleep instead
    when the pressure is nearly full -- sleepNotNap).
    Line pets sleep by the CLOCK instead (LINES_SPEC §5)."""
    if pet._in_sleep_window() is not None:
        pet._tick_bedtime(dt)
        return
    if not pet.asleep:
        pet.sleep_lapse += dt * pet._sleep_inc()
        if pet.sleep_lapse >= pet.sleep_limit:
            pet._fall_asleep()
        elif not pet.lights:
            pet._to_nap_t = getattr(pet, "_to_nap_t", 0.0) + dt
            if pet._to_nap_t < pet._calc_to_nap():
                return                                  # still blinking in the dark
            pet._to_nap_t = 0.0
            edge = SLEEP_NOT_NAP_MIN - pet.restless * SLEEP_NOT_NAP_RESTLESS
            if pet.sleep_lapse >= pet.sleep_limit - edge:
                pet._fall_asleep()                     # close enough to bedtime
            else:
                # checkNap: a shallow doze that BORROWS the current cycle --
                # pressure keeps accruing, so real bedtime still arrives on
                # time.  The +10 nap mood keeps the extra once-per-game-hour
                # guard (belt over the doze-off wait, canon's own anti-farm)
                if pet.sleep_lapse - getattr(pet, "_nap_bonus_lapse", -9e9) >= 60:
                    pet._nap_bonus_lapse = pet.sleep_lapse
                pet.asleep, pet.nap = True, True
                pet._lights_t = 0.0
                pet._lit_obed_hit = False
                # checkNap's nap length: a SICK or hurt pet takes a fixed
                # hour (awakeLimit - minutesHour); healthy naps repay the
                # accrued pressure.  (Canon's end-of-hour 2-hour variant is
                # a wall-clock alignment quirk tuipet's clock doesn't have.)
                pet.awake_lapse = max(0.0, pet.awake_limit - pet.sleep_lapse)
                pet._set_anim("yawn", 1.8)
        else:
            pet._to_nap_t = 0.0                        # the light resets the wait


def _sleep_inc(pet: Any) -> Any:
    """Species sleep-pressure rate (SleepLapseInc: 1 adult / 2 / 9 baby)."""
    return data.load_requirements().get(pet.num, {}).get("sleep_lapse_inc", 1)


def _fall_asleep(pet: Any) -> None:
    """PhysicalState.sleep(): the pressure clock rolls over -- sleep long
    enough to refill the energy bar (clamped 6..15 game-hours), and the
    next awake stretch is whatever remains of the 24."""
    pet.sleep_lapse = 0.0
    pet.asleep = True
    pet.nap = False
    pet._calm_discipline_call()                # bedtime placates the tantrum (canon
    #                                             sleep-onset setDisciplineCall(false))
    pet._lights_t = 0.0                        # setAsleep resets _callMinutesLights
    gain = max(1, getattr(pet, "_sleep_energy_gain", 3))
    need = math.ceil(max(0, pet.max_energy - pet.energy) / gain) * 60.0
    pet.awake_limit = _clamp(need, MIN_AWAKE_LIMIT, MAX_AWAKE_LIMIT)
    pet.sleep_limit = DAY_MINUTES - pet.awake_limit
    pet._set_anim("yawn", 1.8)


def _wake(pet: Any) -> None:
    """setAsleep(false): the wake roll runs on EVERY rise -- natural,
    disturbed or lights-on alike (mood re-audit 2026-07-06; canon disturb()
    funnels through setAsleep(false) unconditionally, so even a grumbled
    wake takes its chances).  A full sleep wakes into the morning tiers; a
    NAP wakes with a +-NapWakeMoodDec swing on 2 rolls of the 5."""
    was_nap = pet.nap
    pet.asleep = False
    pet.nap = False
    pet.futon_doze = False          # the futon's deep doze is spent on wake
    # a pill's owed lights-out dies with the sleep it served (sleep audit
    # r2, 2026-07-28: waking mid-show left the debt armed, and the fx-end
    # hook then darkened the room on an AWAKE pet)
    pet.pending_lights_out = False
    pet.awake_lapse = 0.0
    pet.sleep_limit = DAY_MINUTES - pet.awake_limit
    # a MORNING wake lights the room (canon setLights(true)); a NAP wake
    # must NOT.  A daytime doze the player dimmed would otherwise flip its
    # own light on as the doze ends, and a still-tired pet that re-sleeps
    # then racks a lights-on care mistake it never earned -- the exact
    # wake -> lights-on -> re-sleep churn the recovery doze set out to kill
    # (nap-lights bug 2026-07-24, Joel: "napping with lights out will wake
    # up, turn lights on, then fall back asleep -- disastrous for care
    # mistakes").  The player owns the switch during a nap, not the pet.
    if not pet.lights and not was_nap:
        pet.lights = True                      # morning wake: setLights(true)
    wake_anim = "wake"
    r = random.randrange(MORNING_MOOD_CHANCE)
    m = pet.current_mood()
    if was_nap:
        if r == 0:
            wake_anim = "sad"                    # BadMorning: wakeUp(9)
        elif r == 1:
            wake_anim = "happy"                  # GoodMorning: wakeUp(5)
    else:
        # canon wakeUp poses vary with the morning: 7 normal / 5 good /
        # 9 bad / 6 terrible (birthday audit 2026-07-05: it always woke
        # on the plain pose).  The roll can swing mood by a full tier
        # with nothing but a 1.6s pose to show for it -- the morning now
        # leaves a note the HUD flashes (gameplay polish #11,
        # 2026-07-22; the assist_note pop grammar)
        if r == 0:
            wake_anim = "sad"                    # BadMorning: wakeUp(9)
            pet.wake_note = f"{pet.name} woke up on the wrong side…"
        elif r == 1 and m == "Feliz":
            wake_anim = "surprise"               # TerribleMorning: wakeUp(6)
            pet.wake_note = f"{pet.name} had an awful night!"
        elif r == 2:
            wake_anim = "happy"                  # GoodMorning: wakeUp(5)
            # the note tells the TRUTH about the night (sleep audit
            # 2026-07-22, Joel: "my mon woke up 'beaming' with only one
            # energy bar"): the morning ROLL is pure mood -- canon,
            # untouched -- but a cut-short night (a dawn re-sleep, a
            # midnight bedtime, the 7:00-sharp window) can wake a pet
            # half-empty, and 'beaming' over a drained gauge reads as a
            # bug.  Good roll + poor tank = up early, still weary.
            if pet.energy < pet.max_energy // 2:
                pet.wake_note = f"{pet.name} is up — still weary…"
            else:
                pet.wake_note = f"{pet.name} woke up beaming!"
    pet._set_anim(wake_anim, 1.6)


def _disturbed(pet: Any) -> Any:
    """PhysicalState.disturb(): bothering a sleeper wakes it grumpy.  The
    bookkeeping (count, missed day, postpone, sick risks) only bills REAL
    sleep -- but the mood/spirit dec and the wake land on a NAP too (mood
    re-audit 2026-07-06: canon keeps them outside the !nap guard).  Real
    sleep: nearly-rested (or full energy) it just gets up; otherwise the
    sleep is POSTPONED: it drops back off in DisturbPostpone game-minutes,
    still owing the missed rest."""
    if not pet.asleep:
        return t("guard_zzz", "zzz…")
    nap, postponed = pet.nap, False
    if not nap:
        pet.disturb += 1
        pet.mistake_day += 1                   # DisturbanceMissedDayChange
        rested = (pet.awake_lapse >= FULL_AWAKE_DISTURB - pet.restless * FULL_AWAKE_DISTURB_RESTLESS
                  or pet.energy >= pet.max_energy)
        if rested:
            pet.sleep_lapse = 0.0
        else:
            postponed = True
            postpone = random.randint(*DISTURB_POSTPONE)
            # the lapse regains _sleep_inc per game-min, so a gap of
            # postpone game-minutes is postpone x inc -- the old /inc
            # re-slept a baby (inc 9) in postpone/81 minutes
            pet.sleep_lapse = max(0.0, pet.sleep_limit - postpone * pet._sleep_inc())
            if pet._in_sleep_window() is not None:
                pet._bed_postpone_t = float(postpone)   # a line pet re-sleeps by the clock
            # (the missed rest is repaid naturally: _fall_asleep re-sizes the
            # next sleep from the CURRENT energy debt, so nothing is carried)
        # (the rough-waking sickness risks left with the sickness
        # system (BASIC VPET 2026-07-17))
    # DisturbMoodDec{,Restless,NotRestless}: a restless pet WANTED up
    enth = {1: -1, 0: -2, -1: -3}.get(pet.restless, -2)   # DisturbEnthusiasmDec*
    pet._set_enthusiasm(pet.enthusiasm + enth)
    pet._wake()                                # setAsleep(false): the wake roll
    pet.wake_note = ""                         # a disturbed wake reports the
    #                                             DISTURBANCE, not the morning tier
    if nap:
        return t("guard_stirs", "Mexeu e saiu da soneca.")
    if not postponed:
        return t("guard_grumbles", "Acordou resmungando.")
    pet._set_anim("angry", 1.8)                # Sad_Jeering: woken too soon
    return t("guard_mind_sleep", "zzz… mind its sleep!")


