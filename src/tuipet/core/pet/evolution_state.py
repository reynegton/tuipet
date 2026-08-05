from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
import tuipet.core.egg as egg_mod
from tuipet.i18n.translator import t
from tuipet.core.petbase import *

def new_egg(cls, generation: int=1, egg_type: Optional[Any]=None) -> Any:  # type: ignore
    if egg_type is None:
        egg_type = random.randrange(egg_mod.count())
    pet = cls(num=-1, name="Egg", stage="Egg",
              egg_type=egg_type, generation=generation)
    if generation == 1:
        # the tamer's pocket money (gameplay polish #23, 2026-07-22): a
        # first-generation pet started at 0 bits with every faucet
        # gated -- adventure needs Rookie, a cup needs a stake it
        # couldn't cover.  250 opens the first Rookie stake or one
        # small shop treat; generation 2+ inherits the estate instead.
        pet.bits = 250
    if generation > 1:
        # the heir's ESTATE (death/rebirth + item audits): canon's
        # resetToEgg never touches bits, the bag or the trophy room --
        # all device-lifetime, all inherited.  (The care BONUS rides the
        # bonus_seed channel, granted by app._grant_memory -- the old
        # last_gen.bonus copy was a second, partial careBonusOnReset that
        # the seed always stomped; retired, memory audit 2026-07-06.)
        import tuipet.utils.persistence as _persist
        est = _persist.prev_gen_estate()
        pet.bits = est["bits"]
        pet.inventory = est["inventory"]
        pet.trophies = est["trophies"]
        pet.trophies_won = est["trophies_won"]   # beaten qualifiers persist (seasonBeat)
        bank = {f: int(v) for f, v in (est.get("dna_owned") or {}).items()}
        if bank:                                 # the DNA bank rides the estate
            pet.dna_owned = {f: bank.get(f, 0) for f in data.DNA_FIELDS}
    # a fresh game dawns at 8:00 -- world_seconds 0 is MIDNIGHT, inside every
    # bedtime window, and a hatchling born asleep is a rotten first minute
    pet.world_seconds = 8 * 60.0
    # (the DVPet StartingUses grant -- Toilet/Bandage/Futon -- left with
    # the staple props: strict-DSprite items, 2026-07-17.  DSprite's
    # catalog has no furniture; a fresh device starts with an empty bag.)
    return pet


def _hatch_into_fresh(pet: Any) -> None:
    _, by_num = data.load_sprites()
    target = egg_mod.hatch_target(pet.egg_type)
    if target is None or target not in by_num or data.is_placeholder(target):
        fresh = [n for n, r in by_num.items() if r["stage"] == "Fresh" and not data.is_placeholder(n)]
        target = random.choice(fresh)
    # arc 5: every hatch canonicalizes to a line root -- duplicate twin
    # dexes (the mystery-egg pools) become the root carrying their name.
    # The fuzzy corpus engine receives no NEW pets; it remains for legacy
    # saves and for pets jogressed out of their line.
    croot, lid = lines_mod.canonical_root(target)
    if croot is not None:
        target = croot
    pet.evolve_to(target)
    pet.line_id = lid                    # binds the pet to its line for life
    pet.hatching = False
    pet._rand_personality_traits()               # fix disposition/glutton/restless for life


def advance_hatch(pet: Any, dt: Any) -> Any:
    """Advance the 3s hatch animation at frame cadence (10 Hz) so every DVPet
    crack interval renders (rock 4-15, drawNum(1)@16, drawNum(2)@19, hatch@29).
    Returns True on the frame the egg actually hatches into a Fresh."""
    if not pet.hatching:
        return False
    pet._hatch_t = getattr(pet, "_hatch_t", 3.0) - dt
    if pet._hatch_t <= 0:
        pet._hatch_into_fresh()
        return True
    return False


def from_num(cls, num: int) -> Any:  # type: ignore
    _, by_num = data.load_sprites()
    r = by_num[num]
    pet = cls(num=num, name=r["name"], stage=r["stage"], attribute=r["attribute"],
              field=r.get("field", ""))
    return pet


def _set_xantibody(pet: Any, state: Any) -> None:
    """BINARY (the X slim): any raise lands Permanent; never downgrades."""
    if state != "None":
        pet.x_antibody = "Permanente"


