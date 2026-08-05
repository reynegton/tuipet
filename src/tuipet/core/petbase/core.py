"""The pet's CONSTANT BED + pure helpers (tier-5 stage A, 2026-07-17):
every tuning number, canon table and pure function the sim reads --
extracted whole from pet.py's pre-class region so the coming mixins (and
pet.py itself) can star-import one leaf module and resolve every name in
their own namespace.  `from .pet import ANYTHING` still works: pet.py
star-imports this module back under the __all__ below."""
from __future__ import annotations
from typing import Any, Dict, Optional


class Refused(str):
    """A use_item result that did NOT consume the item.  Reads as a plain
    message everywhere else -- only use_item's consume check looks at the
    type (clone audit 2026-07-15: every refusal string used to burn the
    item)."""


def _clamp(v: Any, lo: Any, hi: Any) -> Any:
    return max(lo, min(hi, v))


WEEKEND_BIT_MULT = 1.5   # weekend COMBAT income bonus (DSprite study 2026-07-14)


def _weekend_mult(now: Optional[float] = None) -> float:
    """The real Sat/Sun check (the player's local clock); `now` is an epoch
    override for tests."""
    import time as _time
    t = _time.localtime(_time.time() if now is None else now)
    return WEEKEND_BIT_MULT if t.tm_wday >= 5 else 1.0


def weekend_bonus(now: Optional[float] = None) -> float:
    """x1.5 bit multiplier on real-world Sat/Sun.

    Applies to COMBAT/COMPETITION income only — battle-win bits and tournament
    purses — never to shop resells or refunds (those are sinks, scaling them
    would just cheapen items on weekends).  Kept as a thin wrapper around
    _weekend_mult so the test suite can pin it to a weekday (conftest) without
    losing the real logic.
    """
    return _weekend_mult(now)


def _enemy_level(enemy: Dict[str, Any]) -> int:
    """The foe's battle level.  DVPet's getLevel read power sums off the old
    enemy cards; 0.5 cards carry none (0.5 BATTLE 2026-07-17), so the STAGE
    rank is the level now -- the same 1..6 scale the corpus level_fought
    gates expect (Fresh 1 .. Mega 6)."""
    import tuipet.data.loaders.data as _data
    return max(1, _data.stage_rank(enemy.get("stage", "Rookie")))


# Lifespan (seconds), scaled from DVPet's real-time model. A pet lives this long
# (the DVPet lifespan clock -- LIFE_START / STAGE_LIFE / the whole LifeDec
# burn economy -- left with the DSprite mortality ruling, Joel 2026-07-22:
# "we gotta do it how dsprite does. life bar must be a dvpet forgotten
# relic".  Death is the clone's per-minute hazard roll now; age alone
# defines the elder.)
GERIATRIC_AGE_DAYS = 15      # the clone's elder line: age_days >= 15 (v0.4.12 L926)
AGE_DAY = 86400.0            # one REAL day of age_seconds (the clone's DAY_MINUTES scale)
GERIATRIC_REMAIN = 21600.0   # stomach-shrink window: the first N seconds past the elder line

# DVPet mood model (config.csv): a signed score mapped to a Mood enum.
MOOD_MIN, MOOD_MAX = -300, 300        # MinMood / MaxMood
MIN_HAPPY_MOOD = 150                  # MinHappyMood
MIN_UNHAPPY_MOOD = -1                 # MinUnhappyMood
TO_DEPRESSED_MOOD = -250              # ToDepressedMoodMin
NEW_UNDEPRESSED_MOOD = -50            # NewUndepressedMood
MIN_ENTHUSIASM, MAX_ENTHUSIASM = -10, 10   # MinEnthusiasm / MaxEnthusiasm
MAX_ENTHUSIASM_MOOD_PENALTY = 10           # MaxEnthusiasmMoodPenalty
# enthusiasmLapse (every EnthusiasmLapseMin=59 game-min == tuipet's mood lapse): awake, an
# unspent spirit sours the mood (mood -= |enth*EnthusiasmMoodDecCoefficient|) and an energetic
# pet's spirit climbs; asleep it decays toward 0.  Spending spirit on activities keeps the
# drain small -- a "stay engaged" mechanic.
# DEFERRED awake enthusiasmLapse constants (see tick's measured rationale --
# ported faithfully it collapses mood within ~15 real-min on the compressed clock)
ENTHUSIASM_MOOD_DEC_COEF = 2               # EnthusiasmMoodDecCoefficient
ENTHUSIASM_CHANGE_ENERGY_COEF = 24         # EnthusiasmChangeEnergyCoefficient
HIGH_ENERGY_ENTH_CHANGE = 1                # HighEnergyEnthusiasmChange (energetic -> spirit up)
LOW_ENERGY_ENTH_CHANGE = 0                 # LowEnergyEnthusiasmChange
ENTHUSIASM_LAPSE_DEC = 1                   # EnthusiasmLapseDec (asleep, +enth -> 0)
ENTHUSIASM_LAPSE_INC = 2                   # EnthusiasmLapseInc (asleep, -enth -> 0)

