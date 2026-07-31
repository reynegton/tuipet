import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.utils.sound as sound
from tuipet.core.petbase import FULL_HUNGER, CLEAN_OBED_INC

def clean(pet):
    """PhysicalState.clean: wash the filth off the floor.  (The mood and
    obedience rewards this once paid are INERT -- both meters left with
    their systems 2026-07-16; the write-calls below are the standing
    no-op citations.)"""
    if (_g := pet._guard()) is not None:
        return _g
    if not pet.poop:
        return "Nada para limpar."
    n, pet.poop = pet.poop, 0
    pet.poop_sizes = []                        # clearFilth()
    pet._set_obedience(pet.obedience + CLEAN_OBED_INC[pet._disposition()])
    pet._set_anim("wash", 1.2)
    return f"Limpou {n} cocôs."


def heal(pet):
    """The pill (BASIC VPET 2026-07-16): the med/bandage staples left
    with the DVPet item system -- one staple treats everything, from the
    F menu (and the road's h key)."""
    return pet.feed_pill()


def set_auto_care(pet, on):
    """SpriteAnim's Set_AutoCare switch -> PhysicalState.setAutoCare: hiring
    the assistant also rolls WHICH Monster answers, from the monster.csv
    CanAssist pool (Evolution.getRandomAssistMonster)."""
    if pet.dead:
        return "Descansando agora — aperte N para um novo ovo."
    pet.auto_care = bool(on)
    if pet.auto_care:
        pool = data.assist_pool()
        pet.assistant_num = random.choice(pool) if pool else -1
        _, by_num = data.load_sprites()
        name = (by_num.get(pet.assistant_num) or {}).get("name", "The assistant")
        return f"{name} está de serviço."
    return "O assistente foi dispensado."


def toggle_lights(pet):
    """The lights button (DVPet setLights): toggles the room light ONLY. The pet
    sleeps and wakes on its own schedule -- this does not force sleep or wake."""
    if (_g := pet._guard(asleep_blocks=False)) is not None:
        return _g
    pet.lights = not pet.lights
    if pet.lights and pet.asleep and pet.nap:
        # lightSwitch: lights ON rouses a NAPPING pet (deep sleep ignores it;
        # sick or injured, the lost doze pushes bedtime a minute closer).
        # (canon !isFuton()'s nap shield left with the Futon: strict-DSprite
        # items, 2026-07-17)
        pet._wake()                         # a nap wake rolls +-NapWakeMoodDec
        return "Luzes acesas — acordou da soneca."
    if not pet.lights and not pet.asleep and pet.energy <= 0:
        # the exhausted nag said "S — rest"; a flat "Lights off." read
        # as a no-op while the doze timer ran (QOL 2026-07-23)
        return f"Luzes apagadas — {pet.name} se deita para descansar…"
    return "Luzes apagadas." if not pet.lights else "Luzes acesas."


