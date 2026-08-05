from .core import *
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
# ---- the DSprite sickness (rebuilt 2026-07-17, Joel: "dsprite didnt have
# sickness?" -- it DID, a thin one, so the classic machine's removal keeps
# the CLONE's rules): one flag, caught per game-minute from filth or
# overweight, cured ONLY by the pill.  No spell timer, no worsening, no
# contagion, no counters.  Constants verbatim from the clone (v0.4.12).
SICK_POOP_P = 0.015            # RETIRED (live-play audit 2026-07-25): the flat
#                                stand-in the lost FILTH_SICK_CHANCE/BOUND
#                                wiring shipped with; kept only to name the
#                                rate the scaled roll matches at 3 piles.
#                                The live roll is in _filth_effects.
SICK_OVERWEIGHT_P = 0.00375    # per overweight step: floor(excess/(base*0.5))
DEATH_SICK_P = 7.5e-5          # the clone's per-minute death whisper while sick
# ---- the DSprite mortality (rebuilt 2026-07-22, Joel: "we gotta do it how
# dsprite does. life bar must be a dvpet forgotten relic"): NO lifespan
# clock, no burns -- death is ONE per-minute hazard roll, the sum of the
# first matching mistake bracket, the sick whisper above, and the first
# matching age bracket.  A healthy pet with <5 mistakes under age 15 CANNOT
# die by the roll.  Tables verbatim from the clone (v0.4.12 L45-47); the
# discrete nets (20-mistake cap, Pen20 frailty, 12h starvation) stand
# beneath it as before -- Pen20 is LINES_SPEC §5 contract, not clock.
DEATH_MISTAKES = ((20, 0.0015), (15, 3.75e-4), (10, 7.5e-5), (5, 1.5e-5))
DEATH_AGE = ((25, 3.75e-4), (20, 1.5e-4), (15, 3.75e-5))
BAD_WEIGHT_MOOD_DEC = 2                 # BadWeightMoodLapseDec (per lapse off Healthy)
VERY_NEUTRAL_MOOD_DEC = 5               # VeryNeutralMoodLapseDec (neutral [5,150) drains faster)
DEPRESSED_LAPSE_MIN = 59.0              # DepressedLapseMin
DEPRESSED_CHANCE = 1000                 # DepressedChance (the roll bound)
DEPRESSED_EXIT_NEG = 100                # DepressedToUnhappyNegativeMoodChance
DEPRESSED_EXIT_POS = 500                # DepressedToUnhappyPositiveMoodChance
UNDEPRESSED_OBED_INC = 33               # UndepressedObedienceIncPositiveMood
DEPRESSED_MOOD_CHANGE = 50              # DepressedMoodChange (each interval while depressed)
DEPRESSED_OBED_CHANGE = -5              # DepressedObedienceChange (each interval)
DEPRESSED_ENTH_CHANGE = -1              # DepressedEnthusiasmChange
TO_DEPRESSED_ROLL_NEG = 10              # negativeMoodDepressedChance (mood <= -250)
TO_DEPRESSED_ROLL_NORM = 1              # normalMoodDepressedChance
POOP_MAX_PILES = 4                      # classic Monster V-Pet max poops (DVPet's _filth[] is 6; Joel set 4 to match the real toy)
POOP_SIZE_FITTING_MAX = 3               # biggest filth art that fits its 8-col slot (7x7 / 8x7 / 8x8); size 4 is 10 wide -- see _do_poop

