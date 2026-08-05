from .core import *
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
# --- food taste (DVPet Taste<Food> + Rank + config.csv) ---
RANK_LIMIT, RANK_MIN = 200, -200       # config RankLimit / RankMinimum
RANK_CHANGE_FOOD = 1                    # config RankChangeFood (per meal)
RANK_CHANGE_SICK = 5                    # RankChangeSick: a bad dose sours the taste...
RANK_CHANGE_SICK_FORCED = 5             # RankChangeSickForced: ...more so when force-fed
RANK_PREF_INC = 2                       # config RankChangeSpeciesPreferenceInc (species like/dislike bias)
RANK_DISLIKED = -2                      # config RankChangeDisliked
RANK_AFTER_FAV = 20                     # config RankChangeAfterFav (decay other ranks toward 0)
# the ATTRIBUTE taste ledger + the rank-event deltas (taste/rank audit
# 2026-07-06 -- the standing "rank system unported" deferral closed).  Young
# pets form tastes faster: the per-event base is stage-scaled.
RANK_CHANGE_ATTR = 1                    # RankChangeAttribute (per drill)
RANK_STAGE_INC = {"Fresh": 3, "InTraining": 2, "Rookie": 1}   # RankChangeStage{1,2,3}Inc
RANK_TRAIN_FORCED = 2                   # RankChangeTrainForced (forced training sours it)
RANK_INJ_BATTLE_WON = 1                 # RankChangeInjuryBattleWon (hurt by that attribute...)
RANK_INJ_BATTLE_LOST = 5                # RankChangeInjuryBattleLost (...and beaten by it)
RANK_BAD_FOOD_FORCED = 3                # RankChangeBadFoodForced (forced the disliked meal)
RANK_FOOD_FORCED = 1                    # RankChangeFoodForced (any forced meal grates)
RANK_INTOL_FORCED = 5                   # RankChangeIntolerantForced
RANK_SICK_FORCED = 5                    # RankChangeSickForced (a forced meal that sickened)
RANK_TIME_SICK = 5                      # RankChangeSick/Injury: misery sours the HOUR too
RANK_WORSE_INJ_ATTR = 5                 # RankChangeInjury: a worsening sours the attr that did it
RANK_WORSE_INJ_FORCED = 5               # RankChangeInjuryForced (it was pushed into it)
NONE_TRAIN_MOOD_RANK = -1               # NoneTrainingAttributeMoodRankChange (the HP drill)
# the personality TRACKER (randPersonalityTraits seeds / personalityTracker /
# randOnChampion): childhood care -- energy kept high, weight kept healthy,
# mood kept happy -- is tallied through Fresh/InTraining/Rookie and RE-ROLLS
# the temperament at the Champion evolution (threshold +-42)
PCHAMP_RANK = 42                        # PersonalityChampRandom{High,Low}*Rank
PCHAMP_HI_ENERGY = 0.75                 # PersonalityChampRandomHighEnergyCoefficient
PCHAMP_LO_ENERGY = 0.25                 # PersonalityChampRandomLowEnergyCoefficient
EXERCISE_DISLIKED_ATTR_ENTH = -3        # ExerciseDislikedAttributeEnthusiasmChange
ENTH_DISLIKE_FORCED = -1                # EnthusiasmChangeDislikeForced
FAV_FOOD_MOOD = 10                      # config FavFoodMoodInc
FOOD_MOOD = 2                           # config FoodMoodInc (neutral food)
FAV_FOOD_ENTH = 1                       # config FavFoodEnthusiasmInc
GLUTTON_FEED_MOOD = 1                   # GluttonFeedMoodChange: a glutton relishes any meal
NOT_GLUTTON_FEED_MOOD = -1              # NotGluttonFeedMoodChange: a picky eater resents each
ENTH_BAD_FOOD_FORCED = -1               # EnthusiasmChangeBadFoodForced (disliked + full + forced)
DISLIKED_FOOD_OBEDIENCE = -1            # config DislikedFoodObedienceChange
INTOL_FOOD_SICK_CHANCE = 50            # config IntolerantFoodSickChance (per roll, x2 rolls)