# DVPet obedience + battle-surrender morale (config.csv column 1, where CanRefuse=TRUE;
# Config.loadConfig strips the name column and PhysicalState loads column 0 => the first
# value column).  Drives PhysicalState.getObedienceFactors / getAdjustedObedience /
# checkSurrender — the pet may give up or beg to flee a battle based on disposition,
# obedience, health and win-rate.  Every number is verbatim from the binary.
CAN_REFUSE = True
REFUSE_CHANCE = 100                 # RefuseRate -> Random.nextInt(REFUSE_CHANCE)
# DELIBERATE DIVERGENCE (refusal recalibration, Joel 2026-07-08): canon compares
# a roll in [0,100) against obedience on the 0..150 scale, so a pet only reliably
# obeys once obedience clears ~100 -- and rookies live at 25..75, refusing half to
# all of every feed/train/battle/care command.  Canon absorbs that because its
# clock runs for days and each refusal is a brief autonomous blip; tuipet's
# compressed, keypress-driven loop turns each into a hard "scold it again" stop.
# A flat grace added to obedience in the refusal gate (NOT the stat itself) lifts a
# normally-raised pet (obed 50..75) to ~85..100% compliance while a neglected one
# (obed 0..25) still visibly rebels (refuses ~35..60%).  Applied once in
# check_refused so every branch (food/attr/item/activity) shares it.
REFUSE_OBEDIENCE_GRACE = 40.0
OBEDIENCE_REFUSAL_CAP = 100         # ObedienceRefusalCap (the refusal-ROLL bound only)
OBEDIENCE_MOOD_MOD = 15.0           # ObedienceMoodModCoefficient
OBEDIENCE_TIME_MOD = 10.0           # ObedienceTimeModCoefficient
# setObedience (obedience audit 2026-07-06): the stat itself caps at MaxObedience
# 150, and EVERY change is nudged once AGAINST the disposition (value -=
# disposition x 1: a sunny pet takes each change a point lower, a sour one a
# point higher) -- the mirror image of setMood's nudge
MAX_OBEDIENCE = 150                 # MaxObedience
OBEDIENCE_DISPO_COEF = 1            # ObedienceChangeDispositionCoefficient (SUBTRACTED)
# obedienceLapse: discipline FADES while awake -- dec 2 on a disposition-shaded
# cadence (sunny 180 / neutral 120 / sour 60 game-min), and each dec event also
# bills the mess (ObedienceChangeFilthScale x piles).  MinObedienceAsleep 150
# == MaxObedience: the lapse can never run asleep (shipped-config quirk).
# THE DISCIPLINE FADE (D1, 2026-07-23): manners drain while AWAKE, so
# discipline is a practice and not a high-water mark.  Canon's SHAPE and
# its 3:2:1 disposition ratio are kept verbatim; the CADENCE is scaled
# x5 because canon's minutes are DEVICE real-minutes and tuipet's clock
# runs 60x faster (THE UNIT LAW).  Sized against the measured reward
# rate rather than copied -- the plan audit proved a raw port drains
# ~60/hour against ~17/hour of reward, parking every pet at 0 and
# inverting D3's promise.  At x5: neutral is -2 per 10 real min
# (-12/hour) against a tantrum's +25 per ~90 real min (+17/hour), so an
# attentive tamer climbs and a neglectful one sinks.
# EARNED DISOBEDIENCE (D3, 2026-07-23 -- Joel approved this SHAPE and
# only this shape).  It AMENDS the soft-refusal recalibration, which was
# made against the OLD chance-based spam that punished well-raised pets.
# This punishes NEGLECT instead: a pet only ever refuses below a quarter
# of the gauge (canon's own ROOKIE_OBED_DEFAULT sits right here), and a
# well-raised pet NEVER refuses, which is what that rule was protecting.
# The odds ramp from 0 at the threshold to DISOBEY_MAX_P at empty, so
# the first refusals are a warning, not a wall.  The cure is RAISING --
# answer tantrums, scold, praise -- never waiting.
DISOBEY_BELOW = MAX_OBEDIENCE // 4      # 37 of 150
DISOBEY_MAX_P = 0.5                     # at a fully neglected gauge
_LAPSE_SCALE = 5
OBEDIENCE_LAPSE_MIN = {0: 120.0 * _LAPSE_SCALE,        # ObedienceLapseMin
                       1: 180.0 * _LAPSE_SCALE,        # ...High disposition
                       -1: 60.0 * _LAPSE_SCALE}        # ...Low disposition