# DVPet calorie buffer (config.csv, PhysicalState.calorieChange / setCalories): a
# -CalorieLimit..+CalorieLimit "fullness within the current hunger heart".  Each lapse
# the buffer drains (faster when geriatric); when it empties the hunger heart drops a
# level (or, at zero, logs a care mistake).  Eating refills it; overfilling speeds the
# next poop.  DVPet's two coupled timers collapse here to one buffer whose drain rate is
# tuned to preserve tuipet's ~1800s-per-heart hunger pace (col-1 calorie mods are 0).
# hunger / stomach (DVPet FullHunger / StomachCapacity / OvereatLimit)
FULL_HUNGER = 4                         # FullHunger: a satisfied stomach (4 hearts)
BATTLE_ENERGY_COST = 5              # the 0.5 bout's toll (clone BATTLE_ENERGY_COST)
BATTLE_WEIGHT_COST = 4              # the 0.5 bout sheds real weight (clone)
EXP_PER_WIN = 100                   # DMX experience per defeated enemy.  The manual's
#                                     award is unspecified; 100 maps its canon level
#                                     thresholds onto tuipet's win pacing (LV5=8 wins,
#                                     LV8=20, LV10=50 -- humulos LV fix 2026-07-17)
TRAIN_ENERGY_COST = 2               # the 0.5 drill's swing (clone TRAIN_ENERGY_COST)
BATTLE_MIN_ENERGY = 10              # the source's battle gate (canon gates 2026-07-18,
#                                     decompile L11746: energy < 10 refuses the fight)
# THE INJURY ROLL (canon restoration 2026-07-23: the decompile's
# BattleInjury table, adapted to today's tree -- the fatigue/mood
# coefficients left with their systems).  Chance out of BATTLE_INJ_BOUND
# per LOCAL recorded bout: condition good/bad x vitamin active or not,
# +BATTLE_INJ_LOSS on a loss, +BATTLE_INJ_BAD_AGE for an elder or an
# InTraining baby.  "Bad" condition = starving, drained, weight >= 8g
# off base, or already sick.  A live vitamin is the canon guard
# (good_v 0 / bad_v 25 -- the vitamin's second job on the device).
# INJURY RECOVERY (P4 ruling 2026-07-23): canon heals a wound on a clock
# -- `randint(1, 12) * InjLapseMin` game-min -- and v0.5.205 shipped the
# ailment WITHOUT it, leaving a 300b shop-only Bandage as the only cure
# while its sibling ailment has a free infinite one.  Restored, with the
# lapse SCALED: canon's 29 is device real-minutes, which under THE UNIT
# LAW would be 29 real SECONDS here (an injury gone before you noticed),
# while the flat /60 precedent would run up to 5.8 real HOURS (longer
# than any session).  300 game-min = 5 real minutes a lapse, so a wound
# lasts 5-60 real minutes of play.  The Bandage stays the INSTANT cure:
# it now buys time rather than being the only door.
MIN_INJ_LENGTH, MAX_INJ_LENGTH = 1, 12  # Min/MaxInjLength, canon
INJ_LAPSE_MIN = 300                     # game-min per lapse (canon 29 = device real-min)
BATTLE_INJ_BOUND = 1000
BATTLE_INJ_TABLE = {"good_v": 0, "good_nv": 3, "bad_v": 25, "bad_nv": 100}
BATTLE_INJ_LOSS = 50                # BattleInjuryWonFactor, added on a LOSS
BATTLE_INJ_BAD_AGE = 10             # BattleInjuryBadAgeFactor (elder OR baby)
DEATH_INJ_P = 7.5e-5                # the death whisper while hurt (sick's scale)
PILL_ENERGY_GAIN = 7                    # the DSprite pill (feed menu, BASIC VPET 2026-07-16)
# THE ERASER, rehoused 2026-07-23 (Joel: "one at a time, own item").  Both
# numbers are DVPet's own, not tuned: foods.csv row 18 (Miracle Drink) is the
# only consumable in either sheet with Mistake = -1, and it carries Energy 12.
MIRACLE_ENERGY_GAIN = 12
# the CURE ladder (2026-07-27): the cheap eraser TAKES the tank the drink
# gives, so the two are a ladder and not the same item at two prices
COMPRESS_ENERGY_COST = 8
# items.csv row 0 (Textbook) = Obedience +20, on the canon 150 scale.
TEXTBOOK_OBEDIENCE = 20
# THE GROW CAPSULE, priced (Joel 2026-07-24: "make the grow capsule worth
# 500b").  A FRACTION of the stage rather than a flat number of minutes:
# the stages run 180..2880 game-minutes, so any flat figure worth having in
# an Ultimate skips a baby stage whole -- the fraction is the only shape
# that means the same thing at every stage.  A quarter puts it beside its
# shelf-mates (the 300b Dumbbell buys ~10 drills of an evolution gate; the
# 500b Vitamin fills effort outright).
GROW_CAPSULE_FRACTION = 0.25
PILL_WEIGHT_GAIN = 5
STOMACH_CAPACITY = 4                    # legacy fallback only -- see stomach_capacity()
# canon stomach (food audit 2026-07-15): capacity is a PER-SPECIES field
# (monster.csv StomachCapacity, 8..40) that SHRINKS in old age --
# getStomachCapacity subtracts (geriatricAge - lifeRemaining) x 0.00021/real-s
# (max ~9 at death), floored at MinStomachCapacity.  It divides applyFood's
# diminishing modifier and gates feed()'s taste moods; the overeat line is
# 0.75 x capacity (OvereatLimitFactor).  tuipet's refuse-at-full stays the
# documented adaptation, so only the modifier/mood-gate sides apply here.
MIN_STOMACH_CAPACITY = 7                # MinStomachCapacity
OVEREAT_FACTOR = 0.75                   # OvereatLimitFactor (x capacity)
# canon 0.00021 per REAL second across the 43200s window (max dec ~9.07);
# tuipet's shrink runs over the GERIATRIC_REMAIN window PAST the elder line
# (age-based since the DSprite mortality port 2026-07-22) -- same endpoint shape
GERIATRIC_STOMACH_COEF = (43200 * 0.00021) / 21600.0
DISPOSE_LEFTOVERS_MIN = 0.5             # DisposeLeftoversMinModifier: at/below, Munching drops the rest
OVEREAT_LIMIT = 5                       # OvereatLimit: a glutton may fill one heart past full
CALORIE_LIMIT = 4                       # CalorieLimit (buffer half-range)
DP_MAX = 4                              # Pen20 DP meter: full (4) required to jogress;
DP_SLEEP_MIN = 45.0                     # +1 per 45 game-min asleep (3h sleep = a full refill)
FOOD_WEIGHT_CHANGE = 1                  # FoodWeightChange: calories rising while positive fattens
DIRTY_EATING_MOOD_DEC = 10              # DirtyEatingMoodDec (a meal amid the filth)
DIRTY_EATING_WORSE_CHANCE = 16          # DirtyEatingWorseSickChance (% per pile)
DIRTY_EATING_SICK_CHANCE = 8            # DirtyEatingSickChance (% per pile)
LESS_HUNGER_CHANCE = 9                  # LessHungerChance: the glutton decay-jitter odds
# sleep (DVPet setAsleep / lightsCall / the morning wake roll)
# careBonusOnReset (config col 0): the departed's whole-life REPORT CARD --
# graded at the next generation's start; the result SEEDS the new egg's bonus.
# (The Memory etch runs FIRST and spends the bonus, so an etched life
# grades from zero + the card; an unetched one keeps its leftover credit.)
BONUS_INC_OBEDIENCE = 75                # BonusIncObedience
BONUS_DEC_OBEDIENCE = 50                # BonusDecObedience
BONUS_INC_WIN_RATE = 90                 # BonusIncWinRate (lifetime %)
BONUS_STAGE = {                         # stage base / attribute bar / battles bar
    "Champion": (0, 175, 30),           # (+1 extra when NOT a Failed form)
    "Ultimate": (2, 225, 50),
    "Mega": (3, 300, 75)}
