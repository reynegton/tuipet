from .core import *
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
# --- DNA system (DVPet DNA.class + PhysicalState.applyDNA + config.csv) ---
MAX_DNA_INVENTORY = 99                  # config MaxDNAInventory
DNA_STRENGTH_CHANGE = 1                 # config DNAStrengthChange
# the charge bill moved onto ENERGY when the mood/spirit meters left (DNA
# slim, BASIC VPET 2026-07-16): canon billed 3/6 spirit per unit against a
# +-10 range -- the same "N charge sessions with recovery between" pacing,
# re-expressed on the meter that still exists.  Off-field charging costs
# double, exactly like the spirit bill it replaces.
DNA_SAME_FIELD_ENERGY, DNA_DIFF_FIELD_ENERGY = 1, 2
DNA_SAME_FIELD_SICK, DNA_DIFF_FIELD_SICK = 1, 2     # checkSick target out of SICK_BOUND
DNA_SICK_BOUND = 100                    # config SickChance / WorseSickChance bound

# DVPet ClockTic.getDNARate: the DNA-generate mini-game maps your mash-rate (which,
# at the 10s mark, equals your total presses) onto one of these 8-wide Field bands
# (config _<field>RateMaxMiniGame). Too slow (<=8) or over-mashed (>80) -> None = a
# wasted wager. Faster mashing reaches the rarer late fields (DarkArea needs 73-80).
DNA_RATE_BANDS = (
    (8, "None"), (16, "DeepSaver"), (24, "JungleTrooper"), (32, "NatureSpirit"),
    (40, "WindGuardian"), (48, "DragonsRoar"), (56, "MetalEmpire"),
    (64, "NightmareSoldier"), (72, "VirusBuster"), (80, "DarkArea"),
)

# HIGH-STAKES WAGERS (bit-sink design 2026-07-14).  The classic 1..99 wager
# banks bits into DNA 1:1; everything past the 99-DNA bank cap buys LAB WORK,
# not volume -- and is spent, never refunded:
#   >= 500  STABILIZED: an over/under-mashed sample never spoils -- the rate
#           clamps into the nearest real band instead of rolling None.
#   >= 2500 RESONANT: the two Fields adjacent to the landed band each bank
#           wager//5 DNA as splash (capped, no refund) -- one big roll tops
#           three banks for tamers who value their time over their bits.
MAX_DNA_WAGER = 9999
DNA_STABILIZER_BET = 500
DNA_RESONANT_BET = 2500


def dna_field_for_rate(rate: int) -> str:
    """DVPet getDNARate: the Field a mini-game rate yields (None if over/under-mashed)."""
    for hi, field in DNA_RATE_BANDS:
        if rate <= hi:
            return field
    return "None"