OBEDIENCE_LAPSE_DEC = 2             # ObedienceLapseDec (same for all dispositions)
OBEDIENCE_FILTH_SCALE = -1          # ObedienceChangeFilthScale
# checkRefusedOff: an UNSCOLDED refusal expires on its own -- the pet got away
# with it (mood up) and hardens a little less (obedience down)
REFUSED_OFF_MIN = 10.0              # RefusedOffMin (game-min on tuipet's cadence scale)
REFUSED_OFF_MOOD_INC = 1            # RefusedOffMoodInc
REFUSED_OFF_OBED_DEC = 1            # RefusedOffObedienceDec
OBEDIENCE_CHANGE_INTOL_FORCED = -3  # ObedienceChangeIntolerantForced (complied + intolerant meal)
# PhysicalState.spoil (config SpoilMoodInc / SpoilObedienceDec): a mood lift paired
# with an obedience cost. tuipet's Play button maps onto this DVPet mechanic.
SPOIL_MOOD_INC = 10                 # SpoilMoodInc
SPOIL_OBEDIENCE_DEC = 10            # SpoilObedienceDec
OBEDIENCE_ENTH_MOD = 6.0            # ObedienceEnthusiasmModCoefficient
REFUSE_UNWELL_SICK = -10.0          # RefuseUnwellModSickFactor
# checkRefused branch mods (config.csv col 1)
REFUSE_MED_FACTOR = -20.0           # RefuseMedFactor (medicine tastes awful)
REFUSE_DISLIKED_FOOD = -25.0        # RefuseDislikedFoodCoefficient (x hunger/stomach)
REFUSE_FAV_STOMACH = 10.0           # RefuseFavModStomachCoefficient (x room left)
REFUSE_HUNGER_MOD = -25.0           # RefuseHungerModCoefficient (x hunger/stomach)
REFUSE_GLUTTON_HUNGER = -15.0       # RefuseGluttonHungerModCoefficient
REFUSE_NOT_GLUTTON_HUNGER = -30.0   # RefuseNotGluttonHungerModCoefficient
REFUSE_PERSONALITY_MATCH = 10.0     # RefuseFavMod*MatchFactor (food suits its temperament)
REFUSE_PERSONALITY_UNMATCH = -10.0  # RefuseFavMod*UnmatchFactor
REFUSE_INTEREST_MOD = -15.0         # RefuseInterestModCoefficient (a bored pet refuses toys)
WEAK_CONSUMABLE_COEF = 0.1          # WeakConsumableCoefficient: a COMPLIANT pet takes items
#                                     grudgingly (Inherit/Recover exempt, like applyItem)
EXERCISE_REFUSE_LOW_ENTH = 20.0     # ExerciseRefuseLowEnthusiasmFactor (fav attr, dispirited)
BATTLE_DISPO_COEF = 10.0            # HighDispositionBattleObedienceDispositionCoefficient
BATTLE_LOW_DISPO_FACTOR = 50.0      # LowDispositionBattleObedienceFactor (docile pets fight when told)
# checkStopTravel (config.csv col 1).  MinEnergyForActivity is -127 in classic --
# the energy floor never gates, so it is not ported.
REFUSE_TRAVEL_COEFF = 3000.0        # RefuseTravelCoefficient (roll range 100..300100)
REFUSE_TRAVEL_WALK = 5.0            # RefuseTravelModWalkFactor (run=20; tuipet has no run mode)
REFUSE_TRAVEL_DISPO = 35.0          # RefuseTravelDispositionCoefficient
# gift call (config.csv col 1): a HAPPY pet may find you a present
GIFT_CHANCE_MIN = 57.0              # GiftChanceMin: game-min between rolls
GIFT_CHANCE_FACTOR = 70             # GiftChanceFactor
GIFT_FESTIVAL_MULT = 3             # a festival pet gifts ~3x as often (2026-07-24)
GIFT_CHANCE_MOOD_COEFF = 0.5        # GiftChanceMoodCoefficient
# trained battle HP (config.csv col 1): the HP drill GROWS fullHealthPoints
STARTING_HEALTH_POINTS = 5          # StartingHealthPoints (resetToEgg)
PERFECT_WINS_LIMIT = 1              # PerfectWinsLimit is 5 in canon -- scaled x5 for the
#                                     compressed clock EXACTLY like TRAIN_POWER_PER_HIT:
#                                     a real device stage lasts DAYS; 50 drill wins to
#                                     reach Champion-foe HP parity (foes 15-25 vs the
#                                     starting 5) was unreachable in a ~2h tuipet stage,
#                                     so pets fought at 5 HP forever, lost constantly,
#                                     and the losses fed the misbehaving spiral
#                                     (audit 2026-07-05).  Every HP-drill win = +1 HP,
#                                     still capped by the age ladder (max_health()).
PERFECT_WINS_HEALTH_INC = 1         # PerfectWinsHealthInc
# getMaxHealth: the HP CAP rises with lapsed life (real-seconds -> game-days here:
# 86400s real = 1 day = 1 tuipet DAY_LENGTH); classic MaxHealth* ladder
HEALTH_CAP_LADDER = ((13, 30), (10, 25), (7, 20), (4, 15), (1, 10))  # (days, cap)
MAX_HEALTH_DEFAULT_CAP = 10         # MaxHealthDefault (under a day old)
# exercise() nuances
EXERCISE_WORSE_SICK_CHANCE = 1      # ExerciseWorseSickChance %
OBEDIENCE_CHANGE_SICK_FORCED = -5   # ObedienceChangeSickForced (forced a sick pet; it got worse)
EXERCISE_CALORIE_DEC = 1            # ExerciseCalorieDec
FAV_EXERCISE_TIME_MOOD = 10         # FavExerciseTimeMoodInc
FAV_EXERCISE_TIME_ENTH = 1          # FavExerciseTimeEnthusiasmChange
NOTFAV_EXERCISE_TIME_MOOD = 2       # NotFavExerciseTimeMoodDec
DISLIKED_TIME_EXERCISE_ENTH = -1    # DislikedTimeExerciseEnthusiasmChange
MODE_CHANGE_ENERGY = -1             # ModeChangeEnergyChange
# toy engagement (applyItemNoObedience): a bored pet gets less from its toys
MAX_ITEM_INTEREST = 5               # MaxItemInterest
ITEM_INTEREST_TIMER = 60            # ItemInterestTimer (game-min per -1 decay; 40 sunny / 80 sour)
ITEM_INTEREST_LOW_TIMER = 40        # ItemInterestLowTimer (disposition +1)
ITEM_INTEREST_HIGH_TIMER = 80       # ItemInterestHighTimer (disposition -1)
PERSONALITY_MOOD_MATCH = 10         # ConsumablePersonalityMatchMoodChange
PERSONALITY_MOOD_UNMATCH = -10      # ConsumablePersonalityUnmatchMoodChange
CALL_MOOD_DEC = 1                    # CallMoodDec: a standing care call drains mood per window-min
EGG_MOOD = 100                      # EggMood: a new egg starts warm (Evolution.egg)
# Evolution.java per-stage ARRIVAL setters (egg/hatch audit 2026-07-06; the
# shipped ranges are all min==max -> deterministic)
FRESH_MOOD = -10                    # FreshMood: born grumpy (it's a newborn)
FRESH_OBEDIENCE = 75                # FreshObedienceMin/Max: born TRUSTING
START_NUTRITION = 6                 # StartProtein/StartMineral/StartVitamin
IN_TRAINING_OBEDIENCE = 50          # InTrainingObedienceMin/Max: toddler rebellion cap
IN_TRAINING_SLEEP_LAPSE = 360       # InTrainingSleepLapse: wakes with real bedtime pressure
ROOKIE_OBED_GOOD = 50               # RookieGoodObedience (Happy daily majority)
ROOKIE_OBED_DEFAULT = 25            # RookieDefaultObedience (Neutral majority)
ROOKIE_OBED_BAD = 0                 # RookieBadObedience (anything else, ties included)
# the missed-day / birthday system (setTimeToAge): each game day of AGE the pet
# has a birthday judged by the day's MAJOR mood and its missed-day tally
MOOD_RECORD_MIN = 5                 # MoodRecordMin: sample the mood tier every 5 game-min
MAX_MISTAKE_DAY_BONUS = 0           # MaxMissedDayForBonusInc: a good day allows ZERO slips
MIN_MISTAKE_DAY_DEC = 1             # MinMissedDayForBonusDec
# (BonusLifeInc/Dec + BonusEvolutionLife left with the lifespan clock --
# DSprite mortality 2026-07-22; the birthday still moves evol_bonus + items)
# DVPet memory / inheritance (PhysicalState.setNewMemory / getMemory,
# item 32 anim Inherit; config.csv MemoryAttributeCoefficient / LifeInc).  The
# departed etches its attack powers -- scaled by the care bonus it died holding --
# into the Memory; the HEIR uses the item to add Va/D/Vi.  (The chip's
# lifespan leg left with the lifespan clock -- DSprite mortality 2026-07-22;
# old chips' "seconds" payloads load fine and are simply not applied.)
MEMORY_ATTR_COEF = 0.01         # MemoryAttributeCoefficient
# A WILD (found) memory's payload -- Joel 2026-07-24 "make wild chips
# carry a random payload".  A single random attribute, well under the +15
# base attribute chip: a stranger's faint trace, not a maxed ancestor's.
WILD_MEMORY_MIN = 5
WILD_MEMORY_MAX = 15
# (the birthday grants speak the TUIPET catalog keys since 2026-07-18 --
# the raw DVPet food ids landed items the strict bag could neither show
# nor use, a reward the player never received; item review 2026-07-18)
GOOD_BIRTHDAY_FOOD = "cupcake"
BAD_BIRTHDAY_FOOD = "candy"
NORMAL_BIRTHDAY_FOOD = "cookie"
WIN_RATE_BONUS_COEF = 0.1           # winRateRookieBonusIncCoefficient (champion: 0.1*winRate - 5)
# saveFromDeath: frantic taps during the dying beat can pull the pet back
HITS_TO_SAVE = 30                   # HitsToSave 175 mouse-clicks over DVPet's ~7s jingle,
                                    #   scaled to a ~6/s keyboard mash over tuipet's 5s beat
