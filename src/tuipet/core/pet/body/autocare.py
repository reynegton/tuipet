from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.core.shop as shop
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod
from tuipet.core.petbase import *

def _tick_auto_care(pet: Any, dt: Any) -> None:
    """PhysicalState.checkAutoCare, one game-min cadence.  The hourly retainer
    bills first (unpaid -> off duty); then at most one visit per spacing --
    awake: filth > hunger > strength; asleep: filth > a lit room (unless the
    Futon is active, DVPet's !isFuton()).  doAutoCare also walks off duty when
    the pet cannot afford the NEXT visit.  ADAPTATION: DVPet charges when the
    assistant animation ends; a headless tuipet pet applies state (and the
    processAutoCarePrice fee + bond costs) here in the tick, and the app-side
    assistant fx is pure presentation via the assist_event mailbox."""
    if not pet.auto_care:
        return
    if getattr(pet, "away", False):
        # doAutoCare/checkAutoCare both gate on _isHome: while the pet is
        # OUT (adventuring -- canon's teleport toggles it) the assistant
        # neither bills the retainer nor visits (auto-care audit 2026-07-06)
        return
    pet._ac_pay = getattr(pet, "_ac_pay", 0.0) + dt
    while pet._ac_pay >= AUTO_CARE_PAYMENT_MIN:
        pet._ac_pay -= AUTO_CARE_PAYMENT_MIN
        hourly = AUTO_CARE_HOUR_PRICE.get(pet.stage, 0)
        if pet.bits < hourly:
            pet.auto_care = False
            pet.assist_note = "The assistant left — the retainer went unpaid."
            return
        pet.bits -= hourly
    pet._ac_cool = max(0.0, getattr(pet, "_ac_cool", 0.0) - dt)
    if pet._ac_cool > 0:
        return
    act = None
    if not pet.asleep:
        if pet.poop > 0:
            act = "clean"
        elif pet.hunger == 0:
            act = "feed"
        elif pet.strength == 0:
            act = "strength"
    else:
        if pet.poop > 0:
            act = "clean"
        elif pet.lights:
            act = "lights"
    if act is None:
        return
    price = AUTO_CARE_VISIT_PRICE.get(pet.stage, 0)
    if pet.bits < price:                            # doAutoCare: can't cover the visit
        pet.auto_care = False
        pet.assist_note = "The assistant left — it couldn't cover a visit."
        return
    piles, sizes = pet.poop, list(pet.poop_sizes)
    if act == "clean":
        # Assistant_Clean -> onClean: the standard clean, minus YOUR wash pose
        pet.poop, pet.poop_sizes = 0, []
        pet._filth_t = 0                            # mess handled: the filth call resets
    elif act == "feed":
        # assistantFeed: the AI Food Pill serving -- lands on a sick pet
        # (the plain-meat route refused sickness and BILLED the head-shake;
        # assistant audit 2026-07-19)
        pet.feed_meat(assisted=True)
    elif act == "strength":
        pet.feed_pill()                             # the tonic tops effort/energy
    elif act == "lights":
        pet.lights = False                          # Assistant_Lights -> onLights
    # processAutoCarePrice: the visit fee, and the bond cost of hired care
    pet.bits -= price
    pet._set_obedience(pet.obedience + AUTO_CARE_OBEDIENCE)
    pet._set_enthusiasm(pet.enthusiasm + AUTO_CARE_ENTHUSIASM)
    pet._ac_cool = AUTO_CARE_VISIT_SPACING
    pet.assist_event = (act, piles, sizes)          # the app plays the visit