MISTAKE_HAPPY_MOOD = 100                # MistakeHappyMoodChange: a Happy pet DROPS TO 100
MISTAKE_MOOD_DEC = 50                   # MistakeMoodDec: everyone else loses 50
LIGHTS_MISTAKE_POSTPONE = -60.0         # AfterMistakeMinutesPostponed: the NEXT lit mistake
#                                         lands 120 lit-minutes on (it REPEATS, not once/night)
LIGHTS_MISTAKE_OBED = -1                # LightsOnMistakeObedienceChange (once per night)
HUNGER_MISTAKE_OBED = 1                 # HungerMistakeObedienceChange (canon: +1!)
HUNGER_MISTAKE_OBED_GLUTTON = -1        # ...ChangeGlutton
LIGHTS_MISTAKE_SEC = 60.0               # MinutesToMistakeLights(60) as ~12% of the sleep,
#                                         scaled to tuipet's ~6-min night -- one mistake/night
MORNING_MOOD_CHANCE = 5                 # MorningMoodChance: 1/5 bad, 1/5 terrible-if-happy, 1/5 good
BAD_MORNING_MOOD = {"Feliz": -150, "Neutro": -100, "Triste": -10, "Deprimido": -10}
GOOD_MORNING_MOOD = {"Feliz": 50, "Neutro": 100, "Triste": 150, "Deprimido": 150}
WORST_MORNING_MOOD = -10                # WorstMorningMood (TerribleMorning sets mood TO this)
NAP_WAKE_MOOD_DEC = 20                  # NapWakeMoodDec: a NAP wake swings +-20 on 2 of the 5 rolls
# disturb (setAsleep(false) runs the wake roll after these; canon disturb())
DISTURB_MOOD_DEC = {1: 0, 0: 10, -1: 20}     # DisturbMoodDec{Restless,,NotRestless}: a restless
#                                              pet WANTED up (0); a mellow one hates it (20)
DISTURB_WORSE_SICK_CHANCE = 50          # DisturbWorseSickChance % (an already-sick sleeper worsens)
DISTURB_SICK_CHANCE = 25                # DisturbSickChance % (vs SickChance bound 100)
DISTURB_LIMIT_CHECK_SICK = 5            # DisturbLimitCheckSick: the sick risk from the 5th disturb on
STARVE_WEIGHT_DEC = 1                   # ActivityWeightChange: starving sheds weight per lapse
# (the ENTIRE LifeDec family -- HungerMistake/Sick/Injury/WorseMalady/
# Fatigue/GeriatricFatigue/XAntibody LifeDec, live and dormant alike --
# left with the lifespan clock: DSprite mortality, Joel 2026-07-22.
# Neglect kills through the hazard tables below now, not through burns.)
# (the X-PROGRAM survival roulette constants left with their item -- the
# X-Program sample was cut with the strict-DSprite shelf 2026-07-17 and
# nothing rolled them since; dossier audit 2026-07-22.  The X-Antibody
# CHIP never carried the roulette.)
#                                         scaled to tuipet's ~84h: ~1.2% of life x total mistakes
# setEnergy: a drop INTO the red bills mood/obedience scaled by the depth
# (dec - newEnergy, i.e. 10 + |new| / 1 + |new|) and fatigues an uninjured pet
NEGATIVE_ENERGY_MOOD_DEC = 10           # NegativeEnergyMoodDec (base; depth added)
NEGATIVE_ENERGY_OBEDIENCE_DEC = 1       # NegativeEnergyObedienceDec (base; depth added)
BONUS_ATTRIBUTE_POWER = 1               # BonusAttributePower: a Happy pet's standard gain in its
#                                         favoured attribute lands doubled (set*Power; the bonus
#                                         rides only the battle incStats + training award paths --
#                                         the only canon callers of the bonus-carrying setters)
CALORIE_LAPSE_CHANGE = -1               # CalorieLapseChange (drain per lapse)
CALORIE_LAPSE_GERIATRIC_EXTRA = -3      # CalorieLapseChangeGeriatric (added when elderly)
# ⭐ A FULL BELLY IS ONE GAME-DAY (Joel 2026-07-25: "retune the hunger, do
# it" -- the care audit's F2 ruling).  The old value read "~1800s per
# hunger heart" and was consumed on a counter that ticks in GAME-MINUTES,
# so a heart took 1,800 of those (1.2 game-days) and a full belly FIVE --
# while ordinary neglect killed the pet at 3.5.  Hunger therefore never
# reached zero in a natural life: the hunger call, both "too hungry"
# refusals and the starvation death were all unreachable, and feeding was
# optional in a game about feeding.
#
# Tied to the day so it can never drift out of scale again: 4 hearts x
# (2 x CALORIE_LIMIT) lapses each == one DAY_MINUTES.  A heart is ~6 real
# minutes of play, a full belly one game-day -- the device's own rhythm,
# where you feed the thing a few times a day.
CALORIE_DECAY_SEC = DAY_MINUTES / (FULL_HUNGER * 2 * CALORIE_LIMIT)
# DVPet per-species physiology (calcNeedDecay: higher coefficient = SLOWER decay). ~85% of
# species share the modal values below, so only outliers diverge from tuipet's tuned pace.
REF_HUNGER_COEF = 60          # modal HungerDecayCoefficient
REF_STRENGTH_COEF = 50        # modal StrengthDecayCoefficient
REF_POOP_RATIO = 64           # modal PoopLimit / PoopLapseInc
# ⭐ THE SIBLING CLOCKS, PUT ON THE DAY TOO (Joel 2026-07-25: "retune the
# poop and effort clocks too", right after the hunger ruling).  Both were
# left on the old scale when the belly moved, and beside a one-game-day
# belly they were absurd: a pile every 1.9 GAME-DAYS and an effort heart
# every 2.1, so a pet produced half a mess a day and its gauge took eight
# days to empty.  Neither chore could become a rhythm, and the effort CALL
# -- which books a care mistake exactly like the hunger call -- could
# barely fire.
#
# POOP follows MEALS, the device's own coupling: four piles a game-day,
# the same cadence as the four hunger hearts, so eating and cleaning keep
# step.  EFFORT is deliberately gentler than the belly -- a drill is a
# bigger ask than a meal -- so its four hearts drain over ~1.3 game-days.
# Both are expressed against DAY_MINUTES so they cannot drift out of the
# day the way the belly did.
POOP_INTERVAL_BASE = DAY_MINUTES / 4          # 360: four piles a game-day
STRENGTH_DECAY_BASE = DAY_MINUTES / 3         # 480: the gauge empties in ~1.3 days

