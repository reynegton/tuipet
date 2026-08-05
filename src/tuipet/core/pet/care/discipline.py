from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.utils.sound as sound
from tuipet.core.petbase import FULL_HUNGER, DISOBEY_BELOW, DISOBEY_MAX_P, SCOLD_OBED_INC

def check_refused(pet: Any, food: Optional[Any]=None, attr: Optional[Any]=None, energy_change: float=0.0, item: Optional[Any]=None) -> Any:
    """The obedience refusal roll left with the discipline system (BASIC
    VPET 2026-07-16): the pet obeys care commands.  TWO meter rules
    survive because they are affordability, not temperament: the energy
    auto-refuse (a jogress/relic/mode-change it cannot pay for) and
    feed()'s own full-belly head-shake."""
    pet.refused = False
    if energy_change and pet.energy + math.ceil(energy_change * pet.max_energy) < 0:
        pet._set_anim("refuse", 1.5)
        return True                  # can't afford the energy -> auto-refuse
    return False


def manners_refusal(pet: Any, kind: Any) -> Any:
    """EARNED DISOBEDIENCE (D3, 2026-07-23): a NEGLECTED pet blows off
    a command.  True == it refused.

    Deliberately a SEPARATE door from check_refused: that one is
    AFFORDABILITY (the energy auto-refuse) and its only callers are
    the jogress and mode-change paths -- both EVOLUTION doors, and
    both outside the shape Joel approved.  Wiring manners into it
    would have silently started refusing evolutions (plan audit P2).

    Refusable: feed, train, battle.  NEVER clean, and never the pill
    or the bandage -- a pet you cannot clean or heal is a softlock,
    not a personality.  Feeding is also never refused while the belly
    is EMPTY: starvation kills, and no amount of attitude should be
    able to close the only door that saves it."""
    if kind not in ("feed", "train", "battle"):
        return False
    if kind == "feed" and pet.hunger <= 0:
        return False                       # never starve a pet out of spite
    gap = DISOBEY_BELOW - pet.obedience              # noqa: F405
    if gap <= 0:
        return False                       # well-raised: NEVER refuses
    p = min(1.0, gap / DISOBEY_BELOW) * DISOBEY_MAX_P  # noqa: F405
    if random.random() >= p:
        return False
    pet.refused = True
    pet._set_anim("refuse", 1.5)
    return True


def refuse_attack(pet: Any, my_hp: Any, enemy_hp: Any) -> Any:
    """Always False: the Orders-style mid-fight refusal left with the
    discipline system."""
    return False


def stop_travel_prob(pet: Any) -> Any:
    """PhysicalState.checkStopTravel as a per-fire PROBABILITY (the caller
    composes it over a full stride).  One draw per controller fire,
    r in [cap, cap + chance*3000); the energy fraction scales the draw
    DOWN, so a rested pet essentially never stops but a drained one plants
    its feet: refuse when r*(energy+1)/max - dispo*35 + obey - 5
    <= cap - obedience."""
    # the obedience walk-refusal left with the discipline system
    # (BASIC VPET 2026-07-16): only a truly DRAINED pet plants its feet
    energy_mod = 1.0 - (pet.max_energy - (pet.energy + 1)) / max(1, pet.max_energy)
    return 1.0 if energy_mod <= 0 else 0.0


def stop_travel_effects(pet: Any) -> None:
    """The refusal's side effects (split from the roll so it can compose)."""
    pet.refused = True
    pet._set_anim("refuse", 1.5)


def check_stop_travel(pet: Any) -> Any:
    """One canonical per-fire draw (kept for tests/direct callers)."""
    if random.random() < pet.stop_travel_prob():
        pet.stop_travel_effects()
        return True
    return False


def check_compliant(pet: Any) -> Any:
    """Always False ("never grudging"): compliance left with the
    discipline system.  Canon's True meant "it obeyed only because you
    spent its compliance token" -- the resentment branches (forced-feed
    rank souring, forced-fatigue obedience bills, grudging weak item
    application) key on it, so the willing constant is False."""
    return False


def _open_praise(pet: Any) -> None:
    """A win or a mega drill opens a 600 game-min praise window
    (= ~10 REAL minutes; see THE UNIT LAW in petbody._tick_life --
    the label used to read "10 game-min", the P0b mislabel)."""
    pet.praise_window = pet.world_seconds + 600.0


def _open_scold(pet: Any) -> None:
    """The tantrum's answer window: 600 game-min (~10 REAL minutes)
    before ignoring it counts."""
    pet.scold_window = pet.world_seconds + 600.0


def _calm_discipline_call(pet: Any) -> None:
    """Bedtime (and canBattle, per canon) placates an open tantrum --
    no reward, no penalty, the moment just passes."""
    if pet.discipline_call:
        pet.discipline_call = False
        pet.scold_window = 0.0


def praise(pet: Any) -> Any:
    """PRAISE: inside a proud-moment window it pays obedience +10 and
    the cheer; outside one, nothing -- the no-praise-farming rule
    (from the pre-strip discipline audit)."""
    if (_g := pet._guard()) is not None:
        return _g
    if pet.world_seconds <= getattr(pet, "praise_window", 0.0):
        pet.praise_window = 0.0
        pet._set_obedience(pet.obedience + 10)
        pet._set_anim("happy", 1.8)
        return f"{pet.name} sorri de orgulho!"
    pet._set_anim("happy", 1.0)
    return f"{pet.name} parece satisfeito — mas não sabe por quê."


def scold(pet: Any) -> Any:
    """SCOLD: answering an open tantrum pays obedience +25 and the
    scolded sulk; scolding a calm pet just makes it sulk, no gain."""
    if (_g := pet._guard()) is not None:
        return _g
    if pet.discipline_call:
        pet.discipline_call = False
        pet.scold_window = 0.0
        pet._set_obedience(pet.obedience + 25)
        pet._set_anim("sad", 1.8)
        return "Repreendido — lição aprendida."
    pet._set_anim("sad", 1.4)
    return f"{pet.name} faz beicinho — ele não fez nada de errado."