def _maybe_evolve(pet: Any) -> None:
    if getattr(pet, "evo_blocked", False):
        return                    # the anti-evo chip (DSprite item)
    if pet.asleep or pet.is_geriatric:
        return
    if getattr(pet, "fx_hold", False):
        return          # an animation owns the screen; evolve on a quiet tick
    if pet.stage_seconds < pet.STAGE_DURATION.get(pet.stage, 9e9):
        return
    # the armed DNA steer beats any chart (divergence: the wild road,
    # 2026-07-07) -- charging a Field to its stage threshold IS the
    # player's choice, and it opens the corpus graph's next-stage edge
    # in that Field; unarmed pets are untouched (highest_dna '' short-
    # circuits, so goldens and existing saves behave identically)
    target = evolution.divergence_target(pet)
    if target is not None:
        prev = pet.num
        pet.evolve_to(target)
        lines_mod.adopt_line(pet, prev=prev)   # re-anchor to any chart that claims
        return                        # the landing, else ride the corpus engine
    if lines_mod.active(pet):
        # line pets evolve by their line's first-match bracket table ONLY.
        # No match = stay and keep re-checking: counters can still earn a
        # row later (the DM20 Perfect battle gate works exactly so).
        target = lines_mod.select_line(pet)
        if target is not None:
            pet.evolve_to(target)
        return
    target = evolution.select(pet)
    if target is not None:
        pet.evolve_to(target)


def _become(pet: Any, num: int) -> Any:
    """The species-swap prologue shared by evolution and mode change:
    identity, energy ceiling, X-antibody lock-in.  Returns the new
    form's requirements record."""
    _, by_num = data.load_sprites()
    r = by_num[num]
    pet.num, pet.name = num, r["name"]
    pet.stage, pet.attribute = r["stage"], r["attribute"]
    pet.field = r.get("field", pet.field)
    _req = data.load_requirements().get(num, {})
    pet.max_energy = _req.get("max_energy", pet.max_energy)
    pet._sleep_energy_gain = _req.get("sleep_energy_gain", 3)
    pet.energy = min(pet.energy, pet.max_energy)   # DVPet clamps to new max (no auto-refill)
    if _req.get("xantibody", "None") in ("Induced", "Natural"):
        pet._set_xantibody("Permanente")          # the X-Antibody locks in
    return _req


def evolve_to(pet: Any, num: int) -> None:
    was_young = pet.stage in ("Egg", "Fresh", "InTraining", "Rookie")
    _req = pet._become(num)
    # Evolution.java's per-stage ARRIVAL setters (egg/hatch audit
    # 2026-07-06 -- none of these were ported; the missing fresh()
    # obedience 75 was the deepest root of the misbehaving-babies era):
    if pet.stage == "Fresh":
        # fresh(): born TRUSTING (obedience 75) but grumpy (-10 mood),
        # hungry, full of energy, with a starter nutrition base 6/6/6
        pet._set_obedience(FRESH_OBEDIENCE)
        pet.strength = 0
        pet.hunger = 0
        pet.energy = pet.max_energy
    elif pet.stage == "InTraining":
        # inTraining(): toddler rebellion -- obedience above 50 KNOCKS
        # BACK to 50; it wakes with the lights on and real bedtime
        # pressure (sleepLapse 360)
        if pet.obedience > IN_TRAINING_OBEDIENCE:
            pet._set_obedience(IN_TRAINING_OBEDIENCE)
        pet.asleep, pet.nap = False, False
        pet.lights = True
        pet.sleep_lapse = IN_TRAINING_SLEEP_LAPSE
    elif pet.stage == "Rookie":
        # rookie(): the childhood report card SETS obedience -- a Happy
        # daily-mood majority earns 50, Neutral 25, anything else 0
        # (a TIE is Mood.None -> the switch default -> bad, canon exact)
        counts = pet.daily_mood
        best = max(counts.values()) if counts else 0
        tops = [k for k, v in counts.items() if v == best and best > 0]
        major = tops[0] if len(tops) == 1 else None
        pet._set_obedience(ROOKIE_OBED_GOOD if major == "Feliz"
                            else ROOKIE_OBED_DEFAULT if major == "Neutro"
                            else ROOKIE_OBED_BAD)
    if was_young and pet.stage == "Champion":
        # randOnChampion (taste/rank audit 2026-07-06): the childhood-care
        # tally becomes the adult temperament
        pet._rand_on_champion()
    pet.stage_seconds = 0.0
    # per-stage care record resets; the next stage's care decides the next form
    pet.care_mistakes = pet.overeat = pet.disturb = 0
    pet.stage_trainings = pet.stage_battles = 0     # battle_log persists (Pen20 rolling window)
    pet.injuries = 0
    pet.inj_length = pet.fatigue_length = 0.0
    pet.levels_fought = []
    pet.reset_dna()                # DNA.resetDNA: charged DNA clears each evolution
    pet.food_eaten = {c: 0 for c in data.FOOD_CATEGORIES}   # MajorFood resets per stage
    pet.weight = pet._base_weight()
    # DVPet attributeEvolChange: a form raises/lowers the carried attribute powers
    pet.vaccine = max(0, pet.vaccine + _req.get("vaccine_change", 0))
    pet.data_power = max(0, pet.data_power + _req.get("data_change", 0))
    pet.virus = max(0, pet.virus + _req.get("virus_change", 0))
    # (the stage-floor lifespan extension + bonusLifespan left with the
    # lifespan clock -- DSprite mortality 2026-07-22.  LifespanMod stays
    # loaded in the requirements as dormant data.)
    if pet.stage == "Champion" and pet.battles:
        # Evolution.champion: the Rookie career's win rate adjusts the bonus
        # (0.1 x winRate - 5: below 50% costs credit, above earns it)
        wr = pet.wins / pet.battles * 100.0
        pet.evol_bonus += int(WIN_RATE_BONUS_COEF * wr - 5)
    if _req.get("give_item", -1) >= 0:        # GiveItem: grant a consumable (dormant in data)
        pet.add_item(f"i:{_req['give_item']}")
    if _req.get("xantibody", "None") in ("Induced", "Natural"):
        # Evolution.evolve: becoming an X form makes the X state PERMANENT
        pet._set_xantibody("Permanente")
    pet._set_anim("happy", 2.5)