# ⭐ THE SPECIES SPREAD IS COMPRESSED (Joel 2026-07-25, option b: "keep the
# multiplier but compress its range" -- his report, "is th mon supposed to
# be pooping during sleep?").  The line above tunes the MODAL species, and
# the retune that set it verified "four piles a game-day" against exactly
# that species -- but the interval is `BASE * (poop_limit/poop_lapse) /
# REF_POOP_RATIO`, and the roster's lapse runs 1 / 2 / 8 / 16:
#
#     lapse  1 -> 1358 species ->  4 piles/game-day   (the number we tuned)
#     lapse  2 ->    7 species ->  8
#     lapse  8 ->  116 species -> 32
#     lapse 16 ->  116 species -> 64      <- a pile every 22 game-minutes
#
# So 232 species (14.5%) were left pooping 32-64 times a day.  That also
# defeated the SLEEP rule: canon holds the gauge at night and lets only a
# DESPERATE 2x gauge go, which for the modal pet is 12 game-hours (it never
# fires in a 10-hour night, measured) -- but at a 22-minute interval the
# threshold falls inside the night and a sleeper goes repeatedly.
#
# The canon multiplier is KEPT, because it is species character; its RANGE
# is compressed so the fastest species poops at most twice as often as the
# slowest, instead of sixteen times.  Ordering is preserved throughout.
POOP_SPREAD_RAW = 16          # the roster's real fastest-vs-modal rate ratio
POOP_SPREAD_CAP = 2           # ...compressed to this: at most ~8 piles a day

