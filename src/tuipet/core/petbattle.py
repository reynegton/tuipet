"""The pet's BATTLE ledger (tier-5, 2026-07-17): eligibility, the drill
result, record_battle's canon bookkeeping (wins/exp/KO6/setPower), and
the attribute-rank machinery."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from typing import Optional
from tuipet.i18n.translator import t
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


class BattleMixin:
    """State contract: the Pet dataclass fields; composed into Pet."""

    def _power_bonus_attr(self) -> Any:
        """set{Vaccine,Data,Virus}Power's bonus gate: the attribute whose gains
        a HAPPY pet doubles -- its own attribute (any stage), or for a None/
        Free-attribute pet past InTraining its EMERGENT favourite (the ledger
        drifts now; the AttributePreference seed stands in until one forms)."""
        if self.attribute in ("Vaccine", "Data", "Virus"):  # type: ignore
            return self.attribute  # type: ignore
        if self.stage in ("Fresh", "InTraining"):  # type: ignore
            return "None"
        return self.favorite_attr or self._phys().get("attr_pref", "None")  # type: ignore

    def _change_rank(self, cat: Any) -> None:
        """Taste.changeRank: bump the eaten category's rank (+/- species pref bias); eating
        your current favourite/disliked pulls the OTHER ranks back toward 0; clamp to
        +/-RankLimit; a rank that reaches the cap becomes the new favourite/disliked."""
        pref, aver, _ = self._species_food()  # type: ignore
        delta = RANK_CHANGE_FOOD
        if cat == pref:
            delta += RANK_PREF_INC
        elif cat == aver:
            delta -= RANK_PREF_INC
        if cat == self.disliked_food:  # type: ignore
            delta += RANK_DISLIKED
            for c in data.FOOD_CATEGORIES:                 # incRankExcept toward 0
                if c != cat and self.food_ranks[c] < 0:  # type: ignore
                    self.food_ranks[c] = min(0, self.food_ranks[c] + RANK_AFTER_FAV)  # type: ignore
        if cat == self.favorite_food:  # type: ignore
            for c in data.FOOD_CATEGORIES:                 # decRankExcept toward 0
                if c != cat and self.food_ranks[c] > 0:  # type: ignore
                    self.food_ranks[c] = max(0, self.food_ranks[c] - RANK_AFTER_FAV)  # type: ignore
        self.food_ranks[cat] = _clamp(self.food_ranks[cat] + delta, RANK_MIN, RANK_LIMIT)  # type: ignore
        for c in data.FOOD_CATEGORIES:
            if self.food_ranks[c] >= RANK_LIMIT:  # type: ignore
                self.favorite_food = c
            elif self.food_ranks[c] <= RANK_MIN:  # type: ignore
                self.disliked_food = c

    def _rank_stage_inc(self) -> Any:
        """RankChangeStage*Inc: young pets form tastes faster (+3/+2/+1)."""
        return RANK_STAGE_INC.get(self.stage, 0)  # type: ignore

    def _promote_attr_ranks(self) -> None:
        """A rank at +-RankLimit becomes the emergent favourite/disliked
        (simplified from Taste.setNewFavDislike like the food port: no
        repeat-collision reroll -- all three attributes are valid both ways)."""
        for a in self._ATTR3:  # type: ignore
            if self.attr_ranks[a] >= RANK_LIMIT and self.favorite_attr != a:  # type: ignore
                self.favorite_attr = a
                if self.disliked_attr == a:  # type: ignore
                    self.disliked_attr = ""
            elif self.attr_ranks[a] <= RANK_MIN and self.disliked_attr != a:  # type: ignore
                self.disliked_attr = a
                if self.favorite_attr == a:
                    self.favorite_attr = ""

    def _change_attr_rank(self, attr: Any) -> None:
        """Taste.changeRank for the attribute ledger: a drill warms the pet to
        its attribute (stage-scaled base, +-2 species preference/aversion
        bias); drilling the current favourite decays the others toward 0."""
        if attr not in self._ATTR3:  # type: ignore
            return
        req = self._phys()  # type: ignore
        delta = RANK_CHANGE_ATTR + self._rank_stage_inc()
        if attr == req.get("attr_pref", "None"):
            delta += RANK_PREF_INC
        elif attr == req.get("attr_aversion", "None"):
            delta -= RANK_PREF_INC
        if attr == self.disliked_attr:
            delta += RANK_DISLIKED
            for a in self._ATTR3:                          # type: ignore
                if a != attr and self.attr_ranks[a] < 0:  # type: ignore
                    self.attr_ranks[a] = min(0, self.attr_ranks[a] + RANK_AFTER_FAV)  # type: ignore
        if attr == self.favorite_attr:
            for a in self._ATTR3:                          # type: ignore
                if a != attr and self.attr_ranks[a] > 0:  # type: ignore
                    self.attr_ranks[a] = max(0, self.attr_ranks[a] - RANK_AFTER_FAV)  # type: ignore
        self.attr_ranks[attr] = _clamp(self.attr_ranks[attr] + delta, RANK_MIN, RANK_LIMIT)  # type: ignore
        self._promote_attr_ranks()

    def _dec_attr_rank(self, attr: Any, change: Any) -> None:
        """decRankAndCheckFavDislikeChange: a bad experience keyed to an
        attribute sours it (None = all three, like canon's disturb(None))."""
        for a in ([attr] if attr in self._ATTR3 else self._ATTR3):  # type: ignore
            self.attr_ranks[a] = _clamp(self.attr_ranks[a] - change, RANK_MIN, RANK_LIMIT)  # type: ignore
        self._promote_attr_ranks()

    def can_train(self) -> Any:
        """The source's drill gates (canon gates 2026-07-18, decompile
        L11697): a starving, sick, drained or filth-flanked pet refuses the
        drill with the head-shake.  (The energy line keeps the clone's own
        threshold -- too drained to SWING, a standing adaptation.)"""
        if (_g := self._guard()) is not None:  # type: ignore
            return _g
        if self.hunger <= 0:  # type: ignore
            self._set_anim("refuse", 1.0)  # type: ignore
            return t("train_too_hungry", "Com muita fome para treinar.")
        if self.sick:  # type: ignore
            self._set_anim("refuse", 1.0)  # type: ignore
            return t("train_too_sick", "Muito doente para treinar.")
        if self.injured:  # type: ignore
            # THE SECOND AILMENT GATES THE DRILL TOO (training audit
            # 2026-07-25).  Injury was restored 2026-07-23 and wired into
            # `battle_condition` -- a wounded pet cannot FIGHT -- but this
            # door predates it and only ever learned about sickness, so a
            # hurt pet was refused every bout and then sent to do timed
            # strike drills instead.  One ailment, one grammar; the cure is
            # free on the F menu, so this costs a tamer nothing but a key.
            self._set_anim("refuse", 1.0)  # type: ignore
            return t("train_too_hurt", "Muito machucado para treinar.")
        if self.poop:  # type: ignore
            self._set_anim("refuse", 1.0)  # type: ignore
            return t("train_clean_first", "Limpe primeiro!")
        if self.energy < TRAIN_ENERGY_COST:  # type: ignore
            self._set_anim("refuse", 1.0)  # type: ignore
            return t("train_too_tired", "Muito cansado para treinar.")
        if self.manners_refusal("train"):     # type: ignore
            return t("train_refuses", "{name} refuses to train!").replace("{name}", self.name)  # type: ignore
        return None

    def can_raid(self) -> Any:
        """The raid gate (tidy audit 2026-07-18: appactions hand-rolled its
        own dead/egg/asleep with third wordings, and a raid press was the
        one poke that DIDN'T disturb a sleeper).  Youth still outranks
        sleep -- a too-young pet is never woken just to be refused."""
        if (g := self._guard(asleep_blocks=False)) is not None:  # type: ignore
            return g
        if self.stage == "Fresh":  # type: ignore
            return t("raid_too_young", "Muito jovem para um raid.")
        if self.asleep:  # type: ignore
            return self._disturbed()  # type: ignore
        return None

    def can_adventure(self) -> Any:
        """The adventure gate (foundation 2026-07-20; tightened per its own
        note, audit 2026-07-25): dead/egg refused, a Fresh baby is too young,
        a sleeper is disturbed rather than served -- and the two body states
        the road can never answer gate HERE, because the world clock is
        parked mid-run: the pile or empty belly you leave with is exactly
        what the boss gate will refuse 40 legs later, with no road cure
        (measured: a guaranteed dead-end run).  SICK and HURT still embark
        -- the sick trudge is the authored road walk, and a town rest is
        their cure -- so their run is a pilgrimage, not a trap."""
        if (g := self._guard(asleep_blocks=False)) is not None:  # type: ignore
            return g
        if self.stage == "Fresh":  # type: ignore
            return t("adv_too_young", "Muito jovem para a aventura.")
        if self.asleep:  # type: ignore
            return self._disturbed()  # type: ignore
        if self.hunger <= 0:  # type: ignore
            return t("adv_too_hungry", "Too hungry for the road — eat first.")
        if self.poop:  # type: ignore
            return t("adv_clean_first", "Limpe antes de sair!")
        return None

    def max_health(self) -> Any:
        """PhysicalState.getMaxHealth: the trained-HP CAP rises with lapsed life."""
        days = self.age_seconds / DAY_LENGTH  # type: ignore
        for d, cap in HEALTH_CAP_LADDER:
            if days >= d:
                return cap
        return MAX_HEALTH_DEFAULT_CAP

    def _check_perfect_wins(self, force: bool=True) -> Any:
        """checkAndIncPerfectWins: every HP-drill success counts (force ==
        PracticeAlwaysIncPerfectWins TRUE) and every BATTLE WIN counts while the
        trained HP sits below its age cap (force=False rides canon's gate --
        Min{Strength,Hunger} are 0 at difficulty 0, so the HP-below-max clause
        is the whole test); each PerfectWinsLimit-th grows fullHealthPoints
        (HealthInc when it actually lands)."""
        if not force and self.full_health >= self.max_health():  # type: ignore
            return ""
        self.perfect_wins += 1  # type: ignore
        if self.perfect_wins % PERFECT_WINS_LIMIT == 0:  # type: ignore
            before = self.full_health  # type: ignore
            self.full_health = min(self.max_health(), self.full_health + PERFECT_WINS_HEALTH_INC)  # type: ignore
            if self.full_health > before:
                return " HP +1!"                     # State.HealthInc
        return ""

    def train_result(self, success: Any, grade: Optional[Any]=None) -> Any:
        """One clone drill (0.5 rules): energy -2 (floored at 0), the
        counters that feed the LINES TR gates, and a clean strike sheds a
        little weight.

        THREE GRADES, THREE TELLS (Joel 2026-07-25: "mon is showing happy
        pose after a normal training hit? wheres the frustration poses
        at???").  The bar grades mega/normal/miss but the verdict pose read
        one BOOLEAN, so a shoulder hit celebrated exactly like a perfect
        strike -- same cheer tableau, same cheer fx, only the sentence
        differed.  The ladder now lands where the shot did: a PERFECT
        strike cheers, a SOLID one sulks (the pet wanted the wall to
        break), a whiff slumps.  `grade` is optional so the sim-side
        callers that only care about the counters keep passing a bool."""
        self._calm_discipline_call()                 # type: ignore
        self.exercise_today += 1  # type: ignore
        self.stage_trainings += 1                    # type: ignore
        self.total_trainings += 1                    # type: ignore
        # the Effort meter fills per drill, win or lose (canon setExercise +1;
        # Joel 2026-07-17 "its not filling the effort meter?" -- the clone left
        # strength to the pill, but the gauge visibly ticking up per drill is
        # the shipped feel and the DM20 rule)
        self.strength = _clamp(self.strength + 1, 0, 4)  # type: ignore
        self._set_energy(max(0, self.energy - TRAIN_ENERGY_COST))  # type: ignore
        # the source sheds weight-2 on EVERY drill, win or lose (canon gates
        # 2026-07-18, decompile L11701) -- floored at the species BASE, not
        # at 1: the bare clone floor fattened a light classic pet (caught
        # live 2026-07-17; the adaptation stands)
        if self.weight > self._base_weight():  # type: ignore
            self._set_weight(max(self._base_weight(), self.weight - 2))  # type: ignore
        g = grade or ("mega" if success else "miss")
        if g == "mega":
            # the praise window opens for a CLEAN STRIKE only (Joel
            # 2026-07-25 "tighten"): it read `success`, so a shoulder hit
            # -- the one the pet now sulks over -- opened a proud moment
            self._open_praise()      # type: ignore
        # mega -> Cheering / normal -> the frustrated sulk (tantrum wears the
        # gloom-cloud emote) / miss -> the dejected slump
        self._set_anim({"mega": "happy", "normal": "tantrum"}.get(g, "sad"), 1.8)  # type: ignore
        return True

    def can_battle(self) -> Any:
        if self.dead:  # type: ignore
            return t("guard_dead", "Descansando agora — aperte N para um novo ovo.")
        if self.stage in ("Egg", "Fresh"):  # type: ignore
            return t("battle_too_young", "Muito jovem para lutar.")
        if self.asleep:  # type: ignore
            return self._disturbed()  # type: ignore
        self._calm_discipline_call()                         # type: ignore
        # the source's battle gates (canon gates 2026-07-18, decompile
        # L11746/11813): a starving, drained, sick or filth-flanked pet
        # refuses the fight with the head-shake
        if (cond := self.battle_condition()) is not None:
            self._set_anim("refuse", 1.0)  # type: ignore
            return cond
        if self.check_refused():                             # type: ignore
            return t("battle_refuses", "{name} refuses to fight!").replace("{name}", self.name)  # type: ignore
        if self.manners_refusal("battle"):    # type: ignore
            return t("battle_refuses", "{name} refuses to fight!").replace("{name}", self.name)  # type: ignore
        return None

    def battle_condition(self, check_energy: bool=True) -> Any:
        """The PURE condition half of can_battle -- no disturb, no anim, no
        refusal roll.  ONE source for every recorded bout: the cup and the
        invite-accept side used to skip these entirely, so a pet too
        starved/sick/drained to SEND a challenge could still grind three
        recorded cup battles per cup and auto-accept incoming invites
        (gameplay audit 2026-07-19).

        ⚠ `check_energy=False` IS FOR THE ROAD, AND ONLY THE ROAD
        (adventure audit 2026-07-25).  The ENERGY clause is a HOME door's
        rule: it keeps a drained pet from picking new fights while it has
        a bed, a shop and a full larder within reach.  The road has its
        OWN energy law, ruled 2026-07-23 (adventure energy audit, D3): a
        spend floors at 0, fighting on empty is allowed and billed through
        the hit formula's condition term, and only a hazard KNOCK pushes
        past empty to plant the feet.  Handing the road the home clause
        made the two laws contradict -- and measurably so: a 40-leg march
        costs 10 energy and ~8 wilds cost 5 each, so **86 of 86 simulated
        arrivals reached the gate under the threshold** and the boss
        became unreachable.  The BODY states (starving / sick / hurt /
        filthy) still hold everywhere, because those are the device's."""
        if self.hunger <= 0:  # type: ignore
            return t("battle_too_hungry", "Com muita fome para lutar.")
        if check_energy and self.energy < BATTLE_MIN_ENERGY:  # type: ignore
            return t("battle_too_drained", "Sem energia para lutar.")
        if self.sick:  # type: ignore
            return t("battle_too_sick", "Muito doente para lutar.")
        if self.injured:  # type: ignore
            # the second ailment gates like the first (canon restoration
            # 2026-07-23: a wounded device pet cannot battle)
            return t("battle_too_hurt", "Muito machucado para lutar.")
        if self.poop:  # type: ignore
            return t("train_clean_first", "Limpe primeiro!")
        return None

    def record_battle(self, won: Any, enemy: Optional[Any]=None, online: bool=False,
                      free_style: Optional[Any]=None, low_health: bool=False) -> Any:
        """One battle, the 0.5 rules (clone record_battle, 2026-07-17):
        counters + flat costs, +2 trainings for a LOCAL bout.  The
        progression channels the rest of the game feeds on: battle_log
        (Pen20 WIN gates), stage_battles (BTL gates), lifetime wins + the
        mystery-egg note, levels_fought, KO6, and the win's +1 power in the
        foe's attribute (a 0.5 card's attribute string names the dominant
        power directly).  ONLINE PvP IS PROGRESSION-NEUTRAL (L17 ruling,
        Joel 2026-07-20, option a): exp and KO6 always excluded it as
        untrusted -- colluding tamers, forged cards -- and the same
        collusion farmed the channels that stayed fed; an online bout now
        bills the BODY only (energy/weight; its purse and ladder standing
        live server-side).  battles+wins move together so win_rate stays
        coherent.  The old free_style/low_health params are
        accepted-and-ignored for stragglers.  (Mood/compliance/contagion
        legs left with their systems; the perfect-wins HP ladder left with
        the classic battle.)

        ⭐`online` IS THE ONE DOOR to those rules (the `source="pvp"`
        alias was CUT 2026-07-25 on Joel's order, battle audit §5).  Two
        ways to say the same thing meant two places to get it wrong, and
        only one of them was ever used: the lobby -- the single caller
        that fights online -- has always passed `online=True`.  The
        anti-farm guarantee it protects is unchanged and still pinned
        (a duel's Mega must never reach the KO6 counter); it now has
        exactly one spelling."""
        # the injury roll judges the body the pet FOUGHT with -- read the
        # condition BEFORE the bout bills it (the weight bill floors to
        # base, which would erase the very drag that made the fight risky)
        _inj_bad = (self.hunger <= 1 or self.energy < BATTLE_MIN_ENERGY  # type: ignore
                    or abs(self.weight - self._base_weight()) >= 8 or self.sick)  # type: ignore
        # a battle SPENDS energy, so it floors at 0 (the energy floor law,
        # D3 ruling 2026-07-23 -- adventure.py's constants block): only a
        # hazard KNOCK pushes past empty.  Fighting on empty still bills the
        # body through the hit formula (Side._condition's energy term).
        self._set_energy(max(0, self.energy - BATTLE_ENERGY_COST))  # type: ignore
        # floored at the species BASE, not at 1 (weight floor law -- the
        # SAME ruling training got 2026-07-17 and the march drain always
        # had; battles were the one sink still grinding to a skeleton.
        # Caught live 2026-07-23: Joel's 52-bout Greymon ground from base
        # 40g to 10g = the MAX weight penalty, -0.10 vs every ideal
        # wild's +0.10 -- a hidden 20-point swing that ate his mega lock
        # and read as "still getting my ass handed to me")
        self._set_weight(max(self._base_weight(), self.weight - BATTLE_WEIGHT_COST))  # type: ignore
        if online:
            return ""
        self.battles += 1  # type: ignore
        self.stage_battles += 1                          # type: ignore
        self.battle_log = (self.battle_log + [1 if won else 0])[-15:]   # type: ignore
        # THE NAMED RIVAL's ledger (Joel 2026-07-26): a rival bout tallies
        # the head-to-head here — the ONE recording source, local bouts
        # only (the `online` return above keeps L17 duels out).  The tally
        # rides the pet save, so the feud dies with the generation.
        if isinstance(enemy, dict) and enemy.get("rival"):
            if won:
                self.rival_wins += 1  # type: ignore
            else:
                self.rival_losses += 1  # type: ignore
        # A BOUT TRAINS, ON BOTH CLOCKS (Joel 2026-07-25: "feed the
        # total_trainings thing too, flip it").  The +2 is the clone rule;
        # what the battle audit found was that only the STAGE counter got
        # it, so fighting fed the TR evolution gate and the hit formula's
        # +10% term while the lifetime +20% term -- the bigger of the two
        # -- sat still no matter how much a pet fought.  The drill has
        # always fed both 1:1; a bout now does the same at its own rate.
        self.stage_trainings += 2  # type: ignore
        self.total_trainings += 2  # type: ignore
        # THE INJURY ROLL (canon restoration 2026-07-23): battles can
        # wound -- the second ailment the 2026-07-16 strip wrongfully
        # took.  Adapted BattleInjury table (petbase); LOCAL bouts only
        # (online stays L17 body-billing).  A healthy winner risks 0.3%,
        # an unhealthy loser ~16%; a live vitamin is the canon guard.
        if not self.injured:  # type: ignore
            vit = getattr(self, "vitamin_lapse", 0.0) > 0
            key = ("bad_" if _inj_bad else "good_") + ("v" if vit else "nv")
            chance = BATTLE_INJ_TABLE[key]  # noqa: F405
            if not won:
                chance += BATTLE_INJ_LOSS  # noqa: F405
            if self.stage == "InTraining" or self.age_seconds >= 15 * 86400:  # type: ignore
                chance += BATTLE_INJ_BAD_AGE  # noqa: F405
            if chance and random.random() < chance / BATTLE_INJ_BOUND:  # noqa: F405
                self.injured = True
                self.injuries += 1                       # type: ignore
                # canon injLapse: the wound also carries how long it takes
                # to heal on its own (P4 ruling 2026-07-23) -- the Bandage
                # skips the wait, it is no longer the only cure
                self.inj_length = random.randint(
                    MIN_INJ_LENGTH, MAX_INJ_LENGTH) * INJ_LAPSE_MIN  # noqa: F405
        if not won:
            return ""
        self.wins += 1  # type: ignore
        self._open_praise()          # type: ignore
        # DMX canon: defeating an enemy pays experience toward LEVEL (the
        # LV line gates)
        self.exp += EXP_PER_WIN  # type: ignore
        import tuipet.utils.persistence as _persist
        total = _persist.wins_add(1)                     # lifetime wins (egg gates)
        if total in egg_mod.wins_thresholds():
            # a lifetime-wins egg gate just crossed (Zuba 75 / Hack 40 / V 25 /
            # Sakumon 50 / Chibickmon 10...): flash the nursery note
            self.egg_unlock_note = "Um novo ovo apareceu no ninho!"
        if enemy:
            self.levels_fought.append(_enemy_level(enemy))  # type: ignore
            # KO6: Stage VI is Mega, full stop (online never reaches here
            # since the L17 ruling; the old per-line PvP guard is subsumed)
            if enemy.get("stage") == "Mega":
                self.mega_kills += 1                     # type: ignore
                _persist.mega_kills_add(1)               # ...and the X-egg progress
            # the win grows the pet's power in the foe's attribute (+1; a
            # HAPPY pet's favoured attribute doubles it, canon setPower)
            dom = enemy.get("attribute")
            if dom in self._ATTR3:  # type: ignore
                inc = 1
                if self.current_mood() == "Feliz" and dom == self._power_bonus_attr():  # type: ignore
                    inc += BONUS_ATTRIBUTE_POWER
                if dom == "Vaccine":
                    self.vaccine += inc  # type: ignore
                elif dom == "Data":
                    self.data_power += inc  # type: ignore
                else:
                    self.virus += inc  # type: ignore
        return "training +2"

    def can_escape(self, enemy: Any) -> Any:
        """PhysicalState.canEscape: a power-weighted roll -- prob = nextInt(mine +
        theirs); escaped iff prob <= mine, the foe's side padded by
        BossEscapeChance 50 / RandomEscapeChance 10 (bosses hold you harder)."""
        mine = self.vaccine + self.data_power + self.virus + (self.full_health or 1)  # type: ignore
        theirs = (enemy.get("vaccine", 0) + enemy.get("data_power", 0)
                  + enemy.get("virus", 0) + enemy.get("hp", 0)
                  + (50 if enemy.get("boss") else 10))     # Boss/RandomEscapeChance
        return random.randrange(max(1, mine + theirs)) <= mine

    def check_surrender(self, health: Any, enemy_health: Any, enemy_max_health: Any, full_hp: Any) -> Any:
        """Always 0 (fight on): the pet-initiated surrender/flee rode the
        obedience formula and left with the discipline system (BASIC VPET
        2026-07-16).  The PLAYER's surrender option stands."""
        return 0

    def surrender_effect(self, surrender_val: Any, health: Any, enemy_health: Any) -> None:
        """ClockTic.surrenderEffect: the morale aftermath when the pet gives up (1) or
        its surrender request is accepted (2)."""
        if health >= enemy_health:
            self._set_obedience(self.obedience  # type: ignore
                                - (SURR_EFFECT_REQ_OBED_DEC if surrender_val == 2 else SURR_EFFECT_OBED_DEC))
        if surrender_val == 2 and health < enemy_health:
            self._set_obedience(SURR_EFFECT_REQ_LOWHP_OBED)      # type: ignore

    def surrender_reject(self) -> None:
        """ClockTic: the trainer refuses the pet's surrender request (surrender==2) and
        sends it back in — it sulks but obeys a touch more.  If it then LOSES,
        battleEnd SETS obedience to 10 (the declined-request grudge).

        DORMANT since the 0.5 BATTLE rewrite (2026-07-17): nothing calls this
        cluster (surrender_reject / surrender_effect / check_surrender /
        can_escape), record_battle never reads _surr_declined, and
        SURR_DECLINED_LOST_OBED is unapplied -- the old comment claimed
        otherwise (gameplay audit 2026-07-19).  Kept as the canon reference
        for a battle flow that asks again; dormant stays dormant."""
        self._set_obedience(self.obedience + SURR_REJECT_OBED_INC)  # type: ignore
        self._surr_declined = True                       # no live consumer (see above)

