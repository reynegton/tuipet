import random
import time
import math
import tuipet.data.loaders.data as data
import tuipet.utils.sound as sound
from tuipet.core.petbase import *
import tuipet.core.shop as shop
import tuipet.core.datacore as datacore
import tuipet.core.evolution as evolution
import tuipet.core.lines as lines_mod

def add_item(pet, key, n=1):
    """Drop loot / grants straight into the bag."""
    pet.inventory[key] = pet.inventory.get(key, 0) + n


def take_item(pet, key, n=1):
    """Spend n from the bag, dropping the key at zero -- add_item's mirror
    (this decrement lived in four hand-rolled copies; refactor 2026-07-05)."""
    left = pet.inventory.get(key, 0) - n
    if left <= 0:
        pet.inventory.pop(key, None)
    else:
        pet.inventory[key] = left


def spend_bits(pet, price):
    """The affordability gate + deduction in ONE place (the 'Not enough
    bits.' guard lived in four copies).  True when paid."""
    if pet.bits < price:
        return False
    pet.bits -= price
    return True


def _compensate_attrs(pet):
    """compensateAttributes x3 rotations: each negative power borrows from
    the next two in canon's order.  (Canon's zero-all escape only fires
    when all THREE are negative -- with both banks empty its loop would
    spin forever; unreachable with the shipped symmetric trades, and the
    port floors the deficit at 0 instead of freezing.)"""
    def comp(main, weak, normal):
        while main < 0:
            if weak > 0:
                weak -= 1
                main += 1
            if main < 0 and normal > 0:
                normal -= 1
                main += 1
            if weak <= 0 and normal <= 0 and main < 0:
                return 0, weak, normal       # the safe floor (see docstring)
        return main, weak, normal
    v, d, vi = pet.vaccine, pet.data_power, pet.virus
    v, d, vi = comp(v, d, vi)
    d, vi, v = comp(d, vi, v)
    vi, v, d = comp(vi, v, d)
    pet.vaccine, pet.data_power, pet.virus = v, d, vi


