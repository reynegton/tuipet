from __future__ import annotations

import tuipet.ui.screens.adventurescreen as adventurescreen
import tuipet.ui.screens.backgroundscreen as backgroundscreen
import tuipet.ui.screens.battlescreen as battlescreen
import tuipet.ui.screens.dnascreen as dnascreen
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.core.rival as rival
import tuipet.ui.screens.shopscreen as shopscreen
import tuipet.ui.screens.tournamentscreen as tournamentscreen
import tuipet.core.tournament as tournament

import tuipet.data.loaders.data as data
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
from tuipet.core.pet import Pet
import tuipet.ui.screens.lobbyscreen as lobbyscreen
class NavActionsMixin:
    def action_inventory(self):
            self._open_mode(shopscreen.ShopPanel(self.pet, start_mode="bag"), self._after_shop)

    def action_eggguide(self):
            import tuipet.ui.screens.eggguidescreen as eggguidescreen
            self._open_mode(eggguidescreen.EggGuidePanel(self.pet), lambda _=None: self.repaint())

    def action_datacore(self):
            import tuipet.ui.screens.datacorescreen as datacorescreen
            self._open_mode(datacorescreen.datacorePanel(self.pet), self._after_datacore)

    def _after_datacore(self, msg):
            import tuipet.ui.screens.datacorescreen as datacorescreen
            import tuipet.ui.screens.albumscreen as albumscreen
            if isinstance(msg, tuple) and msg and msg[0] == "hall":
                self._open_mode(albumscreen.AlbumPanel(self.pet),
                                lambda _=None: self._open_mode(
                                    datacorescreen.datacorePanel(self.pet, start="TROPHIES"),
                                    self._after_datacore))

    def _after_title(self, _=None):
            # The account wall used to stand HERE: name + password demanded on
            # first launch, before the player had seen a single pet (sweep
            # 2026-07-14).  The account only matters online -- the lobby asks for
            # one when it's first opened, and sync starts on the next autosave.
            self._post_title()

    def action_battle(self):
            # DM20's battle icon as a first-class action (Joel 2026-07-23
            # "should we add battles action... like dm20 does it?" -> "yeah
            # lets do it"): a REAL recorded bout -- wins/exp/KO6/log/+2
            # trainings, exactly like a road wild -- against a tier-matched
            # rival (battle.pick_enemy, same stage bracket), with NO purse:
            # adventure stays the earning game, and energy is the pacer
            # (entry gates >= 10, each bout bills -5, ~3 per full tank).
            # can_battle is the ONE gate: dead / too young / asleep-wake /
            # starved / drained / sick / filth + the soft refusal roll.
            err = self.pet.can_battle()
            if err:
                self._do(err); return
            import tuipet.ui.screens.battlescreen as battlescreen
            # THE NAMED RIVAL answers every 3rd bout (Joel 2026-07-26): its
            # card rides the ordinary Battle engine — same bracket, ideal
            # condition, no purse — only the NAME changes.  A rival bout wears
            # the arena backdrop (enemy != None flips it; presentation only).
            import tuipet.core.rival as rival
            foe = rival.maybe_challenge(self.pet)
            if foe is not None:
                self.flash(f"[b]{foe['tamer']}[/] te desafia — "
                           f"{foe['name']} steps up!")
            self._open_mode(battlescreen.BattlePanel(self.pet, enemy=foe),
                            self._after_battle)

    def _after_battle(self, b):
            # the post-bout emotional beat rides the HOUSE screen, the cup's
            # grammar (_after_cup): cheer a win home, sulk a loss.  b is None
            # when the pet walked away before the bell -- nothing happened.
            if (b is not None and getattr(b, "over", False)
                    and self.screen_w.fx is None and not self.pet.dead):
                if (getattr(b, "enemy", None) or {}).get("rival"):
                    # the feud's running score lands with the verdict
                    self.flash(f"[b]{rival.record_line(self.pet)}[/] no total")
                self.screen_w.start_fx("cheer" if b.won else "losing")
            self.repaint()


    def _after_cup(self, msg):
        verdict = None
        if isinstance(msg, tuple):           # (last, champion) from a played bracket
            msg, verdict = msg
        if msg:
            self.flash(msg)
        # the post-cup emotional beat rides the HOUSE screen (anim hardening
        # 2026-07-14: every reference celebrates a win / sulks a loss back
        # home for a few seconds; tuipet's losing() fx sat built but unwired)
        if verdict is not None and self.screen_w.fx is None and not self.pet.dead:
            self.screen_w.start_fx("cheer" if verdict else "losing")
        self.repaint()

    def action_tournament(self):
            err = tournament.can_enter(self.pet)   # single source of entry gating (young/asleep/no-cup)
            if err:
                self._do(err); return
            self.pet.tourney_alert = False         # answering the call silences it
            self._open_mode(tournamentscreen.TournamentPanel(self.pet), self._after_cup)

    def action_dna(self):
            reason = self.pet.can_charge_dna()
            if reason:
                self._do(reason); return
            self._open_mode(dnascreen.DNAPanel(self.pet), self._after_dna)

    def _after_dna(self, result=None):
            self.autosave()
            if isinstance(result, tuple) and result and result[0] == "charged":
                _, field, amount = result          # DVPet applyDNA -> DNA_Feeding -> main view
                self.screen_w.start_fx("dna_charge", icon=field, pet=self.pet)
                self.beep("compatible", bell=False)   # the DNA charge/absorb beep (no dedicated dna rip)
                self.flash("%s absorveu %d DNA de %s" % (self.pet.name, amount, data.pretty_field(field)))
            else:
                self.repaint()

    def action_scenes(self):
            """The E scene picker (restored 2026-07-17): egg default, pick overrides."""
            self._open_mode(backgroundscreen.BackgroundPanel(self.pet), self._after_scenes)

    def _after_scenes(self, msg):
            if msg:
                self.flash(msg)
            self.repaint()

    def action_shop(self):
            self._open_mode(shopscreen.ShopPanel(self.pet), self._after_shop)

    def _after_shop(self, msg):
            if isinstance(msg, tuple) and msg and msg[0] == "eat":
                if len(msg) > 2 and msg[2]:
                    self.flash(msg[2])               # the meal's verdict text
                self.screen_w.start_fx("eat", msg[1], pet=self.pet,
                                       starving=getattr(self.pet, "_last_meal_starving", False))
            elif isinstance(msg, tuple) and msg and msg[0] == "evolve":
                # _evolve sounds INSIDE the strobe (fx snds beat 5), like DVPet evolveAnim.
                # msg[2] = an ItemEvol's key: the Relic's icon frames head the
                # strobe with canon itemEvolve's parade
                ik = msg[2] if len(msg) > 2 else None
                self.flash(self._evolve_msg(msg[1]))
                self.screen_w.start_fx("evolve", old_num=msg[1], icon=ik)
            elif isinstance(msg, tuple) and msg and msg[0] == "play":
                # the Trampoline (Jump): DVPet jumping() -- the pet hops over it
                self.screen_w.start_fx("play", icon=msg[1])
            elif isinstance(msg, tuple) and msg and msg[0] == "item_use":
                # every other AnimationType plays its own canon script (itemfx)
                if len(msg) > 3 and msg[3]:
                    self.flash(msg[3])               # the toy's verdict text
                self.screen_w.start_fx("item", icon=msg[1], script=msg[2])
            elif isinstance(msg, tuple) and msg and msg[0] == "inherit":
                mem = msg[1]
                self.flash(f"[b]{mem.get('name', '?')}[/]'s power lives on!  "
                           f"Va+{mem.get('vaccine', 0)} D+{mem.get('data', 0)} Vi+{mem.get('virus', 0)}")
                self.screen_w.start_fx("inherit", pet=self.pet)
                self.screen_w.fx["ancestor"] = mem.get("num", -1)
            elif msg:
                self.flash(msg)
            self.repaint()

    def action_adventure(self):
            import tuipet.ui.screens.adventurescreen as adventurescreen
            reason = self.pet.can_adventure()   # single-source gate, like raid/train/cup
            if reason:
                self._do(reason); return
            # the zone picker first: choose an UNLOCKED zone, then embark
            self._open_mode(adventurescreen.ZonePickPanel(self.pet), self._after_zone_pick)

    def _after_adventure(self, msg):
            # safety net: however the mode closed, the pet is HOME now -- the
            # away flag (assistant billing / filth / gift-call gates + the
            # status card's @ line) must never survive the room
            self.pet.away = False
            self.pet.away_where = ""
            if msg:
                self.flash(msg)
            self.autosave()
            self.repaint()


    def action_raid(self):
        import tuipet.ui.screens.raidscreen as raidscreen
        reason = self.pet.can_adventure()
        if reason:
            self._do(reason); return
        self._open_mode(raidscreen.RaidPanel(self.pet, self._sync), self._after_raid)

    def _after_raid(self, msg):
        if self.pet:
            self.pet.away = False
            self.pet.away_where = ""
        if self._lobby_worker:
            self._lobby_worker.cancel()
            self._lobby_worker = None
        if getattr(self, "_sync", None):
            self._sync.lobby_disconnect()
        self.autosave()

    def action_lobby(self):
        import tuipet.ui.screens.lobbyscreen as lobbyscreen
        from tuipet.network.net import LobbyClient
        if not self._sync:
            self.flash("Lobby indisponível")
            return
        reason = self.pet.can_adventure()
        if reason and "jovem" not in reason.lower() and "ovo" not in reason.lower():
            self._do(reason); return
        self.pet.away = True
        self.pet.away_where = "no lobby"
        host = lobbyscreen.LobbyPanel(self.pet, LobbyClient)
        self._open_mode(host, self._after_lobby)

    def _after_lobby(self, msg):
        if self.pet:
            self.pet.away = False
            self.pet.away_where = ""
        if self._lobby_worker:
            self._lobby_worker.cancel()
            self._lobby_worker = None
        if getattr(self, "_sync", None):
            self._sync.lobby_disconnect()
        self.autosave()

    def _after_zone_pick(self, zone):
        if zone:
            import tuipet.ui.screens.adventurescreen as adventurescreen
            self._open_mode(adventurescreen.AdventurePanel(self.pet, zone), self._after_adventure)