# DVPet discipline (config.csv, PhysicalState.praise / scold / checkPraiseScoldWindow).
# The pet flags a praise window after a good deed and a scold window after a bad one;
# praising/scolding while the matching window is open trains obedience, the mistimed
# response penalizes it.  Deltas verbatim; windows age on the mood-lapse cadence.
PRAISE_HIGH_DISP_MOOD_INC = 10          # PraiseHighDispositionMoodInc
PRAISE_LOW_DISP_MOOD_INC = 6            # PraiseLowDispositionMoodInc
PRAISE_NONCOMPLIANT_OBED_DEC = 2        # PraiseNoncompliantObedienceDec
CORRECT_PRAISE_OBED = {0: 3, 1: 5, -1: 1}   # CorrectPraiseObedienceInc[/High/Low]
PRAISE_SCOLD_MOOD_INC = 10              # PraiseScoldMoodInc (mis-praise during scold window)
PRAISE_SCOLD_ENTH = 5                   # PraiseScoldEnthusiasmChange (setEnthusiasm)
PRAISE_SCOLD_OBED_DEC = 8               # PraiseScoldObedienceDec
SCOLD_OBED_INC = 1                      # ScoldObedienceInc
SCOLD_HIGH_OBED_MOOD = 75               # ScoldHighObedienceMood threshold
SCOLD_HIGH_OBED_MOOD_DEC = 5            # ScoldHighObedienceMoodDec
SCOLD_LOW_OBED_MOOD_DEC = 15            # ScoldLowObedienceMoodDec
CORRECT_SCOLD_OBED = {0: 0, 1: 2, -1: 0}    # CorrectScoldObedienceInc[/High/Low]
CORRECT_SCOLD_ENTH = -1                 # CorrectScoldEnthusiasmChange
SCOLD_ENTH = -3                         # ScoldEnthusiasmChange (scold outside any window)
SCOLD_PRAISE_MOOD_DEC = 10              # ScoldPraiseMoodDec (mis-scold during praise window)
SCOLD_PRAISE_ENTH_DEC = 6              # ScoldPraiseEnthusiasmDec
SCOLD_PRAISE_OBED = {0: 1, 1: 3, -1: 0}     # ScoldPraiseObedienceInc[/High/Low]
PRAISE_WINDOW_MAX = 2                    # PraiseWindowMax (lapses the window stays open)
SCOLD_WINDOW_MAX = 2                     # ScoldWindowMax
PRAISE_FAIL_MOOD_PENALTY = 10            # PraiseFailMoodPenalty (a good deed unpraised)
PRAISE_FAIL_OBED_INC = 3                 # PraiseFailObedienceInc...
PRAISE_FAIL_OBED_DISPO_COEF = 1          # ...IncDispositionCoefficient (shaded by temperament)
SCOLD_FAIL_MOOD_INC = 10                 # ScoldFailMoodInc (it got away with it)
SCOLD_FAIL_OBED_PENALTY = 10             # ScoldFailObediencePenalty
# auto disciplineCall (checkDisciplineCall): the pet spontaneously acts up on the
# DisciplineCallMin cadence -- chance = randomChance(TargetChance+careAdjust,
# DisciplineCallChance-(ObedienceRefusalCap-obedience)); well-behaved grown pets are
# exempt.  DisciplineCallMin=59 game-min maps onto tuipet's ~59s mood-lapse (Joel's
# cadence-scaling choice), numbers verbatim.
DISCIPLINE_TARGET_CHANCE = 16            # DisciplineCallTargetChance
DISCIPLINE_CALL_CHANCE = 150             # DisciplineCallChance (randomChance bound base)
DISCIPLINE_TARGET_GLUTTON = 3            # DisciplineCallTargetGluttonChange
DISCIPLINE_TARGET_RESTLESS_HI = 3        # restless & under-exercised acts up more
DISCIPLINE_TARGET_RESTLESS_LO = -1
DISCIPLINE_OBEDIENCE_MAX = 50            # DisciplineCallObedienceMax (grown + obedient => exempt)
# the CALL itself (mood re-audit 2026-07-06): the tantrum is a care light with
# three exits -- the scold it demands (+2 obedience), any OTHER care placates it
# (obedience -10, a smug mood +5: it got its way), or it times out ignored
# (mood -25 and a missed day)
DISCIPLINE_CALL_SCOLD_OBED_INC = 2       # DisciplineCallScoldObedienceInc (the right answer)
DISCIPLINE_CALL_OBED_DEC = 10            # DisciplineCallObedienceDec (placated unscolded)
DISCIPLINE_CALL_MOOD_INC = 5             # DisciplineCallMoodInc (placated: it won)
DISCIPLINE_CALL_MOOD_PENALTY = 25        # DisciplineCallMoodPenalty (ignored)
DISCIPLINE_CALL_FAIL_MISSED_DAY = 1      # DisciplineCallFailMissedDayChange
MINUTES_TO_DISCIPLINE_PENALTY = 180.0    # _minutesToDisciplinePenalty 3 game-min

# DVPet AI Assistant (config.csv AutoCare*, PhysicalState.setAutoCare / doAutoCare /
# checkAutoCare / processAutoCarePrice).  A hired helper keeps house while you're
# away: awake it cleans filth, then feeds a starving pet (food 44), then a drained
# one (food 43); asleep it cleans, then dims a lit room.  Every visit bills the
# stage price AND costs bond -- mood -10,
# obedience -1, enthusiasm -1: hired care is not YOUR care.  An hourly retainer
# (or a visit) it cannot cover puts the assistant off duty.
AUTO_CARE_VISIT_PRICE = {"Egg": 50, "Fresh": 50, "InTraining": 100, "Rookie": 200,
                         "Champion": 400, "Ultimate": 800, "Mega": 1600}   # AutoCareStage*Price
AUTO_CARE_HOUR_PRICE = {"Egg": 0, "Fresh": 0, "InTraining": 0, "Rookie": 100,
                        "Champion": 200, "Ultimate": 400, "Mega": 800}
