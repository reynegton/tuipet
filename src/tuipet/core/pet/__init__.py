"""DVPet game model: a single virtual pet, its stats, and care logic.

Tier-5 split (2026-07-17): the constants + pure helpers live in petbase
(star-imported back, so `from .pet import X` never moved).
"""
from __future__ import annotations
import datetime
import os
import random
import time
from tuipet.i18n.translator import t # noqa: F401
from dataclasses import dataclass, field as _dcf
import tuipet.data.loaders.data as data    # noqa: F401
import tuipet.core.shop as shop    # noqa: F401
import tuipet.core.egg as egg_mod    # noqa: F401
import tuipet.core.evolution as evolution    # noqa: F401
import tuipet.core.lines as lines_mod    # noqa: F401
from tuipet.core.petbase import *    # noqa: F401,F403  (the constant bed; __all__ carries _names)
from tuipet.core.petbattle import BattleMixin
from tuipet.core.petbody import BodyMixin
from tuipet.core.petcare import CareMixin
from tuipet.core.petdna import DnaMixin

import tuipet.core.pet.misc as misc
import tuipet.core.pet.memory_state as memory_state
import tuipet.core.pet.intervals as intervals
import tuipet.core.pet.traits as traits
import tuipet.core.pet.conditions as conditions
import tuipet.core.pet.evolution_state as evolution_state
import tuipet.core.pet.stats as stats