def use_item(pet, key):
    """Consume one inventory item -> a short result message ('' = the
    item does nothing here, None-equivalent = don't have it).  The
    DSprite item table, cloned from v0.4.x (BASIC VPET 2026-07-16): the
    DVPet consumable machine -- meds, bandages, vitamins, toys, futons,
    transports, relics, crafters -- left with the item system.  A
    _Refused message keeps the item ('consume on refusal' burned
    Rev.Floppies on live pets; clone audit 2026-07-15)."""
    if pet.inventory.get(key, 0) <= 0:
        return "Nenhum sobrando."
    # the crest eggs (Armor-Spirit): the ONE clone item family that maps
    # onto a classic system -- each virtue joins its Relic's
    # EvolItemID, so the armor evolutions stay reachable (the dub swap is
    # deliberate: reliability->Purity(18), destiny->Fate(25))
    if key.startswith("egg_of_"):
        return pet._crest_egg(key)
    fx = {
        # ---- FOOD (the TUIPET catalog, 2026-07-18) ----------------------
        "fish": lambda: pet._snack(hunger=1),
        "vegetable": lambda: pet._snack(hunger=1, weight=-1),
        "tuna": lambda: pet._snack(hunger=2, energy=1),
        "cake": lambda: pet._snack(hunger=1, energy=2, weight=2),
        "cupcake": lambda: pet._snack(hunger=1, energy=1),
        "cookie": lambda: pet._snack(hunger=1, energy=1),
        "candy": lambda: pet._snack(hunger=1, energy=1),
        "cheese_burger": pet._junk,
        "giga_meal": pet._giga_meal,
        "steak": pet._premium_meat,
        "poison_mushroom": pet._deadly,
        # ---- MEDICINE ---------------------------------------------------
        "vitamin": pet._vitamin,
        "miracle_drink": pet._miracle_drink,
        "cold_compress": pet._cold_compress,
        # ---- CARE -------------------------------------------------------
        "sleeping_pill": pet._sleep_pill,
        "caffeine_pill": pet._caffeine,
        "music_player": pet._alarm,
        "textbook": pet._textbook,
        "port_potty": pet._smart_potty,
        # ---- TRAINING ---------------------------------------------------
        "energy_drink": pet._energy_drink,
        "slim_drink": pet._super_carrot,
        "dumbbell": pet._training_pack,
        # ---- EVOLUTION --------------------------------------------------
        "grow_capsule": pet._time_gear,
        "anti_evo_chip": pet._anti_evo,
        "x_antibody": pet._x_item,
        "dna_crystal": pet._dna_crystal,
        "vaccine_chip": lambda: pet._attr_chip("vaccine", 15),
        "data_chip": lambda: pet._attr_chip("data_power", 15),
        "virus_chip": lambda: pet._attr_chip("virus", 15),
        "vaccine_chip_g": lambda: pet._attr_chip("vaccine", 30),
        "data_chip_g": lambda: pet._attr_chip("data_power", 30),
        "virus_chip_g": lambda: pet._attr_chip("virus", 30),
        "omni_chip_g": lambda: pet._attr_chip(None, 30),
        # ---- LEGACY -----------------------------------------------------
        "revive_floppy": pet._revive_item,
        "memory": pet._inherit_memory,
        # ---- PLAY (small LIVE dials; the SHOW is fired by the bag panel)
        "ball": lambda: pet._toy(weight=-1, msg="Um chutinho incrível!"),
        "skateboard": lambda: pet._toy(weight=-2, energy=-1,
                                        msg="Ele arraса!"),
        "xylophone": lambda: pet._toy(energy=2, msg="Um recital encantador."),
        "video_game": lambda: pet._toy(energy=2, weight=1,
                                        msg="One more level…"),
        "television": lambda: pet._toy(energy=3, weight=1,
                                        msg="Colado na tela."),
        # ---- ADVENTURE (spent ON THE ROAD, not from the home bag) -------
        "town_transport": lambda: _Refused("Save it for the road (press T)."),
        "disaster_transport": lambda: _Refused("Save it for the road (press T)."),
        "life_recovery": lambda: _Refused("Restores adventure lives — use it on the road."),
        "zone_transport": lambda: _Refused("Save it for the road (press T)."),  # noqa: F405
        "continent_transport": lambda: _Refused("Save it for the road (press T)."),  # noqa: F405
        # ---- THE EXPANSION's singular doors (2026-07-26) ----------------
        "med": pet._med_item,
        "elixir": pet._elixir,
        "vitamin_g": pet._vitamin_g,
        "gold_pill": pet._gold_pill,
        "supplement": pet._supplement,
        "hp_chip": lambda: pet._attr_chip(None, 5),
        "hp_chip_g": lambda: pet._attr_chip(None, 10),
        "board_game": pet._board_game,
        "computer_game": pet._computer_game,
        "toy_oven": pet._toy_oven,
        "futon": pet._futon,
        "x_program": pet._x_program,
        "chocolate_egg": pet._chocolate_egg,
        "book": pet._textbook_lite,
        "hedonism_101": pet._hedonism,
        "trampoline": lambda: pet._toy(weight=-1, strength=1,
                                        msg="BOING. Light training!"),
    }.get(key)
    # the expansion FAMILIES: authored snacks, evolution keys, capsules
    if fx is None and key in pet._SNACK_FX:
        fx = lambda: pet._csv_snack(key)          # noqa: E731
    if fx is None and (key in pet._ITEM_EVO_IDS
                       or key in pet._DIRECT_EVO_TARGET):
        fx = lambda: pet._evo_key(key)            # noqa: E731
    if fx is None and (key in pet._CAPSULE_KEYS
                       or key in pet._PRANK_CAPSULES):
        fx = lambda: pet._capsule(key)            # noqa: E731
    if fx is None:
        return ""
    # life-state guard: only the Rev.Floppy works on the dead, and
    # NOTHING works on an egg
    if pet.dead and key != "revive_floppy":
        return _Refused("")
    if pet.stage == "Egg" or pet.num < 0:
        return _Refused("")
    # item on a sleeper: the alarm wakes mistake-FREE (its whole point),
    # the sleeping pill is pointless, the cold shower runs its OWN disturb
    # (same law, applied inside so "AWAKE and bracing" can be true),
    # anything else DISTURBS -- then applies.  The FUTON joins the exempt
    # set (2026-07-26): it is the sleep family's fourth member -- sliding
    # a bed under a sleeper is the opposite of a disturbance.
    if pet.asleep and key not in ("music_player", "sleeping_pill",
                                   "futon"):
        pet._disturbed()
    out = fx()
    if not isinstance(out, _Refused) and out is not None:
        pet.take_item(key)
    return out


def _crest_egg(pet, key):
    """A crest egg -> the classic Relic item-evolution flow."""
    if pet.dead or pet.stage == "Egg" or pet.num < 0:
        return _Refused("")
    item_id = pet._CREST_IDS.get(key, -1)
    target = evolution.item_select(pet, item_id)
    if target is None:
        pet._set_anim("refuse", 1.0)
        return _Refused(f"{pet.name} can't use that yet.")
    if pet.asleep:
        pet._disturbed()
    prev = pet.num
    pet.evolve_to(target)
    lines_mod.adopt_line(pet, prev=prev)     # a special jump re-anchors
    pet.take_item(key)
    pet._set_anim("happy", 1.6)
    import tuipet.utils.persistence as _persist
    _persist.armor_add(1)                 # the crest-wave shop gate counts it
    return f"{pet.name} armor-evolved!"


def _energy_drink(pet):
    """The label says "energy to FULL": SET the signed meter to max (the
    old += max_energy left a drained pet short of full), and refuse at
    full like every care sibling instead of vanishing for nothing."""
    if pet.energy >= pet.max_energy:
        return _Refused("Energia já está cheia.")
    pet._set_energy(pet.max_energy)
    return "Energia restaurada!"


