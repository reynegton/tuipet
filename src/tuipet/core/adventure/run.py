"""Adventure — the MARCH engine (rebuild phase 2, 2026-07-20).

⛔ OWN-GAME LAW (Joel 2026-07-13, carried forward): DVPet is NOT canon for
adventures.  One biome per run, start to the goal, no mid-run scenery swap.

Built: the MARCH (cross a zone in ~INTERACTIVE_STEPS travel actions, the journey
on a ribbon, arrival ends the run); WILD ENCOUNTERS (a per-leg roll from the
zone's own enemy table, lives, win/flee/loss/fail); and the real 26-ZONE
GEOGRAPHY -- the zones come from data/zones.csv + enemies.csv (data.load_maps),
each wearing ONE biome (its gate boss's terrain, no mid-zone span-hopping) with
its own wild pool; the zone BOSS FIGHT -- reaching the end opens the gate boss
(resolve_boss), and FELLING it is the real victory (a loss costs a life, 0 lives
fails, a survivable loss lets the pet face it again); TRAVEL DRAIN -- each
marched leg tires (energy), burns the calorie buffer (weight trims toward base)
and tops the effort gauge, so a run comes home spent; TOWNS -- a mid-zone
waypoint refills lives, rests energy to at least half the tank and suppresses
encounters; and PROGRESSION --
pet.adv_progress tracks zones conquered (the frontier index); felling a zone's
boss unlocks the next, and the ZonePickPanel lets the player embark on any
unlocked zone; and FINDS -- a marched step may spot loot from the zone's own
table (rand_items/rand_foods) to dig up or pass; the home STATUS CARD (statusbox.adventure_line: Quest
N/26 on the home screen); and TRANSPORT items -- a town warp (Birdra) jumps to
the town and rests, a danger warp (Garuda) dashes toward the boss and gets
ambushed.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import math
import random
from functools import lru_cache

import tuipet.data.loaders.data as data
import tuipet.utils.backgrounds as backgrounds
from .logic import *
from .logic import _veteran, _FESTIVAL_CAPSULES
class Adventure:
    """One expedition across one zone.  The march only: `travel()` advances a
    step toward the goal; `done` flips on arrival.  The view reads `name`,
    `scene`, `pct`, `ribbon()` and `last`."""

    def __init__(self, pet: Any, zone: Optional[Any]=None) -> None:
        self.pet = pet
        self.zone = zone if zone is not None else pick_zone(pet)
        self.loc = 0                     # travel actions taken, 0..steps
        self.done = False
        self.failed = False              # 0 lives -> the run is lost (retreat home)
        self.lives = MAX_LIVES
        self._immunity = 0               # legs left before a wild can roll again
        self._drain_acc = 0              # marched-legs accumulator toward a drain tick
        self._resting = False            # currently standing inside a town span
        self.bits_earned = 0             # bits won this run (wild bounties + the boss)
        self.bounty_spent = False        # the replay boss bounty was already claimed today
        self.fights = 0                  # fights entered this run (wild + boss)
        self.wins = 0                    # ...of those, won
        self.finds = 0                   # loot dug up this run
        self.drops = 0                   # battle drops bagged this run (2026-07-26)
        self.streak = 0                  # chained wins alive RIGHT NOW (run-local)
        self.best_streak = 0             # the run's longest chain (the summary line)
        self.holiday = active_holiday()  # a festival today? double bits + more finds
        zi = zone_index(self.zone)
        self.replay = zi is not None and is_conquered(pet, zi)   # a VETERAN road
        self._vboss = None               # the veteran gate boss, built once
        self.last = f"Setting out for {self.name}."

    @property
    def name(self) -> Any:
        return self.zone["name"]

    @property
    def scene(self) -> Any:
        return self.zone["scene"]        # the run's ONE backdrop (own-game law)

    @property
    def total(self) -> Any:
        return max(1, self.zone["steps"])

    @property
    def pct(self) -> Any:
        return min(100, int(self.loc / self.total * 100))

    @property
    def boss(self) -> Any:
        bs = self.zone.get("bosses") or []
        b = bs[0] if bs else None          # one gate boss per run (the first listed)
        if b is not None and self.replay:
            if self._vboss is None:        # built once: the gate keeps identity
                self._vboss = _veteran(b)
            return self._vboss
        return b

    @property
    def boss_name(self) -> Any:
        b = self.boss
        return b["name"] if b else self.name

    @property
    def boss_felled(self) -> Any:
        """True when this run ended by defeating the gate boss (done=True and
        the zone has a boss).  Bossless zones end via 'arrived' instead, so
        the two victory paths stay distinct in the UI."""
        return self.done and self.boss is not None

    def ribbon(self, width: int=14) -> Any:
        """The journey at a glance -- progress lives HERE, not on the pet, so
        the pet is free to just walk (the old engine's doctrine).  '◆' is you,
        '⚑' the goal, '·' the untrod road."""
        cells = ["·"] * width
        goal = width - 1
        cells[goal] = "⚑"
        pos = min(goal, int(self.loc / self.total * goal))
        cells[pos] = "◆"                 # the pet wins a shared cell (you outrank the goal)
        return "".join(cells)

    # -- wild encounters ------------------------------------------------------
    def _wild_pool(self) -> Any:
        """The road's wild mons: THIS zone's own random-encounter table
        (enemies.csv, filtered to its map/zone by data.load_maps).  Falls back
        to stage-matched roster enemies only if a zone ships no randoms."""
        pool = [e for e in self.zone.get("randoms", ()) if not e.get("boss")]
        if pool:
            return pool
        return [e for e in data.enemies_for_stage(self.pet.stage) if not e.get("boss")]

    def _in_town(self, loc: Any) -> Any:
        """Is this leg inside a town waypoint span (rest + no encounters)?"""
        return any(a <= loc <= b for a, b, _t in self.zone.get("town_legs", ()))

    def town_at(self, loc: Any) -> Any:
        """The town id whose span holds this leg, or None (for the town hub)."""
        for a, b, tid in self.zone.get("town_legs", ()):
            if a <= loc <= b:
                return tid
        return None

    def _roll_encounter(self) -> Any:
        """A wild enemy this leg, or None.  A town is safe ground (no roll);
        immunity after a fight is spent first; then a per-leg roll, the pick
        weighted by AppearanceChance."""
        # grace is LEGS, not fights dodged: it spends on town ground too,
        # else a pre-town fight banked a bonus free leg on the far side
        # (audit 2026-07-25)
        if self._immunity > 0:
            self._immunity -= 1
            return None
        # the roll guards the leg being WALKED (the destination) -- the
        # same leg find/hazard test after the step.  The old pre-step read
        # made the walk OUT of town encounter-free and the walk IN
        # ambushable on the doorstep, the town's safe ground off by one in
        # one direction only (audit 2026-07-25)
        if self._in_town(self.loc + 1):
            return None                     # town ground: no wilds
        if random.random() >= ENCOUNTER_CHANCE:
            return None
        pool = self._wild_pool()
        if not pool:
            return None
        weights = [max(1, e.get("chance", 100)) for e in pool]
        e = random.choices(pool, weights=weights, k=1)[0]
        return _veteran(e) if self.replay else e

    # -- transport (in-run warp items) ----------------------------------------
    def _transport_kind(self, key: str) -> Any:
        """'town' (Birdra), 'danger' (Garuda), 'life' (Life Recovery),
        'skip' (Zone Transport: a safe lift up the road) or 'camp'
        (Continent Transport: the Whamon rest) -- the CATALOG road items
        that mean something WITHIN a run -- else None.  (The expansion
        2026-07-26 gave the two worldmap warps run-jobs: the zone picker
        replaced map warping long ago, so their tickets buy road comfort
        instead -- a lift without an ambush, a rest without a town.)"""
        return {"town_transport": "town", "disaster_transport": "danger",
                "life_recovery": "life", "zone_transport": "skip",
                "continent_transport": "camp"}.get(key)

    def held_transports(self) -> Any:
        """The run-usable road-item keys the pet is carrying, in bag order.
        Each row lists only when it BUYS something (the dead-menu-row rule,
        audit 2026-07-25): Life Recovery hides at full hearts, the Town
        Transport hides on town ground (the rest is already yours), and
        the Danger Warp hides within dash range of the gate (a dash that
        moves nothing).  The town warp reaches the NEAREST span in either
        direction, so late, drained and past the town -- exactly when a
        tamer reaches for it -- the ticket still buys a real town."""
        inv = getattr(self.pet, "inventory", {}) or {}
        return [k for k, n in inv.items() if n > 0 and self._transport_kind(k)
                and not (self._transport_kind(k) == "life"
                         and self.lives >= MAX_LIVES)
                # the ticket buys a TOWN: hidden only when you already
                # stand on town ground (audit 2026-07-25 -- the old
                # forward-only filter hid it at the gate in 26/26 zones,
                # so the gate refusal's promised warp-out never existed;
                # the road CAN double back for a rest)
                and not (self._transport_kind(k) == "town"
                         and (self._in_town(self.loc)
                              or not self.zone.get("town_legs")))
                # the dash buys DISTANCE: at the gate it moved nothing,
                # ate the ticket and forced a fight on a body the gate may
                # have just refused (audit 2026-07-25)
                and not (self._transport_kind(k) == "danger"
                         and self.loc >= self.total - 3)
                # the lift buys legs too: hidden at the gate (2026-07-26)
                and not (self._transport_kind(k) == "skip"
                         and self.loc >= self.total - 1)
                # the camp buys REST: hidden when the tank is already at
                # the half it restores to (the dead-menu-row rule)
                and not (self._transport_kind(k) == "camp"
                         and self.pet.energy >= self.pet.max_energy // 2)]

    def use_transport(self, key: str) -> Any:
        """Spend a road item.  Town warp -> jump to the town and rest
        (lives + energy; the PANEL then offers the hub doors like any
        walked-in arrival).  Danger warp -> dash toward the boss and get
        ambushed on arrival.  Life Recovery -> hearts back to full where
        you stand.  Returns 'town-warp', ('encounter', enemy),
        'danger-warp', 'life-recovery', or None (not a run item / not
        held / hearts already full)."""
        kind = self._transport_kind(key)
        inv = getattr(self.pet, "inventory", {}) or {}
        if kind is None or inv.get(key, 0) <= 0 or self.done or self.failed:
            return None
        if kind == "life":
            if self.lives >= MAX_LIVES:        # defensive: menu already hides it
                return None
            self.pet.take_item(key)
            self.lives = MAX_LIVES
            self.last = "A second wind — lives restored!"
            return "life-recovery"
        if kind == "town" and (self._in_town(self.loc)
                               or not self.zone.get("town_legs")):
            # defensive, like the life warp's full-hearts guard: the menu
            # already hides it, and a ticket must never buy a rest you
            # already have (adventure audit 2026-07-25)
            return None
        if kind == "danger" and self.loc >= self.total - 3:
            # defensive: a dash that moves nothing is not for sale
            return None
        if kind == "skip" and self.loc >= self.total - 1:
            return None                        # defensive: nothing to skip
        if kind == "camp" and self.pet.energy >= self.pet.max_energy // 2:
            return None                        # defensive: nothing to rest
        if kind == "skip":
            # the SAFE lift (expansion 2026-07-26): ten legs forward, no
            # ambush, stopping shy of the gate -- the middle ticket between
            # walking and the danger dash
            self.pet.take_item(key)
            self.loc = min(self.total - 1, self.loc + SKIP_LEGS)
            self.last = "A Birdramon lift — the road slides by below."
            return "skip-lift"
        if kind == "camp":
            # the Whamon CAMP: a rest without a town -- energy to half the
            # tank where you stand.  Lives stay Life Recovery's job; the
            # win streak survives (that is this ticket's premium)
            self.pet.take_item(key)
            half = self.pet.max_energy // 2
            if self.pet.energy < half:
                self.pet._set_energy(half)
            self.last = "Camp pitched — rested where you stand."
            return "camp-rest"
        self.pet.take_item(key)
        if kind == "town":
            # the NEAREST town span, behind included: every zone's span
            # ends mid-road, so a forward-only jump left the whole back
            # half (and the gate) with a ticket that bought nothing.
            # Doubling back re-walks real legs -- the ticket's price on
            # top of its price (audit 2026-07-25).
            legs = list(self.zone.get("town_legs") or ())
            tgt = min(legs, key=lambda lg: min(abs(self.loc - lg[0]),
                                               abs(self.loc - lg[1])))
            self.loc = tgt[0]
            self._rest_up()
            self._resting = True
            self.last = "Warped to a town — rested up."
            return "town-warp"
        # danger: dash to just shy of the boss gate, then an ambush
        self.loc = max(self.loc, max(0, self.total - 3))
        pool = self._wild_pool()
        if pool:
            weights = [max(1, e.get("chance", 100)) for e in pool]
            enemy = random.choices(pool, weights=weights, k=1)[0]
            if self.replay:
                # the warp's ambusher is a VETERAN like every other wild on
                # a conquered road -- the raw entry slipped the wrap while
                # award_bits still paid the trained bounty (audit 2026-07-25)
                enemy = _veteran(enemy)
            self.last = f"Warped ahead — ambushed by {enemy['name']}!"
            return ("encounter", enemy)
        self.last = "Warped ahead."
        return "danger-warp"

    def _roll_find(self) -> Any:
        """A loot key spotted on the road this step, or None (no finds in a
        town -- the pet is resting, not scavenging)."""
        pool = self.zone.get("find_keys") or ()
        if not pool or self._in_town(self.loc):
            return None
        chance = FIND_CHANCE * (HOLIDAY_FIND_MULT if self.holiday else 1)
        if random.random() >= chance:
            return None
        # a FESTIVAL road present IS A CAPSULE now (item expansion
        # 2026-07-26, Joel: "rewire christmas presents to basically be
        # holiday versions of these"): the wrapped box lands in the bag and
        # is OPENED for its roll -- opened on the festival day, the roll
        # reaches a tier higher (petcare._capsule); two of the ten boxes
        # are the authored AngrySurprise pranks.  Home gifts stay home.
        if self.holiday and random.random() < FESTIVAL_PRESENT_CHANCE:
            return (random.choice(_FESTIVAL_CAPSULES), True)
        # TIERED FIND RARITY (D1, 2026-07-24): the pool used to be a flat
        # random.choice, so a zone's legendary signature turned up exactly as
        # often as its cheapest snack.  Weighted by the same tier ladder the
        # shelves read -- common 8 : uncommon 4 : rare 2 : legendary 1.
        import tuipet.core.shop as shop
        weights = [shop.tier_weight(k) for k in pool]
        return (random.choices(list(pool), weights=weights, k=1)[0], False)

    def _roll_hazard(self) -> Any:
        """An ambush pounce this leg, or None: town ground is safe, and the
        pouncer is one of THIS zone's own wilds (real roster art -- the
        hazard never invents a creature)."""
        if self._in_town(self.loc):
            return None
        if random.random() >= HAZARD_CHANCE:
            return None
        pool = self._wild_pool()
        if not pool:
            return None
        # the zone's authored AppearanceChance weights, same as the walk
        # and warp picks -- this was the one unweighted draw (audit 2026-07-25)
        weights = [max(1, e.get("chance", 100)) for e in pool]
        return random.choices(pool, weights=weights, k=1)[0]

    def score(self) -> Any:
        """The run's arcade score, from the tallies the card already shows."""
        return (self.bits_earned
                + SCORE_WIN * self.wins
                + SCORE_FIND * self.finds
                + SCORE_LIFE * self.lives
                + SCORE_STREAK * max(0, self.best_streak - 1)
                + (SCORE_CONQUEST if self.done else 0))

    def _rest_up(self) -> None:
        """A town rest, wherever it comes from (waypoint or warp): lives back,
        energy rested to at least HALF the tank (topped by TOWN_REST_ENERGY
        when already above it) -- and the WIN STREAK breaks.  One rest, one
        price, both doors (the waypoint rests on arrival -- there is no
        push-on choice there; truthed 2026-07-25).  (D1 ruling
        2026-07-23: the old flat +6 was one battle's worth -- "rested up" that
        a single fight erased; half a tank makes the words true, and a pet
        KNOCKED past empty warping in comes back standing.)"""
        self.lives = MAX_LIVES
        self.pet._set_energy(max(self.pet.energy + TOWN_REST_ENERGY,
                                 self.pet.max_energy // 2))
        # THE TOWN IS THE ROAD'S SICKBED (audit 2026-07-25): injury is the
        # one ailment a run itself inflicts (fight rolls), and with the
        # clock parked it could never heal -- measured, an ideal pet was 4x
        # likelier to be turned back hurt at the gate than to lose the
        # boss.  A rest patches it, and cures a sickness carried in (the
        # sick trudge's pilgrimage; the home cures are free too, so the
        # town gives away nothing the F menu doesn't).  Mirrors the cure
        # verbs' own writes (petcare pill/bandage) exactly.
        self.pet.sick = False
        self.pet.injured = False
        self.pet.inj_length = 0.0
        self.streak = 0

    def chain(self, won: Any) -> None:
        """Advance the WIN STREAK: a chained win grows it (and the run's
        best); a loss or a flee breaks it."""
        if won:
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.streak = 0

    def streak_mult(self) -> Any:
        """The chained-win bounty multiplier: +STREAK_STEP per win past the
        first, capped at STREAK_CAP."""
        return min(STREAK_CAP, 1 + STREAK_STEP * max(0, self.streak - 1))

    def hazard_hit(self) -> None:
        """Eat the pounce: the small energy toll.  Single source -- the panel
        reports the missed dodge, the ENGINE applies the cost.  UNFLOORED by
        the energy floor law (a KNOCK, not a spend): this is the one road
        source that pushes past empty and trips the planted-feet refusal."""
        self.pet._set_energy(self.pet.energy - HAZARD_ENERGY)
        self.last = "Ambushed on the road!"

    def award_bits(self, enemy: Any) -> Any:
        """Pay out a beaten enemy's bounty (enemies.csv BitsWon range): a wild
        pays a little, a gate boss pays a lot.  Adds to the pet's purse and the
        run tally, returns the amount."""
        lo, hi = enemy.get("bits") or (1, 5)
        lo, hi = min(lo, hi), max(lo, hi)
        amt = random.randint(lo, hi) if hi > 0 else 0
        if amt and self.holiday:
            amt *= HOLIDAY_BITS_MULT        # festival purse
        if amt:
            amt = round(amt * self.streak_mult())   # the chained-win bonus
        if amt and self.replay:
            amt = amt * REPLAY_BITS_NUM // REPLAY_BITS_DEN   # veteran bounty
            if enemy.get("boss"):
                # THE REPLAY BOUNTY IS RATIONED (anti-printer, audit
                # 2026-07-25): a conquered boss pays its veteran purse once
                # per real day per zone -- the town_bought idiom.  Unbounded,
                # the festival x streak x veteran stack paid ~18,000b per
                # repeatable 8-minute run against a 51,677b whole-catalog;
                # every other earner is rationed (cup: the hour; town rows:
                # the daily cap; raid: attempts).  Wilds still pay, and a
                # FIRST conquest is untouched.
                import tuipet.core.shop as shop
                zi = zone_index(self.zone)
                if zi is not None:
                    day = shop._today_ordinal()
                    led = dict(getattr(self.pet, "road_bounty", None) or {})
                    if led.get("day") != day:
                        led = {"day": day}
                    if led.get(str(zi)):
                        amt, self.bounty_spent = 0, True
                    else:
                        led[str(zi)] = 1
                    self.pet.road_bounty = led
        if amt:
            self.pet.bits += amt
            self.bits_earned += amt
        return amt

    def award_drop(self, enemy: Any) -> Any:
        """THE BATTLE DROP (item expansion 2026-07-26, Joel: "i even want
        battle drops in adventure") -- and it was AUTHORED all along:
        every enemies.csv row carries a LootTableID into dropRate.csv.
        Wilds shed attribute chips at 2-7%, elites shed the X-Program at
        100%, and each map's unique story boss drops its RELIC.

        Rationing rides the bounty's own rules: a REPLAY boss whose daily
        veteran purse is spent drops nothing either (the road_bounty
        ledger, anti-printer) -- wilds stay live, a first conquest is
        untouched.  Returns the granted CATALOG key, or None."""
        if enemy.get("boss") and self.replay and self.bounty_spent:
            return None
        table = data.load_loot_tables().get(enemy.get("loot_table", -1))
        if not table:
            return None
        import tuipet.core.shop as shop
        from tuipet.core.pet import Pet
        roll, cum = random.random() * 100, 0
        for icon, rate in table:
            cum += rate
            if roll < cum:
                # a Relic drop speaks the crest shelf's own key; all
                # else resolves through the one icon->key door
                iid = int(icon[2:]) if icon.startswith("i:") else -1
                crest = {v: k for k, v in Pet._CREST_IDS.items()}.get(iid)
                key = crest or shop.key_for_icon(icon)
                if key is None:
                    return None              # an unshipped row stays dormant
                self.pet.add_item(key)
                self.drops += 1
                return key
        return None

    def resolve(self, won: Any, fled: bool=False) -> Any:
        """Settle a wild fight.  Every fight grants a grace leg so the next
        step is clear.  won -> march on; fled -> got away, no penalty, no
        progress; lost -> a life, and at 0 lives the run FAILS (retreat home).
        Returns 'won' | 'fled' | 'lost' | 'failed'."""
        self._immunity = max(self._immunity, POST_FIGHT_GRACE)
        if won:
            self.last = "The road clears."
            return "won"
        if fled:
            self.last = f"{self.pet.name} slips away."
            return "fled"
        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
            self.failed = True
            self.last = f"Overwhelmed in {self.name}."
            return "failed"
        unit = "life" if self.lives == 1 else "lives"
        self.last = f"Beaten back — {self.lives} {unit} left."
        return "lost"

    # -- travel drain ---------------------------------------------------------
    def _march_drain(self) -> None:
        """One marched leg's toll: it tires (energy), burns the calorie buffer
        (weight trims toward the species base when it bottoms out), and tops the
        effort gauge -- travel is light training.  Applied on a leg cadence."""
        from tuipet.core.pet import CALORIE_LIMIT
        self._drain_acc += 1
        if self._drain_acc < WALK_DRAIN_EVERY:
            return
        self._drain_acc = 0
        p = self.pet
        p._set_energy(max(0, p.energy - TRAVEL_ENERGY_DEC))
        p.calories -= TRAVEL_CALORIE_DEC
        if p.calories <= -CALORIE_LIMIT:            # buffer bottomed: shed a weight unit
            p.calories = CALORIE_LIMIT
            p._set_weight(max(p._base_weight(), p.weight - 1))
        if p.strength < TRAVEL_EFFORT_CAP:          # light training tops the effort gauge
            p.strength += 1

    # -- the march ------------------------------------------------------------
    def travel(self) -> Any:
        """Advance one step down the road -- unless a wild blocks it.  Returns
        ('encounter', enemy) when one fires (no progress that leg), 'arrived'
        on the step that reaches the goal (the run is `done`), 'step'
        otherwise, None if the run is already over."""
        if self.done or self.failed:
            return None
        if self.pet.check_stop_travel():
            # canTravel (restored 2026-07-21): a pet pushed PAST EMPTY plants
            # its feet -- today's deliberately-soft calibration (petcare:
            # negative energy only), NEVER the old chance-based refusal
            self.last = f"{self.pet.name} refuses to walk!"
            return ("refused", None)
        enemy = self._roll_encounter()
        if enemy is not None:
            self.last = f"A wild {enemy['name']} blocks the road!"
            return ("encounter", enemy)
        self.loc += 1
        self._march_drain()              # the leg's toll: energy / calories / effort
        if self._in_town(self.loc):
            if not self._resting:        # just stepped into a town: rest up
                self._resting = True
                self._rest_up()
                self.last = f"Reached a town in {self.name} — rested up."
                return "town"
        else:
            self._resting = False
        if self.loc >= self.total:
            self.loc = self.total
            if self.boss is not None:
                # the boss GATES the end -- crossing is not the win, felling it is
                self.last = f"{self.boss_name} guards the gate!"
                return ("boss", self.boss)
            self.done = True             # a bossless zone: the crossing is the win
            self.last = f"{self.name} crossed!"
            return "arrived"
        # DANGER ROLLS BEFORE TREASURE (audit 2026-07-25): the find used to
        # shadow the hazard, so doubling FIND_CHANCE on a festival quietly
        # cut ambushes ~14% -- a festival must never make the road SAFER
        haz = self._roll_hazard()
        if haz is not None:
            self.last = "Something rustles ahead!"
            return ("hazard", haz)
        find = self._roll_find()
        if find is not None:
            key, present = find
            self.last = ("A present sits on the road!" if present
                         else "Something glints on the road.")
            return ("find", key, present)
        self.last = f"{self.name} — {self.pct}%"
        return "step"

    def resolve_boss(self, won: Any, fled: bool=False) -> Any:
        """Settle the gate boss.  won -> the zone is CONQUERED (done); fled ->
        turned back at the gate, no victory (not a failure); lost -> a life, and
        at 0 lives the run FAILS; 'retry' keeps the pet at the gate to try
        again.  Returns 'won' | 'fled' | 'lost'... 'retry' | 'failed'."""
        if won:
            self.done = True
            self.last = f"{self.boss_name} felled — {self.name} conquered!"
            return "won"
        if fled:
            self.last = f"Retreated from {self.boss_name}."
            return "fled"
        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
            self.failed = True
            self.last = f"{self.boss_name} was too strong."
            return "failed"
        unit = "life" if self.lives == 1 else "lives"
        self.last = f"Knocked back by {self.boss_name} — {self.lives} {unit} left."
        return "retry"