# AutoCareStage*HourPrice shipped a flat 100 for every adult stage; the
# retainer now scales with the stage like the visit fee does (half the visit
# ladder) -- a Mega's hired help is a real running cost, not pocket change
# (bit-sink design, Joel 2026-07-14)
AUTO_CARE_HUNGER_FOOD = 44               # AutoCareHungerFoodID (the AI Food Pill)
AUTO_CARE_STRENGTH_FOOD = 43             # AutoCareStrengthFoodID (the AI Supplement)
AUTO_CARE_MOOD = -10                     # _autoCareMoodChange
AUTO_CARE_OBEDIENCE = -1                 # _autoCareObedienceChange
AUTO_CARE_ENTHUSIASM = -1                # _autoCareEnthusiasmChange
AUTO_CARE_PAYMENT_MIN = 60               # _autoCarePaymentMin: the retainer bills hourly
AUTO_CARE_VISIT_SPACING = 3              # game-min between visits (DVPet spaces them via the
#                                          ASSISTANT_ANIM guard -- one helper on screen at a time)

# DVPet fatigue (config.csv, PhysicalState.fatigue / checkFatigueLapse): training to
# exhaustion can leave the pet fatigued for FatigueMin..FatigueMax game-minutes -- a big
# one-time mood/energy/spirit hit, and it cannot act until it has rested off the clock.
# isFatigued() == fatigue_length > 0; the length counts down in game-minutes (1 game-min
# ~= 1s under tuipet's clock).  Habitat-compatibility length mods and the lifespan hit
# are omitted (documented); deltas verbatim.
FATIGUE_MIN = 5                          # FatigueMin
FATIGUE_MAX = 60                         # FatigueMax
FATIGUE_MOOD_DEC = 50                    # FatigueMoodDec (the exhaustion hit)
FATIGUE_ENERGY_DEC = 1                   # FatigueEnergyDec
FATIGUE_ENTH_CHANGE = -1                 # FatigueEnthusiasmChange
ALREADY_FATIGUED_MOOD_DEC = 35           # alreadyFatiguedMoodDec (re-fatigued while down)
ALREADY_FATIGUED_ENTH_CHANGE = -1        # AlreadyFatiguedEnthusiasmChange
ALREADY_FATIGUED_OBED_DEC = 5            # alreadyFatiguedObedienceDec
ALREADY_FATIGUED_SICK_CHANCE = 1         # AlreadyFatiguedSickChance
FATIGUE_WORSE_SICK_CHANCE = 50           # FatigueWorseSickChance (a collapse can turn a cold critical)
GERIATRIC_FATIGUE_ENERGY_DEC = 1         # GeriatricFatigueEnergyDec (already-fatigued + old)
RANK_CHANGE_FATIGUE = 3                  # RankChangeFatigue (the hour + the drill sour on a collapse)
RANK_FATIGUE_FORCED = 2                  # RankChangeFatigueForced (it was pushed there)
OBEDIENCE_FATIGUE_FORCED = -3            # obedienceChangeFatigueForced
RANK_TRAIN_FAIL = 3                      # RankChangeTrainFail (a failed drill sours its attribute)
SPOIL_OBED_DEC = 10                      # SpoilObedienceDec (spoil(): it only obeys what it likes)
SPOIL_MOOD_INC = 10                      # SpoilMoodInc
DISLIKED_ATTR_OBEY = -20                 # DislikedAttributeObeyChange (the hated drill refuses more)
TRAIN_POWER_PER_HIT = 2     # attribute power per drill-hit (compression-scaled from DVPet's flat +1)
FATIGUE_CHANCE = 60                      # FatigueChance (% on an exhausting drill)

# DVPet sickness & injury durations (config.csv, PhysicalState.sicken / injure): an
# illness or injury lasts Min..MaxLength recovery lapses (SickLapseMin/InjLapseMin game-min
# each) and then clears on its own; onset costs mood/spirit.  Habitat-compat length mods
# omitted (documented); deltas verbatim.  Cured early by medicine as before.
SICK_MOOD_DEC = 50                       # SickMoodDec
INJ_MOOD_DEC = 50                        # InjuryMoodDec
SICK_ENTH_CHANGE = -1                    # SickEnthusiasmChange
INJ_ENTH_CHANGE = -1                     # InjuryEnthusiasmChange
MIN_SICK_LENGTH, MAX_SICK_LENGTH = 1, 10     # Min/MaxSickLength (recovery lapses)
MIN_INJ_LENGTH, MAX_INJ_LENGTH = 1, 12       # Min/MaxInjLength
SICK_LAPSE_MIN = 29                      # SickLapseMin (game-min per recovery lapse)
# DVPet GoodNutrition (config.csv): 3 macros accumulate from food and decay each lapse; all
# >= GoodNutritionMinimum gives a "well-fed" buff. Foods are specialised (Meat=protein,
# Fruit=vitamin, Veg=mineral), so good nutrition rewards a VARIED diet.
GOOD_NUTRITION_MIN = 16        # GoodNutritionMinimum
MAX_MACRO = 24                 # MaxProtein / MaxVitamin / MaxMineral
NUTRITION_LAPSE_CHANGE = -3    # NutritionLapseChange (decay per lapse)
NUTRITION_LAPSE_SEC = 600.0    # tuipet cadence for macro decay (real-time adaptation)
GOOD_NUTR_RECOVERY_MULT = 2.0  # GoodNutrition{Sick,Inj,Fatigue}LapseChange=-1 -> ~2x recovery
# (GoodNutritionLifespanDecCoefficient left with the lifespan clock -- it
# never had a consumer here; DSprite mortality 2026-07-22)
INJ_LAPSE_MIN = 29                       # InjLapseMin