def _snack(pet, hunger=0, energy=0, weight=0, obedience=0, powers=None,
           strength=0):
    """The TUIPET food family (2018-07-18 -> grown 2026-07-26): plain
    live-meter meals.  Positive-hunger food is refused at a full belly,
    like every meal.  The expansion legs (obedience / VDV powers /
    effort) land the authored columns of the new rows -- a pepper's +1
    power rides the chip grammar, effort clamps to its 0-4 gauge."""
    if hunger > 0 and pet.hunger >= FULL_HUNGER:
        return _Refused("Refused - belly's full.")
    if hunger:
        pet.hunger = _clamp(pet.hunger + hunger, 0, FULL_HUNGER)
    if energy:
        pet._set_energy(pet.energy + energy)
    if weight:
        pet._set_weight(max(1, pet.weight + weight))
    if obedience:
        pet._set_obedience(pet.obedience + obedience)
    if strength:
        pet.strength = _clamp(pet.strength + strength, 0, 4)  # noqa: F405
    if powers:
        v, d, vi = powers
        pet.vaccine += v
        pet.data_power += d
        pet.virus += vi
    return "Nham nham."


def _giga_meal(pet):
    if pet.hunger >= FULL_HUNGER:
        return _Refused("Refused - belly's full.")
    pet.hunger = FULL_HUNGER
    pet._set_energy(pet.energy + 4)
    pet._set_weight(pet.weight + 6)
    return "UM BANQUETE."


def _vitamin(pet):
    # the canon second job (restoration 2026-07-23): a live vitamin
    # guards against battle injuries (the decompile's good_v/bad_v
    # column) for a game-day -- so a full-effort pet still has a
    # reason to take one before a hard fight
    if pet.strength >= 4 and getattr(pet, "vitamin_lapse", 0.0) > 0:
        return _Refused("Esforço cheio e a vitamina está agindo.")
    pet.strength = 4
    # 1440 game-min == ONE GAME DAY (~24 real minutes of play).  Burns
    # down by dt in petbody._tick_life -- see THE UNIT LAW there.
    pet.vitamin_lapse = 1440.0
    return "Cheio de energia — e ele protege!"


def _bandage(pet):
    """The SECOND med, restored (canon restoration 2026-07-23, Joel:
    "it was wrongfully stripped").  Cures the injury, one dose --
    the pill's own grammar; the pill stays sick-only.  Two ailments,
    two meds, the device pair."""
    if not pet.injured:
        return _Refused("Nada para curativo.")  # noqa: F405
    pet.injured = False
    pet.inj_length = 0.0        # the wait is what the Bandage buys off
    pet._set_anim("happy", 1.4)
    return "Totalmente curado!"


def _caffeine(pet):
    """Tonight's bedtime pushed later: a quarter of the night off the
    clock the pet ACTUALLY sleeps by.  Line pets (every hatch) read the
    wall-clock window, not sleep_lapse -- the old pressure-only nudge
    made this a paid no-op for them (gameplay audit 2026-07-19); their
    push rides the same grace channel a disturb uses.

    THE NO-OP DOSE IS REFUSED (item sweep 2026-07-24).  Both branches
    could spend a 300b pill and move nothing -- a second pill while the
    grace already holds that push, or a pressure pet whose sleep_lapse
    is still 0 (nowhere near bedtime) -- while saying "Wide awake for a
    while yet."  Every care sibling refuses at full instead ("Energy is
    already full", "already a model pupil"); this was the outlier."""
    if pet.asleep:
        return _Refused("Too late - it's already down.")
    if pet._in_sleep_window() is not None:
        bt = lines_mod.bedtime_minutes(pet)
        night = (pet.WAKE_MINUTE - bt) % DAY_MINUTES
        push = night * 0.25
        if getattr(pet, "_bed_postpone_t", 0.0) >= push:
            return _Refused("Bedtime's already pushed back.")  # noqa: F405
        pet._bed_postpone_t = push
    else:
        if pet.sleep_lapse <= 0:
            return _Refused("It's nowhere near bedtime.")      # noqa: F405
        pet.sleep_lapse = max(0.0, pet.sleep_lapse - pet.sleep_limit * 0.25)
    return "Bem acordado por um tempo ainda."


def _miracle_drink(pet):
    """THE ERASER, rehoused and nerfed (Joel 2026-07-23: "one at a
    time, own item").  foods.csv row 18 is DVPet's own answer -- the
    ONLY consumable in either sheet carrying `Mistake = -1` -- so the
    eraser did not need inventing, only finding.

    Why it matters enough to keep at all: care mistakes are a DEATH
    clock, not a gate.  20 kills outright, an Ultimate/Mega dies at 5
    once two game-days into the stage, and the hazard ladder gets
    100x worse from 5 to 20.  The counter resets on every evolution
    -- but 241 of 417 Megas are TERMINAL, and for those it never
    resets again.  This drink is the only way back.

    Canon: Energy +12, Mistake -1.  Its -Mood and -Life legs are
    dropped: mood is a verified no-op meter and the lifespan clock
    left with DSprite mortality (2026-07-22)."""
    if pet.care_mistakes <= 0:
        return _Refused("Nada no histórico para apagar.")   # noqa: F405
    pet.care_mistakes -= 1
    pet._set_energy(pet.energy + MIRACLE_ENERGY_GAIN)   # noqa: F405
    left = pet.care_mistakes
    return ("Um erro, perdoado." if not left
            else f"One slip forgiven — {left} still on the slate.")