HUNGER_AFTER_SAVED = 0              # HungerAfterSavedFromDeath (alive, but starving)
BONUS_AFTER_SAVED = -1              # BonusChangeAfterSavedFromDeath
# battle style (Battle_Style menu): Free = the pet fights its own way (+1 all
# powers, never refuses an order it never got); Orders = you call each attack
# (it may refuse mid-fight, but discipline pays obedience and prouder wins)
BATTLE_FREE_OBED_INC = 1            # BattleFreeObedienceInc (fighting under orders)
ORDERS_WON_MOOD_INC = 10            # OrdersWonMoodInc
BATTLE_DISPO_MOOD_FACTOR = -5       # BattleDispositionMoodFactor (x -disposition)
OBED_HEALTH_COEF = 5                # ObedienceChanceHealthCoefficient (hp >= full/5 = "saudável")
HI_DISPO_OBED_HIGH_HP = 0           # HighDispositionObedienceChanceHighHealthFactor
HI_DISPO_OBED_LOW_HP = -10          # ...LowHealthFactor (a hurt pet obeys less)
HI_DISPO_REFUSE_COEF = 10           # HighDispositionRefuseChanceDispositionCoefficient
LO_DISPO_OBED_HIGH_HP = 10          # LowDispositionObedienceChanceHighHealthFactor
LO_DISPO_OBED_LOW_HP = -10
LO_DISPO_REFUSE_LOW_ENEMY = 0       # LowDispositionRefuseChanceLowEnemyHealthFactor
LO_DISPO_REFUSE_HIGH_ENEMY = 10     # ...HighEnemyHealthFactor (a docile pet balks when losing)
# perfect-conditions energy save (checkEnergyIncFromPerfectConditions):
# an energy DROP during the pet's favourite time may bounce back +1 --
# roll nextInt(base + mods) == 1, so perfect conditions shrink the range
ENERGY_BONUS_BASE = 10              # BonusEnergyIncChance
ENERGY_BONUS_MOOD = -1              # EnergyBonusChanceGoodMood
ENERGY_BONUS_NUTRITION = -2         # EnergyBonusChanceGoodNutrition
ENERGY_BONUS_COMPAT_F = -1          # Compatible/IncompatibleField/Element*Change
ENERGY_BONUS_COMPAT_E = -1
ENERGY_BONUS_INCOMPAT_F = 2
ENERGY_BONUS_INCOMPAT_E = 1
GOOD_NUTRITION_FATIGUE_CHANCE = 40  # GoodNutritionFatigueChance (else FatigueChance 60)
FATIGUE_COMPAT_CHANGE = 5           # Compatible/Incompatible{Field,Element}FatigueChanceChange
# the sleep cycle (config.csv col 1): a free-running ~24h pressure rhythm --
# sleepLapse accrues awake (species SleepLapseInc/min) until sleepLimit, the
# pet sleeps long enough to refill its energy, and the cycle re-anchors
DAY_MINUTES = 1440                  # HoursDay * MinutesHour
MIN_AWAKE_LIMIT = 360.0             # MinAwakeLimit (shortest sleep: 6 game-hours)
MAX_AWAKE_LIMIT = 900.0             # MaxAwakeLimit (longest: 15)
MORE_SLEEP_CHANCE = 9               # MoreSleepChance (the per-minute sleep jitter roll)
LIGHTS_ON_AWAKE_STALL = 50          # LightsOnAwakeLapseUnchangedChance: lit rest is poor rest
CHANGE_NAP_TO_SLEEP = 240           # ChangeNapToSleepMinutes: a held nap becomes the night
NAP_TO_SLEEP_RESTLESS = 10          # ChangeNapToSleepMinutesRestlessCoefficient
NAP_ENERGY_INC = 30                 # NapEnergyInc (checkNapEnergy's accumulator threshold)
NEGATIVE_ENERGY_GAIN = 6            # NegativeEnergyGain: a DRAINED pet recovers faster
SLEEP_MIN_HUNGER_DECAY = 3          # SleepMinHungerDecay: asleep the stomach floors here
SLEEP_MIN_TO_GAIN = 60.0            # SleepMinutesToEnergyGain (uniform across the corpus)
AWAKE_RESTLESS_COEF = 1             # AwakeLapseRestlessCoefficient
BONUS_SLEEP_ENERGY = 2              # BonusSleepEnergy (a restless skip still rests)
NAP_ENERGY_MIN = 1                  # NapEnergyMin
SLEEP_NOT_NAP_MIN = 90              # SleepNotNapMinutes (- restless*60): lights-out near
SLEEP_NOT_NAP_RESTLESS = 60         #   bedtime starts REAL sleep instead of a nap
ON_NAP_MOOD_INC = 10                # OnNapMoodInc
# toNapSleepLapse -> calcToSleepNapLapse (sleep audit 2026-07-06): the pet sits
# in the DARK a while before nodding off -- energetic ~40 game-min, drained 20,
# +-restless, and a well-drilled pet (obedience >= 75) drops the extra +1.
# This delay is canon's real anti-farm for the +10 nap mood.
TO_NAP_HIGH_ENERGY = 40             # ToNapHighEnergyFactor (energy > max/2)
TO_NAP_LOW_ENERGY = 20              # ToNapLowEnergyFactor
TO_NAP_OBEDIENCE_FACTOR = 75        # ToNapObedienceFactor
TO_SLEEP_NAP_RESTLESS = 1           # ToSleepNapLapseRestlessCoefficient
DISTURB_POSTPONE = (10, 60)         # DisturbPostponeMin/Max (game-min until it re-sleeps)
FULL_AWAKE_DISTURB = 480.0          # MaxMinutesToFullAwakeDisturb (- restless*60)
FULL_AWAKE_DISTURB_RESTLESS = 60.0
DEPRESSED_OBEDIENCE = 50.0          # DepressedObedience
SURR_HEALTH_COEF = 5.0              # SurrenderChanceHealthCoefficient
SURR_DISP_COEF = 5.0                # HighDispositionSurrenderChanceDispositionCoefficient
HD_CONT_HI_HP, HD_CONT_LO_HP = 30.0, -10.0    # HighDispositionContinueChance*HealthFactor
HD_CONT_HI_EHP, HD_CONT_LO_EHP = -10.0, 25.0  # HighDispositionContinueChance*EnemyHealthFactor
HD_SURR_HI_HP, HD_SURR_LO_HP = -10.0, 10.0     # HighDispositionSurrenderChance*HealthFactor
LD_CONT_HI_HP, LD_CONT_LO_HP = 60.0, 0.0       # LowDispositionContinueChance*HealthFactor
LD_SURR_HI_EHP, LD_SURR_LO_EHP = 5.0, -60.0    # LowDispositionSurrenderChance*EnemyHealthFactor
SURR_HI_EHP, SURR_LO_EHP = 10.0, 30.0          # SurrenderChance*EnemyHealthFactor
SURR_HI_FACTOR, SURR_LO_FACTOR = 3.0, 0.75     # SurrenderChanceHigh/LowFactor
SURR_HI_WINRATE_MIN = 0.4                       # SurrenderChanceHighFactorWinRateMin
# aftermath (ClockTic.surrenderEffect / surrender-reject / Battle.surrender)
# battleEnd's tail (battle-math audit 2026-07-06)
BATTLE_WON_WORSE_SICK = 10              # BattleWonWorseSickChance (winning hurt still costs)
BATTLE_LOST_WORSE_SICK = 20             # BattleLostWorseSickChance
BATTLE_LOW_HEALTH_COEF = 2              # BattleLowHealthCoefficient (limping = at/below half HP)
BATTLE_HIGH_HP_ENERGY = 1               # BattleHighHealthEnergyDec
BATTLE_LOW_HP_ENERGY = 2                # BattleLowHealthEnergyDec (a hard fight drains double)
BATTLE_CAL_HIGH = 1                     # BattleCalorieDecHighHealth
BATTLE_CAL_LOW = 2                      # BattleCalorieDecLowHealth
BATTLE_LOST_MISSED_DAY = 1              # BattleLostMissedDayChange
SURR_DECLINED_LOST_OBED = 10            # SurrenderRequestDeclinedLostBattleObedienceDec --
#                                         it BEGGED to quit, you refused, it lost: obedience
#                                         is SET to 10 (absolute), not decremented
ENEMY_SICK_CHANCE = 50                  # EnemySickChance: fighting a SICK opponent (PvP
#                                         contagion -- the partner's real state ships) risks
#                                         catching it at battle's end, win or lose
SURR_EFFECT_MOOD_INC = 10               # SurrenderEffectMoodInc
SURR_EFFECT_LOWDISP_MOOD_DEC = 20       # SurrenderEffectLowDispositionMoodDec
SURR_EFFECT_REQ_OBED_DEC = 10           # SurrenderEffectRequestObedienceDec
SURR_EFFECT_OBED_DEC = 1                # SurrenderEffectObedienceDec
SURR_EFFECT_REQ_LOWHP_OBED = 15         # SurrenderEffectRequestLowHealthObedienceInc (setObedience)
SURR_REJECT_MOOD_DEC = 10               # SurrenderRejectMoodDec
SURR_REJECT_OBED_INC = 1                # SurrenderRejectObedienceInc
SURR_ENTH_DEC = 3                       # SurrenderEnthusiasmDec