# DVPet injury worsening + vitamins (config.csv, calcWorse{Exercise,Battle}Inj /
# worsenedInjury / feedVitamin): pushing an injured pet (training/battling) can worsen the
# injury -- extending it and costing mood/obedience/energy/spirit -- at a chance set by
# weight and whether a vitamin is active.  Chances are factor/WorseInjuryChance.  No shipped
# item is flagged Vitamin in items.csv, so has_vitamin() defaults false (the no-vitamin
# rates apply); the grant path (feed_vitamin / a "vitamin" consumable flag) is wired and
# ready.  Values verbatim from config.csv column 1; WorseInjuryLifeDec lifespan hit omitted.
WORSE_INJ_CHANCE = 100                   # WorseInjuryChance / WorseBattleInjuryChance (bound)
WORSE_INJ_EXERCISE = {"bad_nv": 10, "good_nv": 1, "good_v": 0, "bad_v": 5}   # WorseInjury*
WORSE_INJ_BATTLE = {"bad_nv": 15, "good_nv": 5, "good_v": 0, "bad_v": 5}     # WorseBattleInjury*
# the WEAK tables (taste/rank audit 2026-07-06): drilling the species'
# ATTRIBUTE AVERSION (a fixed seed -- the aversion never drifts) hurts more
INJ_WEAK_EXERCISE = {"bad_nv": 20, "good_nv": 5, "good_v": 1, "bad_v": 10}   # WeakInjury*
WORSE_INJ_WEAK = {"bad_nv": 15, "good_nv": 5, "good_v": 1, "bad_v": 5}       # WorseWeakInjury*
# FRESH injuries (sickness/injury audit 2026-07-06): the same weight x vitamin
# matrix vs a 1000 bound, plus a shared additive term -- geriatric/bad-age,
# fatigue x coefficient, negative energy x coefficient, habitat compatibility
# (+-1/axis) -- and battles pad +50 on a LOSS.  The old ports ("overweight ->
# 50%", "loss -> 30%") were paraphrases; canon's baseline is ~0.1-1%.
INJ_CHANCE = 1000                        # InjuryChance (exercise bound)
INJ_EXERCISE = {"bad_nv": 10, "good_nv": 1, "good_v": 0, "bad_v": 5}   # Injury*
INJ_GERIATRIC = 10                       # InjuryGeriatricFactor
INJ_FATIGUE_COEF = 10                    # InjuryFatigueCoefficient (x FatigueMod)
INJ_NEG_ENERGY_COEF = 0.5                # InjuryNegativeEnergyCoefficient
BATTLE_INJ_CHANCE = 1000                 # BattleInjuryChance
INJ_BATTLE = {"bad_nv": 100, "good_nv": 3, "good_v": 0, "bad_v": 25}   # BattleInjury*
BATTLE_INJ_BAD_AGE = 10                  # BattleInjuryBadAgeFactor (elder OR baby)
BATTLE_INJ_LOSS = 50                     # BattleInjuryWonFactor (added on a LOSS)
BATTLE_INJ_FATIGUE_COEF = 10             # BattleInjuryFatigueCoefficient
BATTLE_INJ_NEG_ENERGY_COEF = 1.0         # BattleInjuryNegativeEnergyCoefficient
FATIGUE_MOD = 10                         # FatigueMod
WORSE_INJ_GERIATRIC = 10                 # WorseInjuryGeriatricFactor
WORSE_BATTLE_INJ_BAD_AGE = 10            # WorseBattleInjuryBadAgeFactor
WORSE_BATTLE_INJ_LOSS = 5                # WorseBattleInjuryWonFactor (on a LOSS)
WORSE_INJ_NEG_ENERGY_COEF = 1.0          # WorseInjuryNegativeEnergyCoefficient (battle same)
INJURY_ENERGY_DEC = 1                    # InjuryEnergyDec (a fresh injury saps a bar)
OBED_INJ_FORCED = -5                     # ObedienceChangeInjuryForced (complied + hurt)
OBED_INJ_BATTLE_WON = -2                 # ObedienceChangeInjuryBattleWonForced
OBED_INJ_BATTLE_LOST = -5                # ObedienceChangeInjuryBattleLostForced
# checkSick/checkWorseSick BOUNDS: the home's compatibility shifts the sick
# bound (+-5/axis; a compatible home = safer), old age thins both by 25, and
# fatigue pads a worse-sick TARGET by FatigueMod
SICK_CHANCE_BOUND = 100                  # SickChance
SICK_COMPAT_CHANGE = 5                   # Compatible*SickChanceChange
SICK_GERIATRIC_FACTOR = 25               # SickGeriatricFactor
WORSE_SICK_BOUND = 100                   # WorseSickChance
WORSE_SICK_GERIATRIC = 25                # WorseSickGeriatricFactor
INTOL_WORSE_SICK_CHANCE = 50             # IntolerantFoodWorseSickChance
# incMistake's sickness risks (flagged in the mood arc, closed here): filth
# rolls per pile with a misery pad (|mood| x 0.1 when Unhappy/Depressed), and
# ANY mistake while fatigued adds a 1/1 whisper.  The 50/50 MistakeFilth*
# pair keys on poopCall -- PROVABLY DEAD in the shipped config (the filth
# array holds 6, MistakeFilthLimit is 7) -- kept as documentation only.
MISTAKE_FILTH_WORSE = 50                 # MistakeFilthWorseSickChance (dead: poopCall)
MISTAKE_FILTH_SICK = 50                  # MistakeFilthSickChance (dead: poopCall)
MISTAKE_LOW_FILTH_WORSE = 5              # MistakeLowFilthWorseSickChance (x piles)
MISTAKE_LOW_FILTH_SICK = 1               # MistakeLowFilthSickChance (x piles)
MISTAKE_FILTH_MOOD_COEF = 0.1            # MistakeFilthSickChanceMoodCoefficient
ANY_MISTAKE_FATIGUED = 1                 # AnyMistakeWhileFatigued{,Worse}SickChance
SICK_LAPSE_PENALTY_BM = 48               # SickLapsePenaltyBM: an awake sick pet's gauge races
SICK_NUTRITION_CHANGE = -1               # SickNutritionChange (per awake sick lapse)
WORSE_MALADY_MOOD_DEC = -35              # worseMaladyMoodDec
WORSE_MALADY_OBED_DEC = -10              # worseMaladyObedienceDec
WORSE_INJ_ENERGY_DEC = 1                 # WorseInjuryEnergyDec
WORSE_INJ_ENTH_CHANGE = -1               # WorseInjuryEnthusiasmChange
VITAMIN_HOURS = 60                       # VitaminHours (game-min of injury-worsening protection)
CURED_MOOD_BONUS = 75                    # CuredMoodBonus (divided by Max{Sick,Inj}Length per treatment)
CURED_OBED_BONUS = 25                    # CuredObedienceBonus
# (BadMedLifeDec + BadVitaminLifeDec left with the lifespan clock --
# DSprite mortality 2026-07-22; they had no live consumer since the
# medicine slim anyway)
BAD_MED_BM_INC = 6                       # BadMedBMInc (bowel gauge lurch)
BAD_VITAMIN_MOOD_DEC = 8                 # BadVitaminMoodDec
BAD_VITAMIN_BM_INC = 2                   # BadVitaminBMInc
VITAMIN_WORSE_SICK_CHANCE = 1            # VitaminWorseSickChance %
VITAMIN_OVERFED_SICK_CHANCE = 50         # VitaminOverfedSickChance (RefuseChance-bounded roll)
MEDICINE_HOURS = 60                      # MedicineHours (game-min the medicine indicator lingers, config.csv)
BANDAGE_HOURS = 60                       # BandageHours (game-min the bandage indicator lingers, config.csv)