def _cold_compress(pet):
    """THE CHEAP ERASER (2026-07-27, Joel: "fill the cure hole").

    care_mistakes is the game's death clock -- 20 kills outright, an
    Ultimate dies at 5 -- and the ONLY answer was a 7777b drink that
    also paid +12 energy.  One luxury is not a ladder.  This one wipes
    the same single slip for a quarter of the price and takes the
    energy instead of giving it: relief you have to sleep off.
    """
    if pet.care_mistakes <= 0:
        return _Refused("Nada no histórico para apagar.")   # noqa: F405
    if pet.energy <= COMPRESS_ENERGY_COST:                 # noqa: F405
        return _Refused("Sem energia para o choque.")   # noqa: F405
    pet.care_mistakes -= 1
    pet._set_energy(pet.energy - COMPRESS_ENERGY_COST)    # noqa: F405
    left = pet.care_mistakes
    return ("Um erro apagado — e isso dói." if not left
            else f"One slip scrubbed off — {left} still on the slate.")


def _textbook(pet):
    """THE TEXTBOOK, back to canon (Joel 2026-07-23: R4).  items.csv
    row 0 is `+Obedience -Mood +Stress`; mood and stress are stripped
    systems, so only the obedience leg lands -- and it is the FIRST
    item support the restored discipline system has ever had.

    Refused at a full gauge like every other care sibling, so it
    can't be burned for nothing."""
    if pet.obedience >= MAX_OBEDIENCE:                   # noqa: F405
        return _Refused(f"{pet.name} is already a model pupil.")  # noqa: F405
    before = pet.obedience
    pet._set_obedience(pet.obedience + TEXTBOOK_OBEDIENCE)  # noqa: F405
    return f"Studied hard. (+{pet.obedience - before} obedience)"


def heal_bandage(pet):
    """THE H KEY's verb: patch the battle injury, free (the bandage's
    FINAL door -- Joel 2026-07-26: "remove bandage as an item
    alltogether and just add an h heal hotkey".  It spent one day as a
    300b shop item (v0.5.277, tag-only, never on PyPI) and before that
    one era as the F menu's third row; a care action on this device is
    a BUTTON, and now it has its own).  The canon time-heal (injLapse)
    stays underneath as background truth.

    Mirrors feed_pill's shape: guarded, and healing a sleeper
    DISTURBS it first."""
    if (_g := pet._guard(asleep_blocks=False)) is not None:
        return _g
    if not pet.injured:
        return _Refused("Nada para curativo.")            # noqa: F405
    if pet.asleep:
        pet._disturbed()
    return pet._bandage()


def _attr_chip(pet, field, amount):
    """THE ATTRIBUTE CHIPS (P6, 2026-07-23) -- foods.csv rows 10/11/12
    (+15) and 20/21/22 (+30), plus 33 (Omni, all three).

    Va/D/Vi are LIVE and load-bearing: hundreds of evolution rows gate
    on them, and battle power reads them.  Until now the only ways to
    raise one were winning a battle in that attribute (+1) and the
    inheritance-only Memory -- so a whole live lever had nothing
    buyable behind it.  A chip is worth about fifteen wins.

    Uncapped ON PURPOSE: the win path it shortcuts is uncapped too
    (record_battle just does `pet.vaccine += inc`), and inventing a
    ceiling here would be inventing a rule.  `field=None` is the Omni
    chip -- every power at once.

    Canon legs NOT applied: -Mood (a verified no-op meter) and
    +Stress (a stripped system)."""
    fields = pet._ATTR_FIELDS if field is None else (field,)
    for f in fields:
        setattr(pet, f, getattr(pet, f) + amount)
    if field is None:
        return f"Every power surges! (+{amount} each)"
    return f"{pet._ATTR_WORD[field]} power +{amount}!"


def _dna_crystal(pet):
    """+10 banked DNA in the pet's own Field (the live DNA bank; skips
    one mash session)."""
    field = getattr(pet, "field", "") or ""
    if field in ("", "None"):
        return _Refused("No Field to resonate with.")
    have = pet.dna_owned.get(field, 0)
    if have >= MAX_DNA_INVENTORY:
        return _Refused("That Field's bank is full.")
    pet.dna_owned[field] = min(MAX_DNA_INVENTORY, have + 10)
    return f"+{pet.dna_owned[field] - have} {field} DNA banked!"


def _toy(pet, weight=0, energy=0, msg="Fun!", obedience=0, strength=0):
    """The toy dial: exercise sheds weight, couch time buys energy at a
    weight price.  The SHOW (itemfx script) is fired by the bag panel.
    The expansion legs: a spoiling toy dents obedience (authored), the
    trampoline's bounce is light training (effort, 0-4 gauge)."""
    if weight:
        pet._set_weight(max(1, pet.weight + weight))
    if energy:
        pet._set_energy(pet.energy + energy)
    if obedience:
        pet._set_obedience(pet.obedience + obedience)
    if strength:
        pet.strength = _clamp(pet.strength + strength, 0, 4)  # noqa: F405
    return msg