@dataclass
class Pet(CareMixin, DnaMixin, BattleMixin, BodyMixin):
    num: int
    name: str = ""
    stage: str = ""
    attribute: str = ""
    age_seconds: float = 0.0
    stage_seconds: float = 0.0      # time spent in the current stage
    hunger: int = 4                 # hearts 0..4 (4 = full); FullHunger=4
    calories: int = 0               # DVPet calorie buffer; resetToEgg StartingCalories=0
    strength: int = 4               # effort hearts 0..4; resetToEgg sets FullStrength(4)
    energy: int = 24                # DVPet energy, -max_energy..+max_energy (full at max_energy)
    max_energy: int = 24            # per-Monster (monster.csv MaxEnergy)
    enthusiasm: int = 0             # DVPet spirit, MinEnthusiasm..MaxEnthusiasm (separate from mood)
    weight: int = 20
    poop: int = 0                   # pile count == DVPet countFilth()
    poop_sizes: list = _dcf(default_factory=list)   # per-pile size 1..4 (DVPet _filth bytes)
    asleep: bool = False
    lights: bool = True             # DVPet _lights: room-light toggle, SEPARATE from sleep
    depressed: bool = False         # DVPet _currentMood==Depressed: a sticky STATE entered and
    #                                 left by checkDepressed's rolls, not a mood threshold
    auto_care: bool = False         # DVPet _autoCare: the hired AI Assistant is on duty
    assistant_num: int = -1         # DVPet _assistantID: WHICH Monster answered the contract
    care_mistakes: int = 0
    dna_owned: dict = _dcf(default_factory=lambda: {f: 0 for f in data.DNA_FIELDS})    # banked
    dna_applied: dict = _dcf(default_factory=lambda: {f: 0 for f in data.DNA_FIELDS})  # charged
    dna_wager_pending: int = 0      # a paid mash in flight -- settled spoiled on relaunch (S2)
    food_ranks: dict = _dcf(default_factory=lambda: {c: 0 for c in data.FOOD_CATEGORIES})
    # the ATTRIBUTE taste ledger (taste/rank audit 2026-07-06): drills warm the
    # pet to an attribute, injuries and forced training sour it; a rank at
    # +-RankLimit becomes the emergent favourite/disliked ("" = none yet)
    attr_ranks: dict = _dcf(default_factory=lambda: {"Vaccine": 0, "Data": 0, "Virus": 0})
    saved_hit_type: str = "normal"  # the trained battle form (0.5 drill: mega/normal/miss)
    total_trainings: int = 0        # lifetime drills (the 0.5 hit formula's experience term)
    exp: int = 0                    # DMX battle experience (humulos canon: defeating an
    #                                 enemy pays experience; feeds the LV line gates)
    favorite_attr: str = ""
    disliked_attr: str = ""
    # the personality tracker (childhood care -> the Champion temperament)
    energy_rank: int = 0
    weight_rank: int = 0
    mood_rank: int = 0
    food_eaten: dict = _dcf(default_factory=lambda: {c: 0 for c in data.FOOD_CATEGORIES})
    favorite_food: str = ""             # emerges at rank +RankLimit
    disliked_food: str = ""             # emerges at rank -RankLimit
    wins: int = 0
    hatching: bool = False
    vaccine: int = 0
    data_power: int = 0
    virus: int = 0
    # care-quality counters that drive evolution (mirror DVPet's tracked stats)
    overeat: int = 0
    injuries: int = 0
    disturb: int = 0
    obedience: int = FRESH_OBEDIENCE   # noqa: F405  born TRUSTING (canon FreshObedience).
    #                                 Was 0 -- harmless while the meter was a
    #                                 no-op, but under D3 a bare Pet() would be
    #                                 born NEGLECTED and start refusing commands.
    #                                 (Loaded saves keep their own value; the
    #                                 dead-meter heal reads the explicit 0.)
    # personality traits: fixed at hatch (DVPet randPersonalityTraits), each in {-1,0,+1}.
    # Distinct from the overeat/disturb care counters, which drive evolution.
    disposition: int = 0
    glutton: int = 0
    restless: int = 0
    exercise_today: int = 0         # DVPet _exercise: drills done today (resets daily)
    # discipline windows (DVPet _praise/_scold + their aging windows)
    praise_flag: bool = False       # a good deed is awaiting praise
    scold_flag: bool = False        # a bad deed is awaiting a scolding
    praise_window: int = 0          # lapses since the praise flag opened
    scold_window: int = 0
    compliance: bool = False        # DVPet _compliance (resetToEgg starts false; a fair scold earns it)
    refused: bool = False           # DVPet _refused: the last command was blown off (one-shot)
    discipline_call: bool = False   # DVPet _disciplineCall: a tantrum begging to be disciplined
    fatigue_length: float = 0.0     # DVPet _fatigueLength (game-min remaining; >0 == fatigued)
    inj_length: float = 0.0         # DVPet _injLength (game-min until the injury heals)
    obed_v: int = 0                 # manners-heal marker: 0 = a save from the era when
    #                                 _set_obedience was a NO-OP (see persistence)
    vitamin_lapse: float = 0.0      # DVPet _vitaminLapse (game-min of injury-worsening protection)
    bandage_lapse: float = 0.0      # DVPet _bandageLapse: bandage indicator after mending an injury (getBandage)
    nutr_protein: int = 0           # DVPet _protein (0..MaxProtein), from a meaty diet
    nutr_mineral: int = 0           # DVPet _mineral, from vegetables
    nutr_vitamin: int = 0           # DVPet _vitamin, from fruit
    battles: int = 0
    levels_fought: list = _dcf(default_factory=list)  # opponent levels beaten this stage (DVPet _levelsFought)
    # ---- evolution lines (LINES_SPEC.md): the legible bracket engine ----
    line_id: str = ""               # hatched-from line; "" = corpus fuzzy engine
    stage_trainings: int = 0        # drills attempted this stage (every attempt counts; Pen20)
    data_trainings: int = 0         # lifetime VERSUS (data) sessions -- the DM20 manual's
    #                                 cheat chart cycles on THESE alone (a vaccine mash must
    #                                 not shift the printed pattern; audit 2026-07-13)
    stage_battles: int = 0          # battles fought this stage
    battle_log: list = _dcf(default_factory=list)   # last-15 results 1/0 (persists across evolution; Pen20)
    mega_kills: int = 0             # lifetime Ultimate/Mega-class foes beaten (DMX KO6 gate)
    dp: int = 0                     # Pen20 DP meter 0..4: full to jogress; 3h sleep refills it
    bits: int = 0
    trophies: int = 0
    trophies_won: dict = _dcf(default_factory=dict)   # trophy id -> day-won label (the trophy room)
    # ---- the NAMED RIVAL (Joel 2026-07-26: "build the named rival too") ----
    # rides the pet save on purpose: the feud lives and dies with the
    # generation — a new egg meets a new rival with a clean slate
    rival_name: str = ""            # the recurring tamer; empty until the first challenge
    rival_line: str = ""            # its pet's line id — the form tracks OUR stage
    rival_wins: int = 0             # head-to-head this generation: our wins...
    rival_losses: int = 0           # ...and theirs
    # the FUTON (item expansion 2026-07-26): the next daytime doze holds to
    # a FULL tank instead of half; cleared when that doze's wake lands
    futon_doze: bool = False
    # ---- home shop (PhysicalState _homeFoodShop/_homeItemShop/_restock) ----
    shop_food: list = _dcf(default_factory=list)    # rolled food slots {key, stock, sale}
    shop_item: list = _dcf(default_factory=list)    # rolled item slots
    shop_day: int = -1                              # game day of the current roster (dailyChange)
    shop_restock: int = 0                           # banked restock credits (max RestockMax)
    shop_restock_t: float = 0.0                     # seconds toward the next credit roll
    # sleep cycle (PhysicalState _sleepLapse/_sleepLimit/_awakeLapse/_awakeLimit/_nap)
    sleep_lapse: float = 0.0        # pressure toward the next sleep (accrues awake)
    sleep_limit: float = DAY_MINUTES - MIN_AWAKE_LIMIT   # pressure cap for this cycle
    awake_lapse: float = 0.0        # minutes slept so far
    awake_limit: float = MIN_AWAKE_LIMIT                 # minutes of sleep owed
    nap: bool = False               # a lights-out nap (shallow; lights-on wakes it)
    item_interest: int = 0          # _itemInterest: toy boredom 0..5 (decays over time)
    # missed-day / birthday (PhysicalState _mistakeDay / _dailyMoodRecord / _bonus)
    mistake_day: int = 0            # today's care slips (resets each birthday)
    daily_mood: dict = _dcf(default_factory=lambda: {"Feliz": 0, "Neutro": 0, "Triste": 0, "Deprimido": 0})
    last_birthday: int = 0          # last celebrated age-day
    evol_bonus: int = 0             # _bonus: birthday/win-rate credit fed into evolution odds
    memory: dict = _dcf(default_factory=dict)   # held inheritance data (item 32 payload)
    wild_memories: list = _dcf(default_factory=list)  # FOUND-chip payloads (queue; 2026-07-24)
    birthday_note: str = ""         # transient: the HUD's birthday announcement
    saved_from_death: int = 0       # _savedFromDeath: each rescue raises the next bar
    death_banked: bool = False      # this death's etch/seed ceremony already ran
    #                                 (rides the save: a quit mid-dying-beat used
    #                                 to disinherit the heir; audit 2026-07-19)
    # long-horizon clocks (persisted: losing these on reload forgave starvation,
    # wiped the bowel gauge and re-armed once-per-night mistakes -- audit 2026-07)
    _starve_t: float = 0.0          # the 12h starvation death clock
    _poop_t: float = 0.0            # the bowel gauge (written as durable state by meals)
    _filth_t: float = 0.0           # filth-mistake grace / post-mistake postpone
    _lights_t: float = 0.0          # lights-on sleep mistake (float(-inf) = once/night latch)
    _cal_t: float = 0.0             # calorie/hunger lapse accumulator
    _str_t: float = 0.0             # effort-decay accumulator
    # the four that escaped the lesson above (audit F8, fixed 2026-07-20):
    # quit-cycling billed call mistakes up to 7x faster (or forgave a 599s
    # window), never billed the assistant retainer, and shed DP progress
    _hunger_call_t: float = 0.0     # hunger-call answer window / post-mistake postpone
    _str_call_t: float = 0.0        # effort-call answer window / post-mistake postpone
    _ac_pay: float = 0.0            # the assistant's hourly retainer accumulator
    _dp_t: float = 0.0              # sleep DP-refill accumulator
    _exercise_day: int = -1         # daily exercise counter's day stamp
    # the FIFTH that escaped it (item sweep 2026-07-24): the bedtime grace
    # clock -- a disturb's postpone AND the whole effect of a 300b Caffeine
    # Pill, which for a line pet (every hatch) rides this and nothing else.
    # Held as a bare instance attribute, it evaporated on the next load, so
    # the pill you bought was refunded to the void by a quit.
    _bed_postpone_t: float = 0.0    # bedtime grace: disturb postpone / caffeine
    # the Sleep Pill's room switch, held until its eat show has played (bug
    # report 2026-07-26, v0.5.287).  Transient by design: it lives for the
    # length of one animation, so it is NOT saved -- a quit mid-show leaves a
    # sleeper under a lit room, which the next lights press (or bedtime) fixes.
    pending_lights_out: bool = False
    # THE PRIZE REVEAL (Joel 2026-07-28: "shouldnt we see the prize
    # sprite? not just an announcement?").  A surprise-opener (capsule,
    # chocolate egg) parks its prize key here; the app's fx-end hook hands
    # it to the following cheer, which holds the sprite beside the pet.
    pending_prize: str = ""
    free_style: bool = False        # _isFree: Battle Style toggle (Free vs Orders)
    gift: str = ""                  # pending gift-call present (consumable key; "" = none)
    # the DSprite item timers (BASIC VPET 2026-07-16, cloned from v0.4.x):
    full_until: float = 0.0         # premium meat satiety (game-seconds, world clock)
    auto_clean_until: float = 0.0   # smart potty (game-seconds)
    evo_blocked: bool = False       # anti-evo chip toggle
    gift_t: float = 0.0             # seconds toward the next GiftChanceMin roll
    # ---- home tournament (PhysicalState _trophySchedule/_foughtTrophiesToday) ----
    tourney_schedule: list = _dcf(default_factory=list)   # 24 hourly trophy ids (dailyChange re-roll)
    tourney_day: int = -1                                  # game day of the schedule
    fought_today: list = _dcf(default_factory=list)        # trophy ids fought today (SameDayRetry exempt)
    fought_hours: list = _dcf(default_factory=list)       # game hours whose cup has been RUN today
    #                                                       (Joel 2026-07-13: one entry per cup-hour)
    tourney_alarm: int = -1         # _tourneyAlarm: trophy id to be called for (-1 = unset)
    tourney_real: int = -1          # real-date ordinal of the schedule (cadence 2026-07-17)
    featured_day: int = -1          # real-date ordinal the featured cup last ran
    tourney_alert: bool = False     # TournamentAlert: the call is ringing (this hour only)
    full_health: int = STARTING_HEALTH_POINTS   # _fullHealthPoints: TRAINED battle HP
    perfect_wins: int = 0           # _perfectWins: HP-drill wins toward the next +1 HP
    # (the old adventure fields -- adv_map/adv_zone/adv_seek/adv_loc -- left
    # with the world layer; BASIC VPET 2026-07-16.  The adventure REBUILD
    # 2026-07-20 tracks progression with ONE field: the COUNT of zones
    # conquered -- a ROAD position under the difficulty sort, not a ZONES
    # index (the frontier zone is PROGRESSION[adv_progress]; truthed
    # 2026-07-25).  Auto-persisted (asdict / fields(Pet)); old saves
    # default to 0.)
    adv_progress: int = 0
    # THE RIVAL (cup fun arc 2026-07-21): the mon that last ELIMINATED you
    # from a cup bracket -- it re-seeds into future brackets its tier fits,
    # until revenge settles the grudge.  Real losses only, never forfeits.
    rival_num: int = -1
    egg_type: int = 0
    bg_pick: str = ""               # picked home scene ("" = follow the egg; E picker 2026-07-17)
    generation: int = 1
    dead: bool = False
    sick: bool = False              # the DSprite flag (clone-style, 2026-07-17): pill-cured only
    injured: bool = False           # the SECOND ailment, RESTORED (canon restoration
    #                                 2026-07-23, Joel "whatever is canon bring back"):
    #                                 battles wound; the Bandage cures (one dose,
    #                                 the pill's grammar); injuries counts lifetime
    death_cause: str = ""           # what took it (memorial epitaph, audit 2026-07-05)
    world_seconds: float = 0.0
    # (the weather/temperature block lived here -- temp, day_temp, temp_goal,
    # weather -- removed whole with the weather system; BASIC VPET 2026-07-16)
    field: str = ""
    # (the habitat block lived here -- habitat, home_habitat, habitats,
    # habitat_record -- removed whole with the habitat system; the home scene
    # is wired to egg_type now.  BASIC VPET 2026-07-16)
    x_antibody: str = "None"
    inventory: dict = _dcf(default_factory=dict)
    # the day's town-counter purchases {"day": ordinal, "<tid>:<key>": n} --
    # the authored maxStock caps a town's daily take (shops arc 2026-07-21:
    # DVPet's 375b town steak vs the 2000b catalog would otherwise be a
    # money printer through the demand resale)
    town_bought: dict = _dcf(default_factory=dict)
    # the day's claimed REPLAY boss bounties {"day": ordinal, "<zi>": 1} --
    # a conquered zone's boss pays its veteran bounty once per real day
    # (anti-printer, adventure audit 2026-07-25: the road was the one
    # unrationed earner -- the festival x streak x veteran stack paid
    # ~18,000b per repeatable 8-minute run, ten times the hour-gated cup)
    road_bounty: dict = _dcf(default_factory=dict)
    # transient animation request, consumed by the UI
    anim: str = "idle"
    anim_ttl: float = 0.0

    def __post_init__(self):
        if self.num is not None and self.num >= 0:
            _, by_num = data.load_sprites()
            rec = by_num.get(self.num)
            if rec and not self.field:
                self.field = rec.get("field", "")
            req = data.load_requirements().get(self.num, {})
            self.max_energy = req.get("max_energy", 24)        # per-Monster maxEnergy
            self._sleep_energy_gain = req.get("sleep_energy_gain", 3)
            if self.energy > self.max_energy:
                self.energy = self.max_energy

    # seconds in each stage before it is eligible to evolve (accelerated time).
    # LINES_SPEC §5: the canon curve — babies fly, adults stretch (DM20 timing
    # mapped to game-hours: 6h baby, Child = one full 24h day, 36h, 48h).
    EGG_DURATION = 60      # seconds an egg incubates before hatching (~1 game-hour)

    STAGE_DURATION = {                       # seconds in a stage before it may evolve
        "Fresh": 180, "InTraining": 360, "Rookie": 1440,
        "Champion": 2160, "Ultimate": 2880, "Mega": 9e9,
    }
    LATE_STAGE_WINDOW = 2880.0   # Pen20: the Stage V/VI "evolution window" for the
    #                              5-mistake death rule (Ultimate's own duration)

    @classmethod
    def new_egg(cls, generation=1, egg_type=None):
        return evolution_state.new_egg(cls, generation, egg_type)

    def _hatch_into_fresh(self):
        return evolution_state._hatch_into_fresh(self)
        # (the X-Antibody birth roll is retired -- LINES_SPEC §4: X-forms are
        # reached by hatching X eggs, not won in a lottery at birth)

    def advance_hatch(self, dt):
        return evolution_state.advance_hatch(self, dt)

    def _rand_personality_traits(self):
        return traits._rand_personality_traits(self)

    def _rand_on_champion(self):
        return traits._rand_on_champion(self)

    @classmethod
    def from_num(cls, num):
        return evolution_state.from_num(cls, num)


        # (the sickness recovery lapse, the sick bowel-race penalty and the
        # 6h malady death left with the sickness system (BASIC VPET 2026-07-17); the injury/
        # fatigue/vitamin timers left with theirs, 2026-07-16)

        # incMistake's sickness risks (sickness/injury audit 2026-07-06):
        # filth rolls per pile with a misery pad, and ANY mistake while
        # fatigued adds a 1/1 whisper.  Canon's 50/50 poopCall branch is
        # PROVABLY DEAD in the shipped config (poop/filth audit: the filth
        # array holds 6 piles, MistakeFilthLimit is 7 -- countFilth can never
        # reach it), so it is not ported.
        # (incMistake's filth/fatigue sickness risks left with the sickness
        # system (BASIC VPET 2026-07-17))


        # (the filth sickness rolls left with the sickness system (BASIC VPET 2026-07-17); the
        # filth MOOD nag above is inert since the mood removal but stays as
        # the canon citation it became)


        # (the filth sickness rolls moved to _filth_effects -- canon shape; the
        # old flat roll also invented a STARVATION sickness canon does not have)

    WAKE_MINUTE = 7 * 60          # LINES_SPEC §5: every line form wakes at 7:00


    @property
    def age_days(self):
        return conditions.age_days(self)

    @property
    def is_geriatric(self):
        # the clone's elder line (v0.4.12 L926): AGE alone makes an elder --
        # there is no lifespan clock to be near the end of (DSprite mortality
        # 2026-07-22).  The stage gate stays: the +9 aged-shuffle frames the
        # flag drives exist for the grown stages.
        return (not self.dead
                and self.stage in ("Rookie", "Champion", "Ultimate", "Mega")
                and self.age_days >= GERIATRIC_AGE_DAYS)

    def stomach_capacity(self):
        return stats.stomach_capacity(self)

    # (day_phase/is_daytime and the season calendar left with the day/night
    # + seasons removal -- BASIC VPET 2026-07-17.  The wall clock stays: the
    # sleep system's bedtimes are clock hours, not phases.)


    @property
    def ideal_temp(self):
        return conditions.ideal_temp(self)

    def background(self, file=None):
        return misc.background(self, file)

    def pick_background(self, key):
        return misc.pick_background(self, key)

    def _disposition(self):
        return traits._disposition(self)


    def _glutton(self):
        return traits._glutton(self)

    def _restless(self):
        return traits._restless(self)

    def personality(self):
        return traits.personality(self)

    # (the timeRanks system -- time_pref/seed_time_pref/favorite_time/
    # disliked_time -- left with the day/night system.  BASIC VPET 2026-07-17)

    # (the weather machine -- _update_weather, the thermostat, the futon's
    # temperature pin, the sick fever/chill swings -- was removed whole with
    # the weather system; BASIC VPET 2026-07-16)

    def _set_xantibody(self, state):
        return evolution_state._set_xantibody(self, state)

    # (buy_habitat/move_to -- the habitat buy/move economy -- left with the
    # habitat system: the home scene is wired to the egg now.  BASIC VPET
    # 2026-07-16)


    # (effect_name/call_paused -- the careEffect runtime, Futon-only -- left
    # with the staple props: strict-DSprite items, 2026-07-17)

    # (the thermostat -- set_temp_goal/clear_temp_goal/heat_on -- the futon's
    # pause_temp and the ideal-band comfort mood (_temperature_effects) left
    # with the weather system; the habitat-compat affinity followed with the
    # habitat system itself -- BASIC VPET 2026-07-16.)

    def save_from_death(self):
        return memory_state.save_from_death(self)

    def needs_care(self):
        return conditions.needs_care(self)

    def needs_attention(self):
        return conditions.needs_attention(self)

    def near_bedtime(self):
        return conditions.near_bedtime(self)

    def _guard(self, asleep_blocks=True):
        return misc._guard(self, asleep_blocks)


    def _base_weight(self):
        return stats._base_weight(self)

    def _maybe_evolve(self):
        return evolution_state._maybe_evolve(self)

    # (_apply_egg_habitat/_apply_natural_habitat/go_home_habitat left with
    # the habitat system -- the egg wires the scene directly now.  BASIC
    # VPET 2026-07-16)


    # ---- per-species physiology (DVPet calcNeedDecay coefficients) -------
    def _phys(self):
        return misc._phys(self)

    @property
    def _hunger_interval(self):
        return intervals._hunger_interval(self)

    @property
    def _poop_interval(self):
        return intervals._poop_interval(self)

    @property
    def _strength_interval(self):
        return intervals._strength_interval(self)

    # ---- nutrition (DVPet GoodNutrition: protein/mineral/vitamin macros) --
    def good_nutrition(self):
        return misc.good_nutrition(self)


    def _species_food(self):
        return misc._species_food(self)


    _ATTR3 = ("Vaccine", "Data", "Virus")


    def _become(self, num):
        return evolution_state._become(self, num)

    def evolve_to(self, num):
        return evolution_state.evolve_to(self, num)

    def _swap_form(self, num, subtract_current=False):
        return evolution_state._swap_form(self, num, subtract_current)

    def mode_change(self):
        return evolution_state.mode_change(self)

    def can_mode_change(self):
        return evolution_state.can_mode_change(self)

    # ---- care actions --------------------------------------------------------
    def _set_anim(self, name, ttl):
        return misc._set_anim(self, name, ttl)

    def _set_weight(self, value):
        return stats._set_weight(self, value)

    def _weight_limit_penalty(self):
        return stats._weight_limit_penalty(self)

    def _set_calories(self, value):
        return stats._set_calories(self, value)

    def _set_obedience(self, value):
        return stats._set_obedience(self, value)



    def condition(self):
        return conditions.condition(self)

    def current_mood(self):
        return conditions.current_mood(self)

    def _set_enthusiasm(self, value):
        return stats._set_enthusiasm(self, value)

    def _set_energy(self, value):
        return stats._set_energy(self, value)

    # (_energy_bonus_save -- checkEnergyIncFromPerfectConditions -- left
    # with the day/night system: its trigger WAS the favourite time of day.
    # BASIC VPET 2026-07-17)

    def energy_pct(self):
        return stats.energy_pct(self)

    def _poop_size(self):
        return misc._poop_size(self)


    # (apply_training -- the four-drill DVPet versus training, its attribute
    # power growth, taste-rank ledger and Effort-per-drill -- left with the
    # classic training system (0.5 TRAINING 2026-07-17).  Powers now grow
    # ONLY through battle wins (record_battle's canon setPower +1 stays);
    # Effort fills via the pill; the drill trains FORM.  The attr-rank
    # ledger below is INERT -- nothing warms it, and _power_bonus_attr
    # falls through to the species seed.)


    def is_fatigued(self):
        return conditions.is_fatigued(self)

    def is_injured(self):
        return conditions.is_injured(self)

    def is_frail(self):
        return conditions.is_frail(self)

    def is_freezing(self):
        return conditions.is_freezing(self)

    def is_overheating(self):
        return conditions.is_overheating(self)

    # (_sicken/_worsen_sick/_check_sick/_check_worse_sick -- the whole
    # sickness machine -- left with the sickness system, BASIC VPET
    # 2026-07-17.  The pill is a tonic, filth is a mood/mistake matter,
    # and nothing is contagious.)


    def _growth_period(self):
        return intervals._growth_period(self)

    def _is_failed_form(self):
        return conditions._is_failed_form(self)

    def final_care_grade(self):
        return memory_state.final_care_grade(self)

    def make_memory(self):
        return memory_state.make_memory(self)


    # (the Play action left 2026-07-17: it was spoil() -- mood up, obedience
    # down -- and the mood system is gone, so all it did was punish obedience
    # for a hop.  The clone has no play key; the "play" fx/pose stays for the
    # toy items (itemfx Play/Bounce scripts).)


    def _personality_mood(self, e):
        return traits._personality_mood(self, e)


    # ⛔ JP/EN RELIC GOTCHA (armor canon audit 2026-07-17, the KO6
    # stage-name class): JP 誠実 "Sincerity" is the EN dub's RELIABILITY
    # egg -- the WATER family (item 20: Submarimon/Depthmon/Tylomon...);
    # JP 純真 "Purity" is the EN dub's SINCERITY egg (item 18: Shurimon/
    # Ponchomon...).  The v0.5.5 map wired the EN names backwards, so the
    # Sincerity Egg sold the water armors and Reliability the ninjas.
    _CREST_IDS = {"egg_of_courage": 15, "egg_of_friendship": 16,
                  "egg_of_love": 17, "egg_of_reliability": 20,
                  "egg_of_knowledge": 19, "egg_of_sincerity": 18,
                  "egg_of_hope": 21, "egg_of_light": 22,
                  "egg_of_kindness": 23, "egg_of_miracles": 24,
                  "egg_of_destiny": 25}


    def status_word(self):
        return conditions.status_word(self)