# DVPet poop / filth (config.csv, PhysicalState.poop / poopWaitMoodCheck).  A bowel
# movement bumps mood, sheds a little weight and drops a pile of a size set by the
# Monster's base weight; an uncleaned mess then nags the mood until it is cleaned.
# THE BODY TELLS' gate.  ⚠ E4 AUDIT 2026-07-23: poopdance and yawn have
# been firing since v0.2.337 from app.py's own idle roll (gated on this
# fraction and on pet.near_bedtime(), a helper written for exactly that).
# v0.5.211 "restored" them a SECOND time because the survey grepped for
# literal start_fx("name") and that call site passes a VARIABLE
# (random.choice(specials)) -- the same miss that hid `losing`.  The
# duplicate was removed; this constant survives only to name the
# magic number the original was carrying inline.
POOPDANCE_AT = 0.8                      # fraction of the bowel gauge
POOP_MOOD_INC = 10                      # PoopMoodInc (relief)
CLEAN_MOOD_INC = 6                      # CleanMoodInc
CLEAN_OBED_INC = {0: 1, 1: 2, -1: 0}    # CleanObedienceInc / HighDisposition / LowDisposition
POOP_WEIGHT_DEC_COEF = 0.1             # PoopWeightDecCoefficient
POOP_WEIGHT_LIMIT = 4                   # PoopWeightLimit (max weight lost per poop)
# setWeight (weight audit 2026-07-06): the body clamps HARD at baseWeight +-
# round(baseWeight x WeightLimitMultiple) -- wider than the +-0.5 Over/Under
# tier band -- and hitting either wall stings (weightLimitPenalty: mood -10,
# obedience -0 at difficulty 0, spirit -1)
WEIGHT_LIMIT_MULTIPLE = 0.75            # WeightLimitMultiple
WEIGHT_LIMIT_MOOD_PENALTY = 10          # WeightLimitMoodPenalty
WEIGHT_LIMIT_OBED_PENALTY = 0           # WeightLimitObediencePenalty (difficulty 0: no-op)
WEIGHT_LIMIT_ENTH_PENALTY = 1           # WeightLimitEnthusiasmPenalty
ABOVE_MAX_CAL_BM = 1                    # AboveMaxCaloriesBMGaugeChange: calorie overflow
#                                         while rising hastens the poop (setCalories)
# (DVPet toilet training -- MinToiletUsesToTrain / the SelfToilet branch and
# its stage/obedience gates -- left with the staple props: strict-DSprite
# items, 2026-07-17)
POOP_INC_WEIGHT_FACTOR = 40            # PoopIncWeightFactor -> size 3 at/above
POOP_INC_WEIGHT_FACTOR_SMALL = 15      # PoopIncWeightFactorSmall -> size 1 at/below
POOP_WAIT_MOOD = -1                     # PoopWaitMoodChange (the HELD gauge nags)
LARGE_POOP_WAIT_MOOD = -2               # LargePoopWaitMoodChange (a desperate gauge nags more)
# ⛔ CLOCK-UNIT LAW: canon cadences are in GAME MINUTES and tuipet's clock maps
# one game minute onto ONE REAL SECOND (DAY_LENGTH 1440s = 1440 game min).  A
# `*Min=N` constant therefore ports to N REAL SECONDS -- never N x 60.  The six
# constants below were all converted with REAL minutes (cadence audit
# 2026-07-14; the same error already cost us TEMP_RATE and WEATHER_CHECK_SEC).
FILTH_MOOD_DEC_MIN = 5.0                # FilthMoodDecMin 5 game-min (was 300.0 = 5 game HOURS)
# THE STARVATION CLOCK, on the body's own scale (care audit 2026-07-25).
# 12 GAME-hours with an empty belly, awake -- the number its comment always
# claimed.  It was written `12 * 3600`, a real-seconds shape against a
# counter that accumulates dt in GAME-MINUTES, which asked for thirty game
# days of unbroken starvation and so could never fire.  Same rescale the
# filth-sickness bound took, one line below.
STARVE_DEATH_MIN = 12 * 60              # 720 game-minutes = 12 game-hours
FILTH_SICK_BOUND = 200                  # FilthSickChanceBound 12000 real-min -> /60 game scale
FILTH_SICK_CHANCE = 1                   # FilthSickChance (x piles, per game-min)
FILTH_WORSE_CHANCE = 20                 # FilthWorseSickChance (x piles, already sick)