def _deadly(pet):
    # through _die like every other death: it clears asleep/hatching and
    # sets the pose -- the hand-rolled dead=True skipped both, and the
    # tick-edge detector never saw a between-ticks death at all
    # (gameplay audit 2026-07-19; the app's state check pairs with this)
    pet._die("a poison mushroom")
    return "...estava DELICIOSO. E foi fatal."


def _junk(pet):
    pet.hunger = FULL_HUNGER
    pet._set_weight(pet.weight + 4)
    # the real mistake pipeline: the bare counter bumped care_mistakes
    # without the mood sting or mistake_day, so the burger slip was
    # invisible to the birthday judgment
    pet._inc_mistake()
    return "Delicioso. Lamentável."


def _premium_meat(pet):
    pet.hunger = FULL_HUNGER
    # 12 REAL hours (Joel 2026-07-19, "tune them up to match the words"):
    # the old 12*60 ticks delivered 12 real MINUTES while the text and
    # this message promised hours -- the eat card's countdown exposed it
    pet.full_until = pet.world_seconds + 12 * 3600.0
    return "Satisfeito por 12 horas."


def _smart_potty(pet):
    pet.clean()
    pet.auto_clean_until = pet.world_seconds + 24 * 3600.0  # 24 REAL hours (same ruling)
    return "Limpeza automática por 24 horas."


def _sleep_pill(pet):
    """Sleep NOW, no argument.  A line pet's real sleep outside its
    window used to be woken by the very next tick's 7:00-sharp check --
    one second of sleep for 300b (gameplay audit 2026-07-19): out of
    hours the pill's sleep is the daytime DOZE shape instead (the
    shipped lights-out nap), which sleeps off the energy debt and can
    become the night when the window arrives."""
    if getattr(pet, "away", False):
        # the ROAD is no bed (adventure energy audit 2026-07-23): the
        # march waits out pet.asleep, but the life sim is PAUSED in
        # every mode (the TIME LAW's one-law freeze), so a road sleep
        # never ends -- the pill froze the march FOREVER, ESC home the
        # only way out.  Refused, pill kept.
        return _Refused("Not on the road — no bed out here.")  # noqa: F405
    if pet.asleep:
        return _Refused("It's already asleep.")
    pet._fall_asleep()
    # the room drops AFTER the pill's own eat show, never before (bug
    # report 2026-07-26, v0.5.287: "sleep pill is shutting off lights
    # before eating animation, istead of after").  Lights-off is not a
    # dimmer: arenafx keeps DVPet's fully-opaque lightsOff cover up
    # through a care fx, so flipping it here blanked the whole arena --
    # pet, pill and bite strip -- for all 35 beats of the show the pill
    # was bought for.  Same shape as the Assistant_Lights visit, which
    # DVPet also toggles on its FINAL beat; the app flips it at fx end.
    pet.pending_lights_out = True
    pet._bed_postpone_t = 0.0      # "no argument" overrides a disturb grace
    if pet._in_sleep_window() is False:
        pet.nap = True
    return "Zzz..."


def _alarm(pet):
    """Wake Up Without Mistake: a clean wake, no disturb penalty.  In a
    line pet's sleep window the wake must HOLD like a rude one does --
    with no grace the pet re-slept on the very next tick, leaving the
    purpose-built alarm weaker than throwing any other item at the
    sleeper (gameplay audit 2026-07-19)."""
    if not pet.asleep:
        return _Refused("It's already awake.")
    was_nap = pet.nap
    pet.asleep = False
    pet.nap = False
    pet.lights = True
    pet.pending_lights_out = False   # the pill's debt dies with the sleep
    #                                   it served (sleep audit r2, 07-28)
    pet.awake_lapse = 0.0
    if pet._in_sleep_window() is not None and not was_nap:
        pet._bed_postpone_t = float(random.randint(*DISTURB_POSTPONE))
    return "Hora de acordar!"


def _time_gear(pet):
    """The Grow Capsule: a QUARTER of this stage off the growth clock
    (Joel 2026-07-24: "make the grow capsule worth 500b").

    Three rules keep it worth the bits without becoming the bug it
    replaced:

    * a FRACTION, not a flat number of minutes.  Stages run 180..2880
      game-minutes, so a figure that matters to an Ultimate would skip
      a baby stage whole.  A quarter is a quarter everywhere.
    * it HURRIES the wait, it never ENDS it: the push stops one tick
      short of the gate, so no stack of capsules can evolve a pet
      outright -- and at Ultimate, whose stage length IS
      LATE_STAGE_WINDOW, that same stop is what keeps capsules from
      arming the Pen20 frailty death by themselves.
    * a final form has no clock to hurry, and stage_seconds only
      feeds frailty there, so the capsule REFUSES rather than sell a
      pure downside (the no-duds rule).

    ⚠ THE UNIT LAW (item sweep 2026-07-24) is why the old number went:
    the 2026-07-19 pass read "+120min" as 120 REAL minutes and set
    7200, but dt is game-minutes 1:1 -- 2.5x the longest stage in the
    game, from one 500b bottle."""
    dur = pet.STAGE_DURATION.get(pet.stage, 0)
    if not dur or dur >= 9e8 or not datacore.has_next(pet):
        return _Refused(f"{pet.name} has nothing left to hurry.")  # noqa: F405
    ceiling = dur - 1.0                       # never reaches the gate
    target = min(pet.stage_seconds + dur * GROW_CAPSULE_FRACTION,  # noqa: F405
                 ceiling)
    if target <= pet.stage_seconds:
        return _Refused("O relógio de crescimento já está cheio.")  # noqa: F405
    moved = target - pet.stage_seconds
    pet.stage_seconds = target
    return f"Time lurches forward. (+{int(moved)}min)"


