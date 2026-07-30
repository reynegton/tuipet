"""The app's ACTION handlers (tier-3 split, 2026-07-17): every key on
the actions bar — the action_* entry, its _after_* close-callback, and the
_do result-flash — as a mixin over TuiPetApp's state (screen_w/stats_w/
mode/pet/_open_mode).  app.py keeps the shell: widgets, the 10Hz clock,
repaint, mode plumbing."""
from __future__ import annotations

import random  # noqa: F401

import tuipet.ui.screens.albumscreen as albumscreen    # noqa: F401
import tuipet.ui.screens.assistscreen as assistscreen    # noqa: F401
import tuipet.ui.screens.backgroundscreen as backgroundscreen    # noqa: F401
import tuipet.ui.screens.bugscreen as bugscreen    # noqa: F401
import tuipet.data.loaders.data as data    # noqa: F401
import tuipet.ui.screens.deathscreen as deathscreen    # noqa: F401
import tuipet.ui.screens.datacorescreen as datacorescreen    # noqa: F401
import tuipet.ui.screens.dnascreen as dnascreen    # noqa: F401
import tuipet.core.egg as egg_mod    # noqa: F401
import tuipet.ui.screens.eggguidescreen as eggguidescreen    # noqa: F401
import tuipet.ui.screens.eggselectscreen as eggselectscreen    # noqa: F401
import tuipet.ui.screens.feedscreen as feedscreen    # noqa: F401
import tuipet.ui.screens.hallscreen as hallscreen    # noqa: F401
import tuipet.core.rival as rival    # noqa: F401
import tuipet.ui.screens.helpscreen as helpscreen    # noqa: F401
import tuipet.ui.screens.lobbyscreen as lobbyscreen    # noqa: F401
import tuipet.network.net as net    # noqa: F401
import tuipet.utils.persistence as persistence    # noqa: F401
import tuipet.ui.screens.shopscreen as shopscreen    # noqa: F401
import tuipet.ui.components.statusbox as statusbox    # noqa: F401
import tuipet.utils.theme as theme    # noqa: F401
import tuipet.ui.screens.titlescreen as titlescreen

from tuipet.i18n.translator import t    # noqa: F401
import tuipet.core.tournament as tournament    # noqa: F401
import tuipet.ui.screens.tournamentscreen as tournamentscreen    # noqa: F401
import tuipet.core.training as training    # noqa: F401
import tuipet.ui.screens.optionsscreen as optionsscreen    # noqa: F401
from tuipet.appboot import _lobby_uri    # noqa: F401
from tuipet.core.pet import Pet    # noqa: F401


