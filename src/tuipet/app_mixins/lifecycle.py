from __future__ import annotations
import tuipet.data.loaders.data as data
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.ui.screens.eggselectscreen as eggselectscreen
import tuipet.ui.screens.deathscreen as deathscreen
import tuipet.utils.theme as theme
from tuipet.core.pet import Pet
import tuipet.core.egg as egg_mod

class LifecycleMixin:
    def _after_death(self, result):
            if result == "new":
                self.action_new()
            else:
                self.repaint()

    def _whats_new(self):
            """One 'WHAT'S NEW' line in the msg box, on the FIRST launch of a new
            build only (Joel 2026-07-07: release news belongs on the title
            screen).  The seen stamp lives in settings so it survives pets and
            rides the .bak rotation like every app-level pref."""
            import tuipet.utils.update as update
            cur = update.current_version()
            if not cur:
                return None
            s = persistence.load_settings()
            if s.get("seen_version") == cur:
                return None
            s["seen_version"] = cur
            persistence.save_settings(s)
            if self._new_game:
                # a first-EVER install also has no seen_version, but release news
                # names systems a brand-new player hasn't met (honors, DNA
                # wagers...) -- stamp it seen and say nothing (sweep 2026-07-14)
                return None
            return f"WHAT'S NEW in v{cur}: {self.WHATS_NEW}"

    def _post_title(self):
            if self._new_game:
                self._open_mode(eggselectscreen.EggSelectPanel(self.pet), lambda et: self._hatch_new(et, 1))
            else:
                self._hud(self._welcome)
                self.repaint()

    def _death_ceremony(self, hold=0):
            """The ONE banking ceremony for a death, wherever it's noticed --
            the dying-fx completion, or a relaunch that finds the pet already
            dead.  The etch and the careBonusOnReset seed used to exist only in
            the fx branch, so a quit/crash during the dying beat silently
            disinherited the heir (gameplay audit 2026-07-19).  Runs once per
            death (pet.death_banked rides the save); after that every care key
            leads back to the bare memorial.
    
            UnlockInheritance (onDie with _bonus > 0): the departed CAN etch
            its Memory -- canon's memory_Validation is a real choice
            (declining keeps the bonus for the heir), so the panel asks; the
            etch is the walk-out default.  A held UNUSED payload is
            device-lifetime (canon item 32 survives resetToEgg): back to the
            bank first (memory audit 2026-07-06), where the only-one
            prompt covers it."""
            p = self.pet
            if p.death_banked:
                self._open_mode(deathscreen.DeathPanel(
                    p, old_mem=persistence.peek_memory()), self._after_death)
                return
            if p.memory:
                persistence.bank_memory(dict(p.memory))
                p.memory = {}
            b0 = p.evol_bonus
            new_mem = p.make_memory()
            grade_spent = p.final_care_grade()   # the etch path's seed
            p.evol_bonus = b0
            grade_kept = p.final_care_grade()    # the decline path's seed
            p.evol_bonus = 0                     # the life is spent either way
            old_mem = persistence.peek_memory()
            banked_new = False
            if new_mem and not old_mem:
                persistence.bank_memory(new_mem)    # default: etched
                banked_new = True
            persistence.bank_bonus_seed(grade_spent)    # default seed; B re-banks
            p.death_banked = True
            persistence.save(p)
            self._open_mode(deathscreen.DeathPanel(p, hold=hold, new_mem=new_mem,
                                                   old_mem=old_mem, grade_kept=grade_kept,
                                                   banked_new=banked_new), self._after_death)

    def _grant_memory(self, pet):
            """Hand the banked inheritance data to the next generation: the payload
            rides the pet's save; the Memory chip appears in its bag (DVPet
            items persist across resetToEgg -- tuipet's generations carry only
            this one).  The raw "i:32" icon key it used to ride is healed to the
            named key on load (shop.LEGACY_KEYS; gameplay audit 2026-07-19)."""
            mem = persistence.take_memory()
            if mem:
                pet.memory = dict(mem)
                # the inherited ESTATE bag may already carry the elder's unused
                # husk (the re-banked-payload case) -- never a second chip for
                # one payload (memory audit 2026-07-06)
                if pet.inventory.get("memory", 0) <= 0:
                    pet.add_item("memory")
            # the departed's care grade seeds this generation's bonus (careBonusOnReset)
            pet.evol_bonus = persistence.take_bonus_seed()

    def autosave(self):
            persistence.save(self.pet)
            self._start_sync()              # idempotent: picks up a re-enabled cloud toggle
            self._warn_if_unsaveable()
            self._warn_if_cloud_dropped()
            self._note_progress()
            self._push_cloud()              # mirror the autosave up to the cloud

    def _warn_if_unsaveable(self):
            """A save dir the OS refuses used to fail SILENTLY -- the pet simply
            never persisted and the player found out by losing it (iOS's read-only
            home, support pass 2026-07-13).  Say it once, loudly, with the fix."""
            if not persistence.save_failed or getattr(self, "_save_warned", False):
                return
            self._save_warned = True
            self.beep("alarm")
            self.flash(f"[{theme.NEG}]⚠ NÃO É POSSÍVEL SALVAR — seu pet não persistirá! "
                       f"Set TUIPET_SAVE_DIR to a writable folder.[/]")

    def _note_progress(self):
            """Record cross-generation egg-unlock milestones from the live pet."""
            p = self.pet
            if p is None or p.stage in ("", "Egg"):
                return
            persistence.note_generation(p.generation)
            if p.stage in data.STAGE_ORDER:
                persistence.note_stage_index(data.STAGE_ORDER.index(p.stage))
            if getattr(p, "x_antibody", "None") != "None":
                persistence.note_xanti()

    def _flush_dms_on_quit(self):
            """Quitting straight from the lobby must persist DMs received this
            session: incoming PMs live only in memory until a read/leave saves
            them, so a hard quit (Ctrl-C, terminal close) would otherwise drop
            them (the 'A' gap, 2026-07-12)."""
            if isinstance(self.mode, lobbyscreen.LobbyPanel):
                try:
                    self.mode._save_dms()
                except Exception:
                    pass

    def _hatch_new(self, egg_type, gen):
            if egg_type is None:                        # cancelled -> keep the current pet
                self._do("Manteve seu parceiro atual.")
                return
            if egg_type == "guide":
                # E on the carousel: consult the guide, then come back to the
                # pick with the SAME generation in hand.  (This sentinel was
                # only handled on the fresh-start path -- the retire/death path
                # crashed on it: Termux crash 2026-07-18, egg_type='guide'.)
                import tuipet.ui.screens.eggguidescreen as eggguidescreen
                import tuipet.ui.screens.eggselectscreen as eggselectscreen
                self._open_mode(eggguidescreen.EggGuidePanel(self.pet),
                                lambda _=None: self._open_mode(
                                    eggselectscreen.EggSelectPanel(self.pet),
                                    lambda et: self._hatch_new(et, gen)))
                return
            # the generational COMMIT: nothing mutates until the pick is real
            # (an ESC-cancelled carousel used to have already appended a
            # headstone and overwritten last_gen -- gameplay audit 2026-07-19)
            # AN UNHATCHED EGG RE-ROLLS AS A RE-PICK, NOT A GENERATION (egg
            # audit 2026-07-25): a generation is a LIFE -- snapshot_prev_gen has
            # always refused to record an egg, but this commit still advanced
            # the counter (five re-rolls pumped max_gen to 7 and opened every
            # gen-gated egg unearned), graded the EGG's "care" over the dead
            # elder's banked seed, and dropped the etched Memory with the
            # discarded shell.  A re-pick keeps the generation and carries the
            # whole inheritance to the new shell.
            repick = self.pet.stage == "Egg" and not self.pet.dead
            if repick:
                gen = self.pet.generation
            elif not self.pet.dead:
                # a LIVE retire skips the death flow entirely: canon resetMonster
                # runs careBonusOnReset dead or alive, and a live reset never
                # offers the etch -- the FULL adjusted bonus carries to the heir
                # (memory audit 2026-07-06; this seed used to be lost)
                persistence.bank_bonus_seed(self.pet.final_care_grade())
            persistence.snapshot_prev_gen(self.pet)   # previous-generation egg gates
            old = self.pet
            self.pet = Pet.new_egg(generation=gen, egg_type=egg_type)
            self._grant_memory(self.pet)
            if repick:
                # the outgoing shell's estate moves over untouched: wallet, bag
                # (bought goods included -- the shop opens for an egg), trophy
                # room, DNA bank, the taken seed and the etched memory
                self.pet.bits = old.bits
                self.pet.inventory = dict(old.inventory or {})
                self.pet.trophies = old.trophies
                self.pet.trophies_won = dict(old.trophies_won or {})
                self.pet.dna_owned = dict(old.dna_owned or {})
                self.pet.evol_bonus = old.evol_bonus
                # the anti-printer ledgers ride along (audit 2026-07-25): a
                # re-pick that dropped them refilled every town ration, the
                # home deal AND the road bounty per re-roll -- an estate carry
                # must never mint a fresh shopping day
                self.pet.town_bought = dict(old.town_bought or {})
                self.pet.road_bounty = dict(getattr(old, "road_bounty", None) or {})
                if getattr(old, "memory", None):
                    self.pet.memory = dict(old.memory)
                    if self.pet.inventory.get("memory", 0) <= 0:
                        self.pet.add_item("memory")
            persistence.save(self.pet)
            msg = f"Um novo ovo apareceu! (geração {gen}) (? = ajuda)"
            if getattr(self, "_boot_notice", ""):
                msg = f"{self._boot_notice}  {msg}"
                self._boot_notice = ""
            self._do(msg)