def _anti_evo(pet):
    pet.evo_blocked = not getattr(pet, "evo_blocked", False)
    return "Evolução " + ("BLOQUEADA." if pet.evo_blocked else "desbloqueada.")


def _x_item(pet):
    """The X-Antibody chip: raises the X state (the classic X system).
    Canon xEvolve() charges calcXAntibodyLifeDec() the instant X is gained
    from None (PhysicalState L3361) -- the X-Program's price in LIFE.  That
    burn was dead; the antibody was a free ride (Joel 2026-07-22)."""
    if pet.x_antibody != "None":
        return _Refused("O anticorpo já está ativo.")
    # (calcXAntibodyLifeDec left with the lifespan clock -- DSprite
    # mortality 2026-07-22.  NOTE: the unmarked-pet death roulette was
    # never THIS item's -- it belonged to the separate X-PROGRAM item,
    # removed with the strict-DSprite shelf 2026-07-17; the chip has
    # always been the safe path.  Dossier audit 2026-07-22 corrected
    # this comment's false claim that a roulette ran "below".)
    pet._set_xantibody("Permanent")
    import tuipet.utils.persistence as _persist
    _persist.note_xanti()
    return "O Anticorpo-X faz efeito!"


def _training_pack(pet):
    """The Dumbbell: +10 stage trainings, capped 999 (the source's canon
    value -- the +5 was unexplained drift; TUIPET catalog 2026-07-18)."""
    pet.stage_trainings = min(999, pet.stage_trainings + 10)
    return "Treino +10."


def _revive_item(pet):
    if not pet.dead:
        return _Refused("Ninguém precisa ser revivido.")
    pet.save_from_death()
    return "VIVO."


def stash_wild_memory(pet):
    """A FOUND memory carries a random payload (2026-07-24, Joel:
    "make wild chips carry a random payload").  Where an INHERITED chip
    holds a maxed ancestor's etched Va/D/Vi (tens to hundreds), a wild
    one holds a stranger's faint trace -- a small single-attribute
    imprint well under the +15 base chip.  Queued in `wild_memories`
    so it never collides with the single inherited-payload slot; the
    queue keeps one-chip-one-payload true no matter how many are held."""
    total = random.randint(WILD_MEMORY_MIN, WILD_MEMORY_MAX)  # noqa: F405
    field = random.choice(("vaccine", "data", "virus"))
    mem = {"name": "A stranger", "vaccine": 0, "data": 0, "virus": 0}
    mem[field] = total
    pet.wild_memories.append(mem)
    return mem


def peek_memory(pet):
    """The payload the NEXT chip use will apply -- inherited first, then
    the oldest wild trace.  The inherit fx needs the numbers BEFORE
    use_item consumes them (shopscreen._use)."""
    if pet.memory:
        return pet.memory
    return pet.wild_memories[0] if pet.wild_memories else {}


def _inherit_memory(pet):
    """The Memory chip (DVPet item 32, anim Inherit): a payload's
    Va/D/Vi joins this pet's powers (petbase MEMORY_* law).  An
    INHERITED chip's etched ancestor data takes priority; failing that,
    a FOUND chip spends the oldest wild trace (2026-07-24).  A chip with
    no payload of either kind -- a bare estate husk -- stays mute.
    (The chip's lifespan hours left with the lifespan clock -- DSprite
    mortality 2026-07-22; an OLD chip's "seconds" payload is ignored.)"""
    inherited = bool(pet.memory)
    mem = pet.memory or (pet.wild_memories[0]
                              if pet.wild_memories else None)
    if not mem:
        return _Refused("O chip está silencioso.")  # noqa: F405
    pet.vaccine += int(mem.get("vaccine", 0) or 0)
    pet.data_power += int(mem.get("data", 0) or 0)
    pet.virus += int(mem.get("virus", 0) or 0)
    if inherited:
        pet.memory = {}
    else:
        pet.wild_memories.pop(0)
    return f"{mem.get('name', 'The ancestor')}'s power lives on!"


def _super_carrot(pet):
    if pet.weight <= 1:
        return _Refused("Nada mais para aparar.")
    pet._set_weight(max(1, pet.weight - 10))
    return "Leve como uma pena!"