# X-Antibody: a special state that unlocks evolution into the "X" Monster
# forms.  BINARY since the X slim (BASIC VPET 2026-07-16): None or Permanent
# -- the Temporary protoform (hour decay) and XProgram lost their granters
# with the DVPet item catalog.  Acquired by the shop chip or a Natural X
# evolution.
# BINARY since the X slim (BASIC VPET 2026-07-16): None or Permanent.  The
# Temporary protoform (hour-decay) lost its only granter with the DVPet
# item catalog and left; XProgram likewise.

# Personality: DVPet's 3x3x3 table over (disposition, glutton, restless), each in
# {-1 low, 0 neutral, +1 high}.  Ported verbatim from PhysicalState.checkPersonality.
_PERSONALITY = {
    (0, 0): ("Dócil", "Agitado", "Calm"),
    (0, 1): ("Glutão", "Hasty", "Lazy"),
    (0, -1): ("Contente", "Inquieto", "Stoic"),
    (1, 0): ("Alegre", "Hyper", "Despreocupado"),
    (1, 1): ("Eager", "Brincalhão", "Preguiçoso"),
    (1, -1): ("Generoso", "Antsy", "Tranquilo"),
    (-1, 0): ("Sério", "Ansioso", "Apático"),
    (-1, 1): ("Egoísta", "Travesso", "Letárgico"),
    (-1, -1): ("Tolerante", "Indômito", "Insensível"),
}

# Day/night: the world runs on an accelerated clock. One full DAY_LENGTH-second
# cycle runs dawn -> day -> dusk -> night. Night makes the pet sleepy: kept awake
# it tires and sulks faster, while rest is deepest then.
DAY_LENGTH = 1440.0           # 24 min per day/night cycle




ONLINE_BITS = {"win": 200, "draw": 150, "loss": 100}


def online_reward(won: bool, draw: bool = False, now: Optional[float] = None) -> int:
    """The online purse (0.5 BATTLE 2026-07-17): win 200 / draw 150 /
    loss 100, weekend x1.5 -- PvP pays bits, never training."""
    base = ONLINE_BITS["draw" if draw else ("win" if won else "loss")]
    return int(base * weekend_bonus(now))




# every name (underscored included) rides the star-import back into pet.py
# and into each mixin module -- the tier-5 name-resolution contract
