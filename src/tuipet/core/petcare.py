"""The pet's CARE surface (tier-5, 2026-07-17): every player-initiated
act -- feeding, cleaning, items and the shop verbs, gifts, discipline and
the refusal rolls."""
from __future__ import annotations
from .pet.care import hygiene, feeding, discipline, gifts, inventory
import math  # noqa: F401
import random  # noqa: F401

import tuipet.utils.backgrounds as backgrounds    # noqa: F401
import tuipet.data.loaders.data as data    # noqa: F401
import tuipet.core.egg as egg_mod    # noqa: F401
import tuipet.core.evolution as evolution    # noqa: F401
import tuipet.core.lines as lines_mod    # noqa: F401
import tuipet.core.shop as shop    # noqa: F401
import tuipet.utils.theme as theme    # noqa: F401
from tuipet.core.petbase import *    # noqa: F401,F403  (constants resolve HERE, per mixin)


class CareMixin:
    """State contract: the Pet dataclass fields; composed into Pet."""

    # (the DVPet furniture -- toilet training / the self-toilet / the manual
    # visit / the Futon tuck-in and its careEffect -- left with the staple
    # props: strict-DSprite items, 2026-07-17.  Poop lands on the floor and
    # the clean action washes it, full classic.)

    def check_refused(self, food=None, attr=None, energy_change=0.0, item=None):
        return discipline.check_refused(self, food, attr, energy_change, item)

    def manners_refusal(self, kind):
        return discipline.manners_refusal(self, kind)

    def refuse_attack(self, my_hp, enemy_hp):
        return discipline.refuse_attack(self, my_hp, enemy_hp)

    def stop_travel_prob(self):
        return discipline.stop_travel_prob(self)

    def stop_travel_effects(self):
        return discipline.stop_travel_effects(self)

    def check_stop_travel(self):
        return discipline.check_stop_travel(self)

    def check_compliant(self):
        return discipline.check_compliant(self)

    def can_feed(self):
        return feeding.can_feed(self)

    def feed(self, food=None, assisted=False):
        return feeding.feed(self, food, assisted)

    def feed_meat(self, assisted=False):
        return feeding.feed_meat(self, assisted)

    def feed_pill(self):
        return feeding.feed_pill(self)

    # ---- discipline: praise / scold, RESTORED (canon restoration B,
    # 2026-07-23, Joel: "it was wrongfully stripped... whatever is canon
    # bring back").  The device pair: SCOLD answers the tantrum call,
    # PRAISE answers a proud moment (a battle win, a mega drill).  The
    # gauge is `obedience` (0..100).  Refusals stay SOFT (standing rule);
    # discipline is the tantrum economy, not a leash. -----------------------
    def _open_praise(self):
        return discipline._open_praise(self)

    def _open_scold(self):
        return discipline._open_scold(self)

    def _calm_discipline_call(self):
        return discipline._calm_discipline_call(self)

    def praise(self):
        return discipline.praise(self)

    def scold(self):
        return discipline.scold(self)

    def clean(self):
        return hygiene.clean(self)

    def heal(self):
        return hygiene.heal(self)

    def set_auto_care(self, on):
        return hygiene.set_auto_care(self, on)

    def toggle_lights(self):
        return hygiene.toggle_lights(self)

    # ---- shop / items --------------------------------------------------------
    # (buy_slot -- the town-counter purchase -- cut with the town chain
    # 2026-07-19; shop.buy is the ONE live purchase path)
    # (dead-code cut, LOW audit 2026-07-19: CareMixin.sell -- shop.sell is
    # the ONE live resell path -- plus _apply_item_stats (the DVPet
    # consumable core; the strict-DSprite item cut orphaned it), _fruit and
    # _erase_mistake (their items left the catalog; the textbook rides
    # _erase_mistakes_all).  Nothing live called any of them.)

    # never a gift: a trap, a road tool, an heirloom, or a premium you'd feel
    # cheated to unwrap for free.  (Road items are already excluded by the
    # where=="home" test; listed here for intent.)
    _GIFT_BANNED = frozenset({"poison_mushroom", "memory", "revive_floppy",
                              "town_transport", "disaster_transport",
                              "life_recovery",
                              # the expansion (2026-07-26): traps and earned
                              # keys are never gift-wrapped -- the spirits
                              # are ENDGAME prizes (roads give Human, cups
                              # give Beast), the X-Program is an elite drop,
                              # and a gift is supposed to be NICE
                              "zone_transport", "continent_transport",
                              "x_program", "burnt_food", "hedonism_101",
                              "prank_capsule_a", "prank_capsule_b",
                              "human_fire_spirit", "human_light_spirit",
                              "human_ice_spirit", "human_wind_spirit",
                              "human_thunder_spirit", "human_earth_spirit",
                              "human_water_spirit", "human_wood_spirit",
                              "human_metal_spirit", "human_dark_spirit",
                              "beast_fire_spirit", "beast_light_spirit",
                              "beast_ice_spirit", "beast_wind_spirit",
                              "beast_thunder_spirit", "beast_earth_spirit",
                              "beast_water_spirit", "beast_wood_spirit",
                              "beast_metal_spirit", "beast_dark_spirit"})

    def _pick_gift(self, festival=False):
        return gifts._pick_gift(self, festival)

    def claim_gift(self):
        return gifts.claim_gift(self)

    def add_item(self, key, n=1):
        return inventory.add_item(self, key, n)

    def take_item(self, key, n=1):
        return inventory.take_item(self, key, n)

    def spend_bits(self, price):
        return inventory.spend_bits(self, price)

    def _compensate_attrs(self):
        return inventory._compensate_attrs(self)

    def use_item(self, key):
        return inventory.use_item(self, key)

    def _crest_egg(self, key):
        return inventory._crest_egg(self, key)

    def _energy_drink(self):
        return inventory._energy_drink(self)

    def _snack(self, hunger=0, energy=0, weight=0, obedience=0, powers=None,
               strength=0):
        return inventory._snack(self, hunger, energy, weight, obedience, powers, strength)

    def _giga_meal(self):
        return inventory._giga_meal(self)

    def _vitamin(self):
        return inventory._vitamin(self)

    def _bandage(self):
        return inventory._bandage(self)

    def _caffeine(self):
        return inventory._caffeine(self)

    def _miracle_drink(self):
        return inventory._miracle_drink(self)

    def _cold_compress(self):
        return inventory._cold_compress(self)

    def _textbook(self):
        return inventory._textbook(self)

    def heal_bandage(self):
        return inventory.heal_bandage(self)

    _ATTR_FIELDS = ("vaccine", "data_power", "virus")
    _ATTR_WORD = {"vaccine": "Vaccine", "data_power": "Data", "virus": "Virus"}

    def _attr_chip(self, field, amount):
        return inventory._attr_chip(self, field, amount)

    def _dna_crystal(self):
        return inventory._dna_crystal(self)

    def _toy(self, weight=0, energy=0, msg="Fun!", obedience=0, strength=0):
        return inventory._toy(self, weight, energy, msg, obedience, strength)

    def _deadly(self):
        return inventory._deadly(self)

    def _junk(self):
        return inventory._junk(self)

    def _premium_meat(self):
        return inventory._premium_meat(self)

    def _smart_potty(self):
        return inventory._smart_potty(self)

    def _sleep_pill(self):
        return inventory._sleep_pill(self)

    def _alarm(self):
        return inventory._alarm(self)

    def _time_gear(self):
        return inventory._time_gear(self)

    def _anti_evo(self):
        return inventory._anti_evo(self)

    def _x_item(self):
        return inventory._x_item(self)

    def _training_pack(self):
        return inventory._training_pack(self)

    def _revive_item(self):
        return inventory._revive_item(self)

    def stash_wild_memory(self):
        return inventory.stash_wild_memory(self)

    def peek_memory(self):
        return inventory.peek_memory(self)

    def _inherit_memory(self):
        return inventory._inherit_memory(self)

    def _super_carrot(self):
        return inventory._super_carrot(self)

    # ======================= THE EXPANSION (2026-07-26) =====================
    # Joel: "bring in all 99 unused items ... your call".  Every handler
    # below lands the AUTHORED columns of its source row on LIVE meters
    # (Mood/Enthusiasm/Stress stay dormant).  Board:
    # ITEM_EXPANSION_2026_07_26.md.

    # the plain snacks: stats straight off the authored foods.csv columns
    # (weight = Calories // 2, the new-row rule).  One table, one handler.
    _SNACK_FX = {
        "meat": dict(hunger=1, weight=2),
        "fruit": dict(hunger=1, obedience=-1),
        "bread": dict(hunger=1, weight=1),
        "cheese": dict(hunger=1, weight=2),
        "broccoli": dict(hunger=1, obedience=2),
        "orange": dict(hunger=1, obedience=-1),
        "honey": dict(hunger=1, energy=1, weight=1, obedience=-5),
        "yellow_pepper": dict(hunger=1, obedience=1, powers=(0, 0, 1)),
        "green_pepper": dict(hunger=1, obedience=1, powers=(0, 1, 0)),
        "red_pepper": dict(hunger=1, obedience=1, powers=(1, 0, 0)),
        "bitter_herbs": dict(hunger=0, obedience=5),
        "food_pill": dict(hunger=4, weight=3, obedience=5),
        "ai_food_pill": dict(hunger=1),
        "ai_supplement": dict(hunger=0, strength=1),
        "burnt_food": dict(hunger=1, strength=-1, obedience=5),
    }

    def _csv_snack(self, key):
        return inventory._csv_snack(self, key)

    def _med_item(self):
        return inventory._med_item(self)

    def _elixir(self):
        return inventory._elixir(self)

    def _vitamin_g(self):
        return inventory._vitamin_g(self)

    def _gold_pill(self):
        return inventory._gold_pill(self)

    def _supplement(self):
        return inventory._supplement(self)

    def _board_game(self):
        return inventory._board_game(self)

    def _computer_game(self):
        return inventory._computer_game(self)

    def _toy_oven(self):
        return inventory._toy_oven(self)

    def _futon(self):
        return inventory._futon(self)

    def _x_program(self):
        return inventory._x_program(self)

    def _textbook_lite(self):
        return inventory._textbook_lite(self)

    def _hedonism(self):
        return inventory._hedonism(self)

    # the evolution KEYS (Joel: "wire fully").  item_select forms answer to
    # their care gates (the item is an extra gate, not a bypass);
    # item_direct is the authored paid shortcut (graph adjacency only).
    _ITEM_EVO_IDS = {
        "datatron": 33,
        "human_fire_spirit": 43, "human_light_spirit": 44,
        "human_ice_spirit": 45, "human_wind_spirit": 46,
        "human_thunder_spirit": 47, "human_earth_spirit": 48,
        "human_water_spirit": 49, "human_wood_spirit": 50,
        "human_metal_spirit": 51, "human_dark_spirit": 52,
        "beast_fire_spirit": 53, "beast_light_spirit": 54,
        "beast_ice_spirit": 55, "beast_wind_spirit": 56,
        "beast_thunder_spirit": 57, "beast_earth_spirit": 58,
        "beast_water_spirit": 59, "beast_wood_spirit": 60,
        "beast_metal_spirit": 61, "beast_dark_spirit": 62,
    }
    _DIRECT_EVO_TARGET = {
        "horn_helmet": 140, "grey_claws": 93, "water_bottle": 110,
        "torn_tatter": 121, "white_wings": 101, "black_wings": 102,
        "metal_armor": 213, "flaming_wings": 97,
    }

    def _evo_key(self, key):
        return inventory._evo_key(self, key)

    # the CAPSULES (Joel: "roll the existing find tool"): the gift roller
    # in item form.  The two AngrySurprise rips are PRANKS -- the box is
    # identical on the shelf and in the bag; that IS the gacha.
    _CAPSULE_KEYS = frozenset({"capsule_a", "capsule_b", "capsule_c",
                               "capsule_d", "capsule_e", "capsule_f",
                               "capsule_g", "capsule_h"})
    _PRANK_CAPSULES = frozenset({"prank_capsule_a", "prank_capsule_b"})
    _PRANK_POOL = ("burnt_food", "fruit", "cheese_burger", "ai_food_pill")

    def _capsule(self, key):
        return inventory._capsule(self, key)

    def _chocolate_egg(self):
        return inventory._chocolate_egg(self)