def _swap_form(pet: Any, num: int, subtract_current: bool=False) -> None:
    """The Mode/revert half of Evolution.evolve: swap the SPECIES ONLY.
    No growth-clock reset, no care-record/DNA/taste reset, no lifespan
    extension -- the transform shares the life (evolve skips all of it
    when SpecialEvol is Mode or reverting)."""
    cur = data.load_requirements().get(pet.num, {})
    _req = pet._become(num)
    pet.weight = pet._base_weight()
    if subtract_current:            # revert: un-apply the Mode form's changes
        pet.vaccine -= cur.get("vaccine_change", 0)
        pet.data_power -= cur.get("data_change", 0)
        pet.virus -= cur.get("virus_change", 0)
    else:                           # entering the Mode: its changes apply
        pet.vaccine = max(0, pet.vaccine + _req.get("vaccine_change", 0))
        pet.data_power = max(0, pet.data_power + _req.get("data_change", 0))
        pet.virus = max(0, pet.virus + _req.get("virus_change", 0))


def mode_change(pet: Any) -> Any:
    """PhysicalState.modeChange: a Mode form reverts to its first
    pre-evolution (only if its power changes can be un-applied); anything
    else evolves along a valid Mode target.  The activity refusal rolls
    with the energy pre-check, compliance is spent, success costs
    ModeChangeEnergyChange and plays State.Evolving.
    Returns (old_num_or_None, message)."""
    if pet.dead:
        return None, "Descansando agora — aperte N para um novo ovo."
    if pet.asleep:
        return None, pet._disturbed()
    refused = pet.check_refused(energy_change=MODE_CHANGE_ENERGY)
    pet.check_compliant()
    if refused:
        return None, f"{pet.name} refuses to change!"
    old = pet.num
    if evolution.is_mode_form(pet.num):
        prev = evolution.pre_evolution(pet.num)
        cur = data.load_requirements().get(pet.num, {})
        if (prev is None
                or pet.vaccine - cur.get("vaccine_change", 0) < 0
                or pet.data_power - cur.get("data_change", 0) < 0
                or pet.virus - cur.get("virus_change", 0) < 0):
            pet._set_anim("refuse", 1.0)             # Jeering
            return None, "The mode holds — it can't revert."
        pet._swap_form(prev, subtract_current=True)
    else:
        targets = evolution.mode_targets(pet)
        if not targets:
            pet._set_anim("refuse", 1.0)             # Jeering
            return None, "O modo está fora de alcance."
        pet._swap_form(targets[0])
    pet._set_energy(pet.energy + MODE_CHANGE_ENERGY)
    pet._set_anim("happy", 2.5)                      # State.Evolving
    return old, f"MODE CHANGE — {pet.name}!"


def can_mode_change(pet: Any) -> Any:
    return (pet.num != -1 and not pet.dead
            and pet.stage not in ("Egg", "Fresh")
            and evolution.can_mode_change(pet))