class ActionsMixin:
    """State contract: self.pet / self.mode / self.screen_w / self.stats_w /
    self._open_mode / self._close_mode / self.flash / self.repaint."""

    def _after_title(self, _=None):
        # The account wall used to stand HERE: name + password demanded on
        # first launch, before the player had seen a single pet (sweep
        # 2026-07-14).  The account only matters online -- the lobby asks for
        # one when it's first opened, and sync starts on the next autosave.
        self._post_title()

    def _after_death(self, result):
        if result == "new":
            self.action_new()
        else:
            self.repaint()

    def _after_egg_pick(self, egg_type):
        if egg_type is None:                       # backed out -> return to the title
            self._open_mode(titlescreen.TitlePanel(), self._after_title)
            return
        if egg_type == "guide":                    # N: consult the egg guide, then
            self._open_mode(eggguidescreen.EggGuidePanel(self.pet),   # come back
                            lambda _=None: self._open_mode(
                                eggselectscreen.EggSelectPanel(self.pet),
                                self._after_egg_pick))
            return
        self._new_game = False                     # the fresh start is settled
        self.pet = Pet.new_egg(egg_type=egg_type)
        self._grant_memory(self.pet)
        note = getattr(self, "_boot_notice", "")   # a quarantined save's warning
        self._boot_notice = ""                     # rides THIS flash (title audit
        self.flash((note + "  ·  " if note else "")  # 2026-07-19) -- it marquees
                   + "Take good care of your egg!  (? = help)")
        self.repaint()

    # ---- multiplayer lobby ----------------------------------------------
    def action_help(self):
        self._open_mode(helpscreen.HelpPanel(self.pet), lambda _=None: self.repaint())

    def action_bug(self):
        self._open_mode(bugscreen.BugReportPanel(self.pet), self._after_bug)

    def _after_bug(self, result=None):
        if isinstance(result, tuple) and result and result[0] == "bug":
            name = persistence.get_account()[0] or ""
            self.run_worker(self._send_bug(result[1], self._bug_meta(), name),
                            name="bug", exclusive=False)
            self._hud("Sending your report\u2026")
        self.repaint()

    def action_lobby(self):
        if self.mode is not None:
            return
        # TODO: Estudar a comunicação de rede do servidor gringo original e manter a compatibilidade
        # dos envios/recebimentos para reativar o multiplayer futuramente.
        self._hud(t("msg_multiplayer_disabled", "Multiplayer desativado"))
        self.repaint()

    def _lobby_connect(self, name, pw, card):
        """Create + start the WebSocket client; the app owns its worker lifecycle."""
        persistence.set_account(name, pw)
        uri = _lobby_uri()
        client = net.LobbyClient(uri, name, pw, card)
        self._lobby_worker = self.run_worker(client.run(), name="lobby", exclusive=False)
        return client

    def _drop_lobby_worker(self):
        """Cancel the live LobbyClient worker (one teardown for every panel
        that logs in through _lobby_connect -- the raid left ITS worker
        running, and the next lobby login orphaned it: two sessions on one
        BOOT evicting each other in a reconnect loop for the rest of the
        run; gameplay audit 2026-07-19)."""
        w = getattr(self, "_lobby_worker", None)
        if w is not None:
            w.cancel()
            self._lobby_worker = None

    def _after_lobby(self, result=None):
        # The lobby panel applies its own jogress/battle results in-place (you stay
        # in the lobby between sessions), so here we just tear down the connection.
        self._drop_lobby_worker()
        self.repaint()

    def action_quit(self):
        persistence.save(self.pet)
        self.exit()

    def action_options(self):
        """The OPTIONS menu gathers the app-level switches (theme / sound /
        account / update / keys / new egg / erase) under one key -- g/m/n gave
        the action bar its breathing room back (Joel 2026-07-04)."""
        if self.mode is not None:
            return
        self._open_mode(optionsscreen.OptionsPanel(
            self.pet, lambda: self.sound, self._toggle_sound,
            on_theme_change=self._restyle,
            bindings=self.BINDINGS,
            update_hint=lambda: getattr(self, "_update_msg", ""),
            verdict=self._verdict),
            self._after_options)

    def _after_options(self, result):
        self._restyle()                             # a previewed theme may have settled
        if result and result[0] == "restart":
            # the update's restart offer: save, leave Textual cleanly, and
            # main() re-execs the NEW code once the terminal is restored
            self.autosave()
            self._restart_after_exit = True
            self.exit()
            return
        if result and result[0] == "new":
            self.action_new()
            return
        if result and result[0] == "account":
            self.run_worker(self._switch_account(result[1], result[2]),
                            name="switch", exclusive=False)
            return
        if result and result[0] == "erase":
            self._stop_sync()                       # the pusher must not re-seed the cloud
            persistence.erase_all()
            self.pet = Pet.new_egg()                # placeholder until the carousel picks
            # a fresh start IS a new game: without this flag the post-title flow
            # skipped the egg-select carousel and kept the placeholder egg
            # (Joel 2026-07-05: "automatically selected an egg for me??")
            self._new_game = True
            self._open_mode(titlescreen.TitlePanel(), self._after_title)
            self.flash("Todos os dados apagados — um novo começo.")
            return
        self.repaint()

    def _do(self, result):
        self.flash(result)
        self.repaint()

    def action_feed(self):
        if self.screen_w.fx is not None:        # let the current care animation finish before acting again
            return
        reason = self.pet.can_feed()            # egg/asleep/dead -> flash the reason, no menu
        if reason:
            self._do(reason); return
        self._open_mode(feedscreen.FeedPanel(self.pet), self._after_feed)

    def _after_feed(self, result):
        # result: ("fed"|"full"|"refused", food, msg); None on cancel.  A refusal
        # plays no food fx -- the refuse pose (State.Refusing) is already on the pet
        if not result:
            self.repaint(); return
        outcome, food, msg = result
        icon = food.get("key", "f:0")               # the food's REAL icon rides the eat fx
        # eat(): the wolf-down modifier is decided BEFORE the meal (a starving
        # pet that just ate has hunger>0 -- reading it here was always False)
        starving = getattr(self.pet, "_last_meal_starving", False)
        if outcome == "fed" and self.pet.anim == "eat":
            self.screen_w.start_fx("eat", icon, pet=self.pet, starving=starving)   # SFX per-bite in the fx loop
        elif outcome == "healed":
            # the pill is EATEN (decompile EATING state): the same eat fx as
            # meat, on the ripped pill bite strip (pill-anim fix 2026-07-18)
            self.screen_w.start_fx("eat", icon, pet=self.pet)
        elif outcome == "full":
            self.screen_w.start_fx("spit", icon)  # _refuse fires on each head-shake (fx snds)
        self._do(msg)

    def action_train(self):
        reason = self.pet.can_train()
        if reason:
            self._do(reason); return
        self._open_mode(training.TrainingPanel(self.pet), self._after_train)

    def _after_train(self, msg):
        if msg:
            self.flash(msg)
        # DVPet onExerciseFinish: success -> setPraise(true) -> the cheer(true) fx;
        # anything less -> State.Jeering -> jeer(true, _angry).  train_result left
        # the verdict in pet.anim (the sim is paused while the drill is open, so
        # it's still fresh here).  THREE GRADES, THREE TELLS (Joel 2026-07-25):
        # a PERFECT strike cheers, a SOLID hit grumbles the deserved 4/6 jeer,
        # a whiff takes the deeper 10/9 slump -- the boolean used to cheer the
        # middle grade like a perfect one.
        if self.pet.anim == "happy":
            self.screen_w.start_fx("cheer")
        elif self.pet.anim == "tantrum":
            self.screen_w.start_fx("jeer")
        elif self.pet.anim == "sad":
            self.screen_w.start_fx("jeer", good=False)
        elif self.pet.anim == "refuse":
            # canon canExercise: _refused -> State.Refusing -- the head-shake plays
            # back on the LCD after onPreTrain dumps the menu (spit == refuse(); no icon)
            self.screen_w.start_fx("spit")
        self.repaint()

    def action_discipline(self):
        # praise & scold, RESTORED (canon restoration B, 2026-07-23).
        # The asleep poke follows the care-key law: wake + refuse this
        # press; youth outranks sleep like every other gate.
        import tuipet.ui.screens.disciplinescreen as disciplinescreen
        p = self.pet
        if (g := p._guard(asleep_blocks=False)) is not None:
            self._do(g); return
        if p.stage in ("Egg", "Fresh"):
            self._do("Muito novo para lições."); return
        if p.asleep:
            self._do(p._disturbed()); return
        self._open_mode(disciplinescreen.DisciplinePanel(p),
                        self._after_discipline)

    def _after_discipline(self, result):
        # the lesson's emotional beat rides the HOUSE screen, the same
        # grammar every other verdict uses (_after_cup / _after_battle /
        # the drill's cheer/jeer): a landed PRAISE cheers, a landed SCOLD
        # jeers, and a wrong-moment verb shows only its small pose --
        # nothing happened, so nothing plays (E1, Joel 2026-07-23:
        # "praise and scold should have happy and sad animations").
        msg, show = result if isinstance(result, tuple) else (result, None)
        if msg:
            self.flash(msg)
        if show and self.screen_w.fx is None and not self.pet.dead:
            self.screen_w.start_fx(show)
        self.repaint()

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

    def action_tournament(self):
        err = tournament.can_enter(self.pet)   # single source of entry gating (young/asleep/no-cup)
        if err:
            self._do(err); return
        self.pet.tourney_alert = False         # answering the call silences it
        self._open_mode(tournamentscreen.TournamentPanel(self.pet), self._after_cup)

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

    def action_inventory(self):
        self._open_mode(shopscreen.ShopPanel(self.pet, start_mode="bag"), self._after_shop)

    def action_assist(self):
        self._open_mode(assistscreen.AssistPanel(self.pet), self._after_assist)

    def _after_assist(self, msg=None):
        if msg:
            self.flash(msg)       # the hire/dismiss verdict rides home
        self.repaint()

    def action_eggguide(self):
        # the egg unlock book -- read-only, safe at any stage
        self._open_mode(eggguidescreen.EggGuidePanel(self.pet), lambda _=None: self.repaint())

    def action_datacore(self):
        self._open_mode(datacorescreen.datacorePanel(self.pet), self._after_datacore)

    def _after_datacore(self, msg):
        if isinstance(msg, tuple) and msg and msg[0] == "album":
            # TROPHIES' ENTER: browse the album, then come back to the shelf
            # it opened from (the egg-guide-from-carousel round-trip shape)
            self._open_mode(albumscreen.AlbumPanel(self.pet),
                            lambda _=None: self._open_mode(
                                datacorescreen.datacorePanel(self.pet, start="TROPHIES"),
                                self._after_datacore))
            return
        if isinstance(msg, tuple) and msg and msg[0] == "hall":
            # LEGACY's ENTER: walk the hall of memory, then back to the
            # headstone shelf (the album round-trip's exact shape)
            self._open_mode(hallscreen.HallPanel(self.pet),
                            lambda _=None: self._open_mode(
                                datacorescreen.datacorePanel(self.pet, start="LEGACY"),
                                self._after_datacore))
            return
        if isinstance(msg, tuple) and msg and msg[0] == "evolve":
            # modeChange -> State.Evolving: the same strobe as any evolution
            self.flash(f"[b]{msg[2] if len(msg) > 2 else 'MUDANÇA DE MODO!'}[/]")
            self.screen_w.start_fx("evolve", old_num=msg[1])
        self.repaint()

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

    def _after_zone_pick(self, zone):
        if not zone:
            self.repaint(); return          # backed out of Adventure
        import tuipet.ui.screens.adventurescreen as adventurescreen
        self._open_mode(adventurescreen.AdventurePanel(self.pet, zone=zone),
                        self._after_adventure)

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
        self._hud(t("msg_raid_disabled", "Raid desativada"))
        self.repaint()

    def _after_raid(self, msg):
        if msg:
            self.flash(msg)
        self._drop_lobby_worker()   # the raid's login is LIVE: never leak it
        self.autosave()
        self.repaint()

    def action_gift(self):
        if self.mode is not None or self.screen_w.fx is not None or not self.pet.gift:
            return
        key = self.pet.gift
        msg = self.pet.claim_gift()
        if msg:
            self.screen_w.start_fx("gift", icon=key)   # gifting() amble, chains to cheer (giftEnd)
            # the SURPRISE: hold the reveal until the present is opened at the
            # end of the amble (2026-07-24) -- a tease now, the contents then.
            self._pending_gift_reveal = msg
            self._do("Um presente! Vamos ver o que é…")

    def action_heal(self):
        """The H key: patch a battle injury -- a free care BUTTON like C
        clean (the bandage's final door, Joel 2026-07-26).  A cure plays
        the canon Bandaging show (items.csv i:80); a refusal just speaks."""
        if self.screen_w.fx is not None:        # let the current care animation finish before acting again
            return
        msg = self.pet.heal_bandage()
        if "patched" in str(msg):
            self.screen_w.start_fx("item", icon="i:80", script="Bandaging")
        self._do(str(msg))

    def action_clean(self):
        if self.screen_w.fx is not None:        # let the current care animation finish before acting again
            return
        poop = self.pet.poop
        sizes0 = list(self.pet.poop_sizes)      # clean() wipes them; the fx still shows the piles
        msg = self.pet.clean()
        if self.pet.anim == "wash":
            self.screen_w.start_fx("clean", poop=poop)
            self.screen_w.fx["sizes"] = sizes0
            self.beep("wash", bell=False)
        self._do(msg)

    def action_sleep(self):                                     # the "s" key is the LIGHTS toggle
        self.beep("confirm", bell=False)                        # a button blip on the lights on/off press
        self._do(self.pet.toggle_lights())

    def action_new(self):
        # (the seed bank + prev-gen snapshot moved to _hatch_new's COMMIT
        # point: mutating here let an ESC-cancelled carousel leave a
        # duplicate headstone and record a still-live pet as the previous
        # generation -- gameplay audit 2026-07-19)
        gen = self.pet.generation + 1
        self._open_mode(eggselectscreen.EggSelectPanel(self.pet),
                        lambda et: self._hatch_new(et, gen))