def _csv_snack(pet, key):
    """A generic authored meal -- and the FOOD EVOLUTION door: one
    corpus form (Citramon) gates on `evol_food` and the source's
    processFoodEvol (evolution.food_select) sat with zero callers.
    Eating a new-table food now asks it; the meal is an extra gate,
    never a bypass."""
    out = pet._snack(**pet._SNACK_FX[key])
    if isinstance(out, _Refused):  # noqa: F405
        return out
    icon = shop.ICON_KEYS.get(key, "")
    target = evolution.food_select(pet, int(icon[2:])) \
        if icon.startswith("f:") else None
    if target is not None:
        prev = pet.num
        pet.evolve_to(target)
        lines_mod.adopt_line(pet, prev=prev)
        pet._set_anim("happy", 1.6)
        return f"...the meal stirs something. {pet.name} evolves!"
    return out


def _med_item(pet):
    """The field pill (foods.csv 4, grant-only): cures sickness, the
    free pill's one job in pocket form -- never sold, so the free-cure
    law holds."""
    if not pet.sick:
        return _Refused("Nenhuma doença para tratar.")  # noqa: F405
    pet.sick = False
    pet._set_anim("eat", 1.4)
    return "A doença passa."


def _elixir(pet):
    """The premium combo (2000b): cures sickness AND fills the tank.
    The free pill stays the cure -- this sells convenience."""
    if not pet.sick and pet.energy >= pet.max_energy:
        return _Refused(f"{pet.name} doesn't need it.")  # noqa: F405
    pet.sick = False
    pet._set_energy(pet.max_energy)
    pet._set_anim("eat", 1.4)
    return "Doença curada — cheio de vida!"


def _vitamin_g(pet):
    """The golden mend (2000b): heals the injury AND the vitamin's
    whole job (effort full + a game-day's injury guard).  H stays the
    free cure -- this is the vitamin's big sibling."""
    if not pet.injured and pet.strength >= 4 \
            and getattr(pet, "vitamin_lapse", 0.0) > 0:
        return _Refused("Nada para remendar e a proteção está ativa.")  # noqa: F405
    pet.injured = False
    pet.inj_length = 0.0
    pet.strength = 4
    pet.vitamin_lapse = 1440.0
    pet._set_anim("happy", 1.4)
    return "Dourado! Curado, protegido, cheio de energia."


def _gold_pill(pet):
    """Canon Energy +12 (the miracle drink's dose, no eraser)."""
    if pet.energy >= pet.max_energy:
        return _Refused("Energia já está cheia.")  # noqa: F405
    pet._set_energy(pet.energy + 12)
    return "Vitalidade dourada!"


def _supplement(pet):
    """Effort to FULL + the obedience leg (authored +5) + its weight."""
    if pet.strength >= 4 and pet.obedience >= MAX_OBEDIENCE:  # noqa: F405
        return _Refused("Nada mais para fortalecer.")  # noqa: F405
    pet.strength = 4
    pet._set_obedience(pet.obedience + 5)
    pet._set_weight(pet.weight + 1)
    return "Transbordando esforço!"


def _board_game(pet):
    """The attribute RESHAPER (items.csv 5): Vaccine -15 -> Data +15,
    plus the authored obedience.  Refused when there is no Vaccine to
    convert -- a converter with an empty tank is a dud."""
    if pet.vaccine < 15:
        return _Refused("Poder Vacina insuficiente para troca.")  # noqa: F405
    pet.vaccine -= 15
    pet.data_power += 15
    pet._set_obedience(pet.obedience + 5)
    return "Um jogo longo — a ordem cede à lógica. (Va-15 → D+15)"


def _computer_game(pet):
    """Virus -15 -> Data +15 (items.csv 8)."""
    if pet.virus < 15:
        return _Refused("Poder Vírus insuficiente para troca.")  # noqa: F405
    pet.virus -= 15
    pet.data_power += 15
    return "Recorde — o caos compila. (Vi-15 → D+15)"


def _toy_oven(pet):
    """'+Appetite': makes room for a meal (hunger -1)."""
    if pet.hunger <= 0:
        return _Refused("A barriga já está vazia.")  # noqa: F405
    pet.hunger = max(0, pet.hunger - 1)
    return "Um cheiro maravilhoso — de repente com fome."


def _futon(pet):
    """The deep daytime bed: lie down NOW (the sleeping pill's flow)
    and the doze HOLDS until the tank is FULL, not half (petbody's
    recovery-doze threshold reads futon_doze; cleared on wake)."""
    if getattr(pet, "away", False):
        return _Refused("Not on the road — no bed out here.")  # noqa: F405
    if pet.asleep:
        if getattr(pet, "futon_doze", False):
            return _Refused("Já bem agasalhado.")  # noqa: F405
        pet.futon_doze = True
        return "O futon desliza por baixo — sono mais profundo."
    pet._fall_asleep()
    pet.lights = False
    pet._bed_postpone_t = 0.0
    if pet._in_sleep_window() is False:
        pet.nap = True
    pet.futon_doze = True
    return "Bem agasalhado. Zzz..."


