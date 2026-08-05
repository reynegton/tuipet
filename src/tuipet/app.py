"""tuipet — a terminal Monster V-Pet rendered with halfblock sprites."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import os as _os
import random
if not _os.environ.get("COLORTERM"):
    _os.environ["COLORTERM"] = "truecolor"
from rich.cells import cell_len, set_cell_size
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Static
import tuipet.ui.components.statusbox as statusbox
from tuipet.appactions import ActionsMixin
from tuipet.appboot import (    # noqa: F401  (re-export: tuipet.app.X keeps resolving)
    MIN_COLS, MIN_ROWS, _load_sound, _lobby_uri, _preflight, _save_sound,
    _sound_path, host_platform)
import tuipet.data.loaders.data as data
import tuipet.ui.components.menu as menu
from tuipet.i18n.translator import t
import tuipet.ui.screens.eggselectscreen as eggselectscreen
import tuipet.utils.persistence as persistence
import tuipet.network.net as net
import tuipet.ui.screens.lobbyscreen as lobbyscreen
import tuipet.ui.screens.titlescreen as titlescreen
import tuipet.ui.screens.deathscreen as deathscreen
import tuipet.utils.sound as sound
import tuipet.utils.update as update_check
import tuipet.network.cloudsync as cloudsync
import tuipet.core.shop as shop
from tuipet.core.pet import Pet
from tuipet.core.petbase import POOPDANCE_AT
import tuipet.utils.theme as theme
from tuipet.core.arena import (    # noqa: F401  (full re-export: preserve tuipet.app.* for callers/tests)
    Screen, SCREEN_COLS, SCREEN_ROWS, SPRITE_W, PET_BASE_X, _FxCtx,
    hearts, bar, _FX, GRAVESTONE, POOP_W, POOP_PAD,
    _evol_strobe, _filth_right, _filth_pts, COND_W, COND_H, SICK_ZONE,
    PLAY_HOP, PLAY_LEAD, PLAY_HOP_H, GIFT_OUT, GIFT_BACK, GIFT_HOLD,
    _HIDDEN_STATUS_ICONS, _effect_overlay, _sick_mark_up,
)
import re as _re
_NAV_KEYS = frozenset({"up", "down", "left", "right", "j", "k", "h", "l", "tab",
                       "pageup", "pagedown"})
HUD_W = 40              # message-box content width (CSS #msg: 44 - 2 border - 2 padding)
HUD_GAP = "      "      # blank run between marquee wraps so the looped text reads cleanly
HUD_STEP = 2            # advance the marquee every N frames (10 Hz clock -> ~0.2 s/char)
HUD_HOLD = 8            # marquee steps to hold on the message head before scrolling (~1.6 s)
_HUD_MARKUP = _re.compile(r"\[/?[^\]]*\]")
def _hud_plain(t: Any) -> Any:
    """Visible text of a Rich-markup string (tags stripped) for width measurement."""
    return _HUD_MARKUP.sub("", t)
def _hud_esc(t: Any) -> Any:
    """Escape '[' so a plain marquee window is never parsed as Rich markup."""
    return t.replace("[", "\\[")
def _hud_fits(markup: Any) -> Any:
    """True when a message renders inside the box -- measured in CELLS, never
    chars (bug report #32, Joel v0.5.264 "what is space t?": '⚡' is TWO
    terminal cells, so a 40-char road strip measured 41 cells, slipped past
    the char check, and Textual wrapped 'ESC' onto the box's invisible
    second row)."""
    return cell_len(_hud_plain(markup)) <= HUD_W
def keys_markup() -> Any:
    """The action bar, rebuilt per theme: the shortcut letters wear the
    theme's KEY colour -- cyan on EVERY theme today (the per-theme key
    colours died with the putty-shell revert, Joel 2026-07-05 "this looks
    bad"; the magenta this docstring used to promise was archaeology --
    naming audit 2026-07-19).  Was a module constant with `b cyan` baked
    in, unreachable by theme.apply (shell polish 2026-07-05).

    Reading order mirrors the Help screen's sections — CARE, then
    EXPLORE, then GROW, then MANAGE — one layout language across the bar,
    Help and the Options→Keys page (bar tidy 2026-07-18).  GROW's egg
    guide wraps onto line 3: the line only holds 71 cells."""
    from tuipet import SERVIDOR_ONLINE
    k = f"b {theme.KEY}"
    l1 = f"[{k}]f[/] {t('action_feed', 'feed')}  [{k}]h[/] {t('action_heal', 'heal')}  [{k}]c[/] {t('action_clean', 'clean')}  [{k}]o[/] {t('action_lights', 'lights')}  [{k}]v[/] {t('action_assist', 'assist')}  [{k}]p[/] {t('action_discipline', 'discipline')}  [{k}]m[/] {t('action_battle', 'battle')}"
    
    l2_parts = [f"[{k}]a[/] {t('action_adventure', 'adventure')}"]
    if SERVIDOR_ONLINE:
        l2_parts.append(f"[{k}]r[/] {t('action_raid', 'raid')}")
    l2_parts.append(f"[{k}]u[/] {t('action_cup', 'cup')}")
    if SERVIDOR_ONLINE:
        l2_parts.append(f"[{k}]l[/] {t('action_lobby', 'lobby')} [dim](pvp)[/]")
    l2_parts.extend([
        f"[{k}]t[/] {t('action_train', 'train')}",
        f"[{k}]x[/] {t('action_dna', 'DNA')}",
        f"[{k}]d[/] {t('action_datacore', 'datacore')}"
    ])
    l2 = "  ".join(l2_parts)
    
    l3_parts = [
        f"[{k}]e[/] {t('action_eggs', 'eggs')}",
        f"[{k}]s[/] {t('action_shop', 'shop')}",
        f"[{k}]b[/] {t('action_bag', 'bag')}",
        f"[{k}]n[/] {t('action_scenes', 'scenes')}",
        f"[{k}]g[/] {t('action_options', 'options')}"
    ]
    if SERVIDOR_ONLINE:
        l3_parts.append(f"[{k}]i[/] {t('action_bug', 'bug')}")
    l3_parts.extend([
        f"[{k}]?[/] {t('action_help', 'help')}",
        f"[{k}]q[/] {t('action_quit', 'quit')}"
    ])
    l3 = "  ".join(l3_parts)

    return f"{l1}\n{l2}\n{l3}"
_gen_subtitle = statusbox.gen_subtitle
_age_compact = statusbox.age_compact
_care_deco = statusbox.care_deco
_status_line = statusbox.status_line
class Stats(Static):
    """The right-hand card widget.  Every card body lives in statusbox --
    this widget only chooses home/egg/grave and writes the lines."""

    def paint(self, pet: Pet) -> Any:
        if pet.dead:
            return self._paint_grave(pet)
        if pet.num == -1 or pet.stage == "Egg":
            return self._paint_egg(pet)
        self.border_subtitle = _gen_subtitle(pet)
        self.update("\n".join(statusbox.home_lines(pet)))

    def _paint_egg(self, pet: Any) -> None:
        self.border_subtitle = _gen_subtitle(pet)
        self.update("\n".join(statusbox.egg_lines(pet)))

    def _paint_grave(self, pet: Any) -> None:
        self.border_subtitle = _gen_subtitle(pet)
        self.update("\n".join(statusbox.grave_lines(pet)))
from tuipet.app_mixins import *

class TuiPetApp(ActionsMixin, HudMixin, TimersMixin, CloudMixin, SoundMixin, LifecycleMixin, ErrorsMixin, AccountMixin, App):  # type: ignore
    CSS = """
        Screen { align: center middle; }
        #wrap { width: auto; height: auto; }
        #top { width: auto; height: auto; }
        #left { width: 44; height: auto; }
        #lcd { border: thick #7a7e78; padding: 0 1; background: #c6c9cc; width: 44; height: 14; }
        #msg {
            border: round #7a7e78; padding: 0 1; width: 44; height: 3; margin-top: 1;
            color: #7d8186; content-align: left middle;
        }
        #stats { border: round #7a7e78; padding: 0 1; width: 30; height: 18; margin-left: 1; }
        #keys {
            border: round #7a7e78; padding: 0 1; width: 75; height: 5; margin-top: 1; color: #7d8186;
        }
        """

    WHATS_NEW = ("KEYS THAT SPELL THEMSELVES, round two: E is the Eggs "
                     "guide now and N the scene picker — joining yesterday's "
                     "S shop, B bag, O lights and I bug. Every door you open "
                     "often wears its own letter; the bar, help and "
                     "Options→Keys all tell the same story. (At the grave, "
                     "N still starts the next egg — that promise is older "
                     "than the remap.)")

    BINDINGS = [
            # jogress is LOBBY-ONLY (fusion needs a real partner from the
            # roster).  m is the HOME PvE bout vs a stage-matched rival --
            # no purse, training +2 -- and PvE also lives in Adventure, raids
            # and the cup.  (The 2026-07-07 "battles are online-only" ruling
            # was superseded by the 0.5 home bout; the old comment here
            # outlived it -- claims audit 2026-07-25.)
            # Order = the ACTIONS bar / Help-screen reading order (CARE,
            # EXPLORE, GROW, MANAGE) so the Options→Keys page tells the same
            # story (bar tidy 2026-07-18).
            # Mnemonic remap (player report 2026-07-28: "assign the correct
            # letters"): s=shop, b=bag (the frequent doors get their letters);
            # lights rides o (an on/off toggle), bug rides i (an issue).
            ("f", "feed", t("app_menu_feed", "Feed")), ("h", "heal", t("app_menu_heal", "Heal")), ("c", "clean", t("app_menu_clean", "Clean")),
            ("o", "sleep", t("app_menu_lights", "Lights")), ("v", "assist", t("app_menu_assistant", "Assistant")),
            ("p", "discipline", t("app_menu_discipline", "Discipline")),
            ("m", "battle", t("app_menu_battle", "Battle")),
            ("a", "adventure", t("app_menu_adventure", "Adventure")),
            ("r", "raid", t("app_menu_raid", "Raid")), ("u", "tournament", t("app_menu_cup", "Cup")),
            ("l", "lobby", t("app_menu_lobby", "Lobby")),
            ("t", "train", t("app_menu_train", "Train")), ("x", "dna", t("app_menu_dna", "DNA")),
            ("d", "datacore", t("app_menu_datacore", "datacore")), ("e", "eggguide", t("app_menu_eggguide", "Egg Guide")),
            ("s", "shop", t("app_menu_shop", "Shop")), ("b", "inventory", t("app_menu_bag", "Bag")),
            ("n", "scenes", t("app_menu_scenes", "Scenes")), ("g", "options", t("app_menu_options", "Options")),
            ("i", "bug", t("app_menu_bug", "Bug")), ("question_mark", "help", t("app_menu_help", "Help")), ("q", "quit", t("app_menu_quit", "Quit")),
            # space rides along as a silent confirm alias (QOL 2026-07-23):
            # every in-panel confirm takes ENTER or SPACE, the home view took
            # only ENTER.  action_gift no-ops when no gift is pending.
            ("enter,space", "gift", t("app_menu_gift", "Accept gift")),
        ]

    from tuipet import SERVIDOR_ONLINE

    if not SERVIDOR_ONLINE:
            BINDINGS = [b for b in BINDINGS if (b[1] if isinstance(b, tuple) else getattr(b, 'action', '')) not in ('raid', 'lobby', 'bug')]

    def __init__(self, pet: Pet | None = None) -> None:
            super().__init__()
            try:                       # the version THIS process runs (see _bug_meta)
                from importlib.metadata import version as _v
                self._boot_version = _v("tuipet")
            except Exception:
                self._boot_version = ""
            self._welcome = t("app_msg_welcome", "Welcome! Raise your pet.")
            self._new_game = False
            if pet is None:
                loaded, msg = persistence.load()
                if loaded is not None:
                    pet, self._welcome = loaded, (msg or t("app_msg_welcome_back", "Bem-vindo de volta!"))
                else:
                    self._new_game = True
                    if msg:          # a QUARANTINED corrupt save -- never play it
                        self._welcome = msg     # off as a first launch (sweep 07-14)
                        # ...and never SWALLOW the notice either: the new-game
                        # path skips the welcome hud (title -> carousel, strips
                        # own the box every frame), so the message rode nothing
                        # and the loss looked exactly like a first launch -- the
                        # thing the 07-14 sweep existed to prevent (title audit
                        # 2026-07-19).  It joins the first surviving surface:
                        # the post-pick flash in _after_egg_pick.
                        self._boot_notice = msg
            self.pet = pet or Pet.new_egg()
            self.mode = None            # active in-display panel (no pop-up screens)
            self._dying_fx = False      # type: ignore
            self._mode_close = None
            self.sound = _load_sound()
            self._needs = False  # type: ignore
            self._flash_t = 0           # ticks an action flash holds before a care-need re-asserts
            self._showing_need = False  # type: ignore
            self._update_msg = None     # set by the background PyPI check when a newer release exists
            self._showing_update = False  # type: ignore
            self._showing_armed = False  # type: ignore
            self._showing_tidy = False   # type: ignore
            self._showing_eggwait = False   # type: ignore
            self._sync = None           # background cloud-save push client (net.SyncClient), or None
            self._hud_scroll = None     # plain text being marquee-scrolled, or None when it fits
            self._hud_off = 0           # marquee window offset
            self._hud_hold = 0          # steps left to hold on the head before scrolling
            self._hud_tick = 0          # frame counter for the marquee throttle

    def compose(self) -> ComposeResult:
            with Vertical(id="wrap"):
                with Horizontal(id="top"):
                    with Vertical(id="left"):
                        yield Screen(id="lcd")
                        yield Static(t("app_msg_welcome", "Welcome! Raise your pet."), id="msg")
                    yield Stats(id="stats")
                yield Static(keys_markup(), id="keys")

    def on_mount(self) -> None:
            self.screen_w = self.query_one("#lcd", Screen)
            self.stats_w = self.query_one("#stats", Stats)
            self.msg_w = self.query_one("#msg", Static)
            self.keys_w = self.query_one("#keys", Static)
            self.screen_w.border_title = "TUIPET"
            self.stats_w.border_title = "STATUS"
            self.keys_w.border_title = "ACTIONS"
            # the "● on" LED is LIVE (repaint syncs it to pet.lights) -- set
            # once, it kept reading "on" all night (QOL 2026-07-23)
            self.screen_w.border_subtitle = "● on" if self.pet.lights else "● off"
            wn = self._whats_new()
            if wn:                       # first launch on a new build: the news
                self._welcome = f"{wn}  ·  {self._welcome}"   # rides the msg box
            self._hud(self._welcome)
            theme.apply(theme.load_choice())
            self._restyle()
            self.repaint()
            self._open_mode(titlescreen.TitlePanel(), self._after_title)   # the panel's strip() carries PRESS ENTER
            self.set_interval(0.1, self.on_frame)    # single DVPet interval clock: 1 tick == 0.1s (main view AND sub-screens)
            self.set_interval(1.0, self.on_tick)
            self.set_interval(10.0, self.autosave)
            from tuipet import SERVIDOR_ONLINE
            if SERVIDOR_ONLINE:
                self.run_worker(self._check_update(), name="update", exclusive=False)
                self.run_worker(self._flush_bugs(), name="bugflush", exclusive=False)
                self._start_sync()

    async def _check_update(self) -> None:
            """Background, once per launch: ask PyPI for a newer tuipet and INSTALL
            it (Joel 2026-07-14: "make it so the game automatically checks and
            updates itself... then they have to restart for it to be the new one").
    
            Never blocks the game: this runs off the UI thread and the player keeps
            playing the version they launched.  Python already imported that code,
            so a fresh install can only take effect on the NEXT launch -- the nudge
            says exactly that, and never claims a live swap.
            Honest about what it cannot do (the silent-failure law): where we cannot
            run pip for the player -- iOS sandboxes subprocesses, a source checkout
            has no release to install over -- we fall back to telling them the
            command.  A failed install says so and hands the command over too; it
            never pretends the update happened.
            """
            import asyncio
            latest = await asyncio.to_thread(update_check.latest_if_newer)
            if not latest:
                return
            if not persistence.get_auto_update():          # the player opted out
                self._update_msg = f"⬆ tuipet {latest} disponível — {update_check.manual_command()}"  # type: ignore
                return
            if update_check.upgrade_argv() is None:        # iOS / source: cannot self-install
                self._update_msg = f"⬆ tuipet {latest} disponível — {update_check.manual_command()}"  # type: ignore
                return
            self._update_msg = f"⬆ instalando tuipet {latest}…"  # type: ignore
            ok, _msg = await asyncio.to_thread(update_check.run_upgrade)
            if ok:
                self._updated_to = latest
                self._update_msg = f"✔ tuipet {latest} instalado — reinicie para jogar"  # type: ignore
            else:
                self._update_msg = f"⬆ tuipet {latest} disponível — {update_check.manual_command()}"  # type: ignore

    def on_unmount(self) -> None:
            persistence.save(self.pet)
            self._flush_dms_on_quit()       # a lobby quit must not drop PMs from this session
            self._flush_cloud_on_quit()     # capture the final state cloud-side on any exit

    def on_key(self, event: Any) -> None:
            fx = getattr(getattr(self, "screen_w", None), "fx", None)
            if fx is not None and fx.get("kind") == "dying":
                # dying(): the pet is a BUTTON -- frantic taps can save it
                # (numHits > HitsToSave x (savedFromDeath + 1))
                self._revive_hits = getattr(self, "_revive_hits", 0) + 1  # type: ignore
                self.beep("click", bell=False)
                event.stop()
                event.prevent_default()
                return
            if (self.mode is None and not self.pet.dead
                    and getattr(self.screen_w, "fx", None) is not None
                    and event.key != "q"):
                # canon disableMainMenu: the WHOLE menu locks while an animation
                # plays (Joel 2026-07-06).  The 8 mutating care actions always
                # guarded; the browse menus could still open mid-ceremony -- now
                # every binding waits for the show.  q (quit) stays live; the
                # dying-fx revive mash is handled above this gate.
                # the swallowed key is ACKNOWLEDGED (QOL 2026-07-23): a silent
                # eat read as a frozen app and invited a mash -- same soft
                # click the dying-fx taps get
                self.beep("click", bell=False)
                event.stop()
                event.prevent_default()
                return
            if self.mode is None and self.pet.dead:
                # A departed pet can DO nothing (the device shows only the grave).
                # ONE chokepoint ahead of every global binding -- the per-action
                # can_*() gates kept slipping (a dead mon could still adventure,
                # Joel 2026-07-05).  Any care key leads back to the memorial;
                # quit, options and the LOBBY stay live beside the grave (Joel
                # 2026-07-19: the social room is not a care action -- chat, DMs,
                # ladder and rooms all work; battles/jogress stay refused by
                # can_battle/can_jogress and the server's session gate).
                if event.key not in ("q", "g", "l"):
                    event.stop()
                    event.prevent_default()
                    if event.key == "n" and self.pet.death_banked:
                        # the bare grave card promises "press N for a new egg"
                        # -- deliver the CAROUSEL, not another lap through the
                        # memorial (QOL 2026-07-23).  Pre-bank, N still runs
                        # the ceremony below: the etch comes first.
                        self.action_new()
                        return
                    # every care key leads to the memorial (the dead-gate law) --
                    # and if this death's etch/seed ceremony hasn't run yet (a
                    # relaunch mid-dying-beat), it runs HERE, so the inheritance
                    # can never be lost to a quit (gameplay audit 2026-07-19).
                    # An untouched relaunch still gets the dying beat + mash
                    # window from the tick's state check instead.
                    self._death_ceremony()
                return
            if self.mode is not None:
                event.stop()
                event.prevent_default()      # a panel owns the keyboard: don't fire global BINDINGS
                # Textual names punctuation keys ("." -> "full_stop", "!" ->
                # "exclamation_mark"), so a panel's `len(k) == 1 and k.isprintable()`
                # text test silently dropped every non-alphanumeric.  For a
                # text-capturing panel, forward the actual typed character instead of
                # the key NAME (nav keys carry no printable character, so they still
                # arrive by name; space stays "space" via its explicit handling).
                k = event.key
                ch = getattr(event, "character", None)
                if (getattr(self.mode, "captures_text", False)
                        and ch is not None and len(ch) == 1
                        and ch.isprintable() and not ch.isspace()):
                    k = ch
                result = self.mode.key(k)
                snd = getattr(self.mode, "sfx", None)
                if snd:
                    self.beep(snd, bell=False)
                    self.mode.sfx = None
                elif getattr(self.mode, "captures_text", False):
                    pass                                # typing: no nav/confirm blips (audit 2026-07)
                elif event.key in _NAV_KEYS:
                    self.beep("scroll", bell=False)     # cursor-move blip for every list screen
                elif event.key == "enter":
                    self.beep("confirm", bell=False)    # menu confirm (a screen's own sfx wins above)
                elif event.key == "escape":
                    self.beep("cancel", bell=False)     # back/cancel
                if result is not None and result[0] == "done":
                    self._close_mode(result[1])
                elif result is not None and result[0] == "quit":
                    self.action_quit()                  # a screen asked to quit the app (e.g. q on the title)
                elif event.key == "q" and not getattr(self.mode, "captures_text", False):
                    self.action_quit()                  # QoL: q quits from any non-text screen, not just the main view
                else:
                    self.repaint()

    def _mode_strip(self) -> None:
            """A scene panel's one-line strip (note + key hints) rides the #msg box
            under the LCD -- the box sat BLANK during every sub-screen while the
            panels stacked that chrome inside the LCD and overflowed its 12 rows
            (the 2026-07-04 box-clip audit).  _hud gives long strips the marquee."""
            m = self.mode
            while getattr(m, "sub", None) is not None:   # the DEEPEST panel owns the strip
                m = m.sub                                # type: ignore
            strip = getattr(m, "strip", None)
            self._hud(strip() if strip is not None else "")

    def _open_mode(self, panel: Any, on_close: Optional[Any]=None) -> None:
            self.mode = panel
            self._mode_close = on_close
            # clear the message strip so a screen never shows the PREVIOUS screen's
            # farewell flash; scene panels put their own strip() here instead
            if getattr(self, "msg_w", None) is not None:
                self._hud("")
                self._mode_strip()
            self.repaint()

    def _close_mode(self, result: Any) -> None:
            cb = self._mode_close
            self.mode = None
            self._mode_close = None
            # a screen's strip must never outlive it (Joel 2026-07-10: the lobby's
            # hints stuck to the main view -- with no care need pending, on_tick's
            # message cascade never rewrites an already-filled box).  Clear BEFORE
            # the callback so a farewell flash or a chained _open_mode still paints
            # onto a clean box.
            if getattr(self, "msg_w", None) is not None:
                self._hud("")
            if cb:
                cb(result)
            else:
                self.repaint()

    def _verdict(self, msg: str) -> None:
            """Deliver an ASYNC WORKER's outcome so it actually REACHES the
            player (the swallow class -- rounds 19/21/22): a worker can finish
            while any screen is open, whose strip overwrites the hud every
            frame.  Home -> flash now; in a mode -> park it, the ✉-drain
            pattern shows it back home.  EVERY async worker with a player
            verdict routes here (bug sends, account switches, ...)."""
            if self.mode is None:
                self.flash(msg)
            else:
                self._verdict_note = msg

    def _restyle(self) -> None:
            # the DMG-shell reading (2026-07-05): the LCD's thick frame is the
            # screen BEZEL, the round boxes are the SHELL body, the titles/key
            # hints are printed LABEL text -- plain themes fall back to border/mid
            try:
                for w in (self.screen_w, self.stats_w, self.msg_w, self.keys_w):
                    w.styles.border = ("round", theme.SHELL)
                    w.styles.border_title_color = theme.LABEL
                self.screen_w.styles.border = ("thick", theme.BEZEL)
                self.screen_w.styles.border_subtitle_color = theme.ACCENT
                self.screen_w.styles.background = theme.LCD_BG
                self.msg_w.styles.color = theme.LABEL
                self.keys_w.styles.color = theme.LABEL
                self.keys_w.update(keys_markup())   # the shortcut letters re-tint too
            except Exception:
                pass

    def _center(self, text: str) -> Any:
            from rich.text import Text
            n = text.plain.count("\n") + 1  # type: ignore
            pad = max(0, (SCREEN_ROWS - n) // 2)
            if not pad:
                return text
            out = Text("\n" * pad)
            out.append_text(text)  # type: ignore
            return out

    def repaint(self) -> None:
            if self.mode is not None:
                self.screen_w.update(self._center(self.mode.text()))
                self._mode_strip()
            else:
                self.screen_w.paint(self.pet)
                led = "● on" if self.pet.lights else "● off"
                if self.screen_w.border_subtitle != led:
                    self.screen_w.border_subtitle = led
            if (painter := self._status_painter()) is not None:
                painter()
            else:
                # data/datacore browses in the LCD; keep live vitals on the right
                self.stats_w.paint(self.pet)

    def _status_painter(self) -> Any:
            """The mode's card painter, dispatched from statusbox's registry
            (one module owns every card -- Joel 2026-07-17: "MODULIZE THE
            STATUS BOX")."""
            fn = statusbox.painter_for(self.mode)
            if fn is None:
                return None
            return lambda: fn(self)

    def _status_eggselect(self) -> None:
            statusbox.eggselect(self)

    def _status_eat(self) -> None:
            statusbox.eat(self)

    def _status_card(self, title: Any, lines: Any) -> None:
            statusbox.card(self, title, lines)

    FLASH_HOLD = 4                  # seconds an action result holds before the care-need shows