def _x_program(pet):
    """The RISKY X (items.csv 14, a 100%-authored elite drop): the
    authored drains ARE the price -- belly emptied, effort zeroed,
    80% of the tank torn away -- then the X takes hold.  No invented
    death roll; the aftermath (hunger calls, red-energy stings) is
    the gamble."""
    if pet.x_antibody != "None":
        return _Refused("O anticorpo já está ativo.")  # noqa: F405
    pet.hunger = 0
    pet.strength = 0
    pet._set_energy(pet.energy - int(pet.max_energy * 0.8))
    pet._set_xantibody("Permanent")
    import tuipet.utils.persistence as _persist
    _persist.note_xanti()
    return "Ele convulsiona... e TRANSCENDE. O X faz efeito!"


def _textbook_lite(pet):
    """The Book (items.csv 2): the textbook's little brother -- the
    authored +5, same full-gauge refusal."""
    if pet.obedience >= MAX_OBEDIENCE:                   # noqa: F405
        return _Refused(f"{pet.name} is already a model pupil.")  # noqa: F405
    before = pet.obedience
    pet._set_obedience(pet.obedience + 5)
    return f"A quiet chapter. (+{pet.obedience - before} obedience)"


def _hedonism(pet):
    """Hedonism 101 (items.csv 1): obedience -80, exactly as authored.
    A trap with a warning label -- the poison mushroom's precedent:
    a trap always goes down, never refuses."""
    pet._set_obedience(pet.obedience - 80)
    return "Ele lê a coisa TODA. Modos: obliterados."


def _evo_key(pet, key):
    """A dormant door opens: the spirits and the Datatron ride the same
    item_select flow the crest eggs do; the direct items name their form
    outright.  Refused (item kept) when nothing answers."""
    item_id = pet._ITEM_EVO_IDS.get(key)
    if item_id is not None:
        target = evolution.item_select(pet, item_id)
    else:
        target = evolution.item_direct(pet, pet._DIRECT_EVO_TARGET[key])
    if target is None:
        pet._set_anim("refuse", 1.0)
        return _Refused(f"{pet.name} can't use that yet.")  # noqa: F405
    prev = pet.num
    pet.evolve_to(target)
    lines_mod.adopt_line(pet, prev=prev)
    pet._set_anim("happy", 1.6)
    if key.startswith("human_"):
        # the Frontier chain, kept authentic: mastering a HUMAN spirit
        # wakes its BEAST half -- the beast key lands in the bag, ready
        # for the next stage's door (roads give Human, the Human gives
        # Beast; no cup RNG invented)
        beast = key.replace("human_", "beast_", 1)
        if beast in pet._ITEM_EVO_IDS:
            pet.add_item(beast)
            return (f"{pet.name} evolui — e a metade FERA do "
                    "spirit answers!")
    return f"{pet.name} evolves!"


def _capsule(pet, key):
    """Open the box: a tier-weighted surprise from the gift pool -- and
    on a HOLIDAY the roll reaches one tier higher (the festival-present
    grammar; 'christmas presents are holiday versions of these').  A
    prank capsule pays from the junk drawer, every time."""
    if key in pet._PRANK_CAPSULES:
        prize = random.choice(pet._PRANK_POOL)
    else:
        import tuipet.core.tournament as tournament
        prize = pet._pick_gift(festival=bool(tournament.holiday()))
    while prize in pet._CAPSULE_KEYS or prize in pet._PRANK_CAPSULES:
        prize = pet._pick_gift()        # never a box inside a box
    pet.add_item(prize)
    pet.pending_prize = prize           # the cheer SHOWS it (app hook)
    e = shop.entry(prize) or {}
    name = e.get("name", "something")
    if key in pet._PRANK_CAPSULES:
        pet._set_anim("refuse", 1.2)
        return f"...it's {name}. HA!"
    pet._set_anim("happy", 1.6)
    return f"Inside: {name}!"


def _chocolate_egg(pet):
    """A snack with a TOY INSIDE (authored: 'Toy Inside +Mood'): the
    meal, then a common-tier surprise."""
    out = pet._snack(hunger=1, weight=1)
    if isinstance(out, _Refused):  # noqa: F405
        return out
    # a TOY, as authored -- not another food (bug: "isnt there supposed
    # to be items in chocolate eggs?", 2026-07-28).  The old pool took
    # every common-tier good: 18 of 29 prizes were FOODS (one was
    # another chocolate egg), and grant-only treats leaked in because
    # a None tier reads as common.  Priced non-Feed commons only now.
    pool = [k for k, v in shop.CATALOG.items()
            if k not in pet._GIFT_BANNED and v.where == "home"
            and k not in pet._CAPSULE_KEYS
            and k not in pet._PRANK_CAPSULES
            and v.price is not None and v.tier == "common"
            and v.category != "Feed"]
    prize = random.choice(pool)
    pet.add_item(prize)
    pet.pending_prize = prize           # the cheer SHOWS it (app hook)
    e = shop.entry(prize) or {}
    return f"Munch — a toy inside: {e.get('name', 'something')}!"


