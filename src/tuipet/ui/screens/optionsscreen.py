"""OPTIONS — one home for the app-level switches (Joel 2026-07-04: "put all
options related shit in there" and give the action bar its keys back).

Rows: Theme (hosts the live-preview ThemePanel as a sub), Sound (hosts the
SoundPanel sub: the on/off switch + the volume bar; the value still names the
detected backend so silent-sound mysteries self-explain), Account (hosts the
lobby AccountPanel to switch who's signed in — the current pet parks with the
old account in the cloud), Cloud sync (the cloud-save + offline-mail toggle;
TUIPET_NO_SYNC outranks it), Update (on-demand PyPI check via update.py,
threaded so the UI never blocks), Keys (a scrollable page of every
home-screen binding), a New egg hand-off, and Erase all data (typed-YES
confirm; wipes the local save dir -- the cloud copy stays with the account).
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import threading

import tuipet.ui.components.menu as menu
import tuipet.utils.persistence as persistence
import tuipet.utils.sound as sound
import tuipet.utils.theme as theme
import tuipet.utils.update as update_check
from tuipet.ui.screens.themescreen import ThemePanel
from tuipet.i18n.translator import t
from tuipet import SERVIDOR_ONLINE

_ROWS: tuple[str, ...] = ("theme", "sound", "account", "cloud", "update", "keys", "language", "new", "erase")
if not SERVIDOR_ONLINE:
    _ROWS = tuple(r for r in _ROWS if r not in ("account", "cloud", "update"))
def _get_label() -> Any:
    return {"theme": t("opt_lbl_theme", "Theme"), "sound": t("opt_lbl_sound", "Sound"), "account": t("opt_lbl_account", "Account"),
            "cloud": t("opt_lbl_cloud", "Cloud sync"), "update": t("opt_lbl_update", "Update"), "keys": t("opt_lbl_keys", "Keys"),
            "language": t("opt_lbl_language", "Language"),
            "new": t("opt_lbl_new", "New egg"), "erase": t("opt_lbl_erase", "Erase all data")}
# the note line under the list describes the SELECTED row and follows the
# cursor (Joel's live review 2026-07-07: it sat frozen on the flavour line);
# action feedback (sound toggled, update verdict...) overrides it until the
# action feedback (sound toggled, update verdict...) overrides it until the
# cursor moves again.  Over-wide lines marquee via menu.note(tick).
def _get_desc() -> Any:
    return {"theme": t("opt_desc_theme", "recolor the whole game — live preview"),
            "sound": t("opt_desc_sound", "the DVPet chirps — switch + volume"),
            "account": t("opt_desc_account", "switch login — the pet parks in the cloud"),
            "cloud": t("opt_desc_cloud", "cloud saves + offline mail — on or off"),
            "update": t("opt_desc_update", "ENTER checks + installs · A flips launch auto-install"),
            "keys": t("opt_desc_keys", "every binding on one page"),
            "language": t("opt_desc_language", "choose game language (pt, en, es)"),
            "new": t("opt_desc_new", "retire the pet, hatch the heir"),
            "erase": t("opt_desc_erase", "wipe save, progress and login — for keeps")}


def _sound_value(on: Any, with_volume: bool=False) -> Any:
    """The sound state + WHICH backend carries it, so a silent install
    self-explains (the Termux no-player mystery).  First token only and capped
    so nothing clips mid-word in the 18-char value column; the volume rides
    along on the OPTIONS row when a real player exists (the bell has none)."""
    if not on:
        return t("opt_snd_off", "off")
    b = sound.backend()
    if b:
        name = b.split("-")[0][:13]
        return t("opt_snd_on_vol", "on · {name} · {vol}%").format(name=name[:6], vol=sound.volume()) if with_volume else t("opt_snd_on", "on · {name}").format(name=name)
    import tuipet.utils.hostinfo as hostinfo
    return t("opt_snd_on_bell_ios", "on · bell (iOS)") if hostinfo.is_ios() else t("opt_snd_on_bell_only", "on · bell only")


class SoundPanel:
    """The sound page: the on/off switch and a volume bar (Joel 2026-07-15:
    the full-scale chirps were piercing — "chop that sound volume in half").
    ←→ steps the volume by 10 and chirps at the NEW level so you hear what you
    picked.  A bell-only host is told the truth — the terminal bell has no
    volume, so the bar never pretends to slide it."""

    _ROWS = ("sound", "volume")
    def _get_snd_desc(self) -> Any:
        return {"sound": t("opt_snd_desc_sound", "the DVPet chirps — on or off"),
                "volume": t("opt_snd_desc_volume", "←→ set it — every step chirps")}

    def __init__(self, sound_get: Any, sound_toggle: Any) -> None:
        self.sound_get = sound_get
        self.sound_toggle = sound_toggle
        self.cursor = 0
        self.frame_i = 0
        self.msg = ""                  # action feedback; empty -> the row's _DESC
        self.sfx = None

    def anim(self) -> None:
        self.frame_i += 1              # heartbeat: over-wide notes marquee

    def strip(self) -> Any:
        if self._ROWS[self.cursor] == "volume" and sound.available():
            return menu.hints(("←→", t("opt_snd_hint_vol", "volume")), ("ENTER", t("opt_snd_hint_hear", "hear it")),
                              ("ESC", t("opt_snd_hint_back", "back")))
        return menu.hints(("↑↓", t("opt_snd_hint_pick", "pick")), ("ENTER", t("opt_snd_hint_toggle", "toggle")), ("ESC", t("opt_snd_hint_back", "back")))

    def key(self, k: Any) -> Any:
        row = self._ROWS[self.cursor]
        if k in ("up", "k"):
            self.cursor = (self.cursor - 1) % len(self._ROWS)
            self.msg = ""
        elif k in ("down", "j"):
            self.cursor = (self.cursor + 1) % len(self._ROWS)
            self.msg = ""
        elif row == "volume" and k in ("left", "right", "h", "l"):
            if not sound.available():
                self.msg = t("opt_snd_bell_no_vol", "the terminal bell has no volume")
                return None
            v = sound.set_volume(sound.volume()
                                 + (10 if k in ("right", "l") else -10))
            self.msg = t("opt_snd_vol", "volume: {v}%").format(v=v)
            if self.sound_get():
                self.sfx = "confirm"   # type: ignore
        elif k in ("enter", "space"):
            if row == "sound":
                self.sound_toggle()
                self.msg = t("opt_snd_res", "sound: {val}").format(val=_sound_value(self.sound_get()))
                self.sfx = "confirm" if self.sound_get() else None  # type: ignore
            elif not sound.available():
                self.msg = t("opt_snd_bell_no_vol", "the terminal bell has no volume")
            elif not self.sound_get():
                self.msg = t("opt_snd_off_msg", "sound is off — nothing to hear")
            else:
                self.msg = t("opt_snd_vol", "volume: {v}%").format(v=sound.volume())
                self.sfx = "confirm"  # type: ignore
        elif k in ("escape", "g"):
            return ("done", None)
        return None

    def text(self) -> Any:
        out = menu.header(t("opt_snd_hdr", "SOUND"), sound.backend() or "bell")
        vol = sound.volume()
        if sound.available():
            vbar = "█" * (vol // 10) + "░" * (10 - vol // 10) + f" {vol}%"
        else:
            vbar = t("opt_snd_bell_na", "bell — n/a")        # no player: nothing a slider could touch
        rows = ((t("opt_snd_lbl_sound", "Sound"), _sound_value(self.sound_get())), (t("opt_snd_lbl_volume", "Volume"), vbar))
        for i, (label, val) in enumerate(rows):
            out.append_text(menu.row(f"{label:<16} {val[:18]}", i == self.cursor))
        out.append_text(menu.blanks(5))
        out.append_text(menu.note(self.msg or self._get_snd_desc()[self._ROWS[self.cursor]],
                                  tick=self.frame_i))
        # no in-LCD key footer: the strip owns the keys, and this one was
        # STATIC -- it contradicted the strip on the volume row ("↑↓ pick
        # ENTER go" vs "←→ volume · ENTER hear it").  QOL sweep 2026-07-23.
        out.right_crop(1)
        return out


class KeysPanel:
    """Every home-screen binding on one scrollable page (no cursor — there is
    nothing to pick, ↑↓ just slide the window)."""

    VISIBLE = 8

    def anim(self) -> None:
        pass          # frame heartbeat: over-wide notes marquee (sweep 2026-07-15)

    def __init__(self, bindings: Any) -> None:
        # Textual binds a couple of keys by identifier, not glyph -- show the
        # glyph so the page reads "?  Help" / "Enter  Accept gift" instead of
        # leaking "question_mark" (which also overran the 6-col key column).
        keyname = {"question_mark": "?", "enter": "ENTER",
                   "enter,space": "ENTER"}   # space is a silent gift alias
        self.rows = [f"{keyname.get(k, k):<6} {label}"
                     for k, _action, label in bindings]
        self.top = 0

    def strip(self) -> Any:
        return menu.hints(("↑↓", t("opt_key_hint_scroll", "scroll")), ("ESC", t("opt_snd_hint_back", "back")))

    def key(self, k: Any) -> Any:
        last = max(0, len(self.rows) - self.VISIBLE)
        if k in ("up", "k"):
            self.top = max(0, self.top - 1)
        elif k in ("down", "j"):
            self.top = min(last, self.top + 1)
        elif k == "pageup":                  # page jumps, lobby-chat style
            self.top = max(0, self.top - (self.VISIBLE - 1))
        elif k == "pagedown":
            self.top = min(last, self.top + (self.VISIBLE - 1))
        elif k in ("escape", "enter", "space", "g"):
            return ("done", None)
        return None

    def text(self) -> Any:
        n = len(self.rows)
        lo, hi = self.top + 1, min(self.top + self.VISIBLE, n)
        out = menu.header(t("opt_key_hdr", "KEYS"), f"{lo}-{hi}/{n}")
        shown = self.rows[self.top:self.top + self.VISIBLE]
        for r in shown:
            out.append_text(menu.row(r))
        out.append_text(menu.blanks(self.VISIBLE - len(shown) + 1))
        out.append_text(menu.footer(t("opt_key_footer", "↑↓ scroll  ESC back")))
        return out


class LanguagePanel:
    """The language page: allows picking between pt, en, es, and others."""

    _LANGS = ("pt", "en", "es", "fr", "de", "it", "zh-CN", "ja", "ru")

    def __init__(self) -> None:
        from tuipet.utils.persistence.settings_io import get_saved_language
        from tuipet.i18n.translator import get_language
        self.cursor = 0
        curr = get_saved_language() or get_language()
        if curr in self._LANGS:
            self.cursor = self._LANGS.index(curr)
        self.frame_i = 0
        self.msg = ""
        self.sfx = None  # type: ignore

    def anim(self) -> None:
        pass

    def strip(self) -> Any:
        return menu.hints(("↑↓", t("opt_snd_hint_pick", "pick")), ("ENTER", t("opt_hint_go", "go")), ("ESC", t("opt_hint_back", "back")))

    def key(self, k: Any) -> Any:
        if k in ("up", "k"):
            self.cursor = (self.cursor - 1) % len(self._LANGS)
            self.msg = ""
        elif k in ("down", "j"):
            self.cursor = (self.cursor + 1) % len(self._LANGS)
            self.msg = ""
        elif k in ("enter", "space"):
            self.sfx = "confirm"  # type: ignore
            return ("done", (self._LANGS[self.cursor],))
        elif k in ("escape", "g"):
            return ("done", None)
        return None

    def text(self) -> Any:
        out = menu.header(t("opt_lbl_language", "Language").upper(), "")
        rows = (("Português", "pt"), ("English", "en"), ("Español", "es"), 
                ("Français", "fr"), ("Deutsch", "de"), ("Italiano", "it"), 
                ("中文 (Zh-CN)", "zh-CN"), ("日本語", "ja"), ("Русский", "ru"))
        for i, (label, code) in enumerate(rows):
            out.append_text(menu.row(f"{label:<16}", i == self.cursor))
        out.append_text(menu.blanks(2))
        out.append_text(menu.note(self.msg, tick=self.frame_i))
        out.right_crop(1)
        return out


class OptionsPanel(menu.SubHost):
    def __init__(self, pet: Any, sound_get: Any, sound_toggle: Any, on_theme_change: Optional[Any]=None,
                 bindings: Any=(), update_hint: Optional[Any]=None, verdict: Optional[Any]=None) -> None:
        self.pet = pet
        self.sound_get = sound_get
        self.sound_toggle = sound_toggle
        self.on_theme_change = on_theme_change
        self.bindings = tuple(bindings)
        self.update_hint = update_hint
        self.verdict = verdict or (lambda m: None)   # the app's async-verdict
        #                                              channel (rounds 19/21/22)
        self.cursor = 0
        self.sub = None                # the hosted Theme/Account/Keys panel
        self._sub_row = None           # which row opened it (routes the done)
        self._done = None              # a sub verdict that must close options
        self.frame_i = 0
        self._upd = None               # None idle | "…" checking | "" none | "x.y.z"
        self._installing = False       # a pip run is in flight
        self._updated = False          # installed: the NEW code needs a restart
        self.confirm = False           # typed-YES gate for the erase
        self.confirm_restart = False   # update installed: offer the relaunch
        self.confirm_new = False       # one-ENTER gate before retiring a LIVING pet
        self.buf = ""
        self.msg = ""                  # action feedback; empty -> the row's _DESC
        self.sfx = None  # type: ignore

    @property
    def captures_text(self) -> Any:
        # typing YES — or a name/password in the hosted AccountPanel — q is a
        # letter here, never quit
        return self.confirm or self.confirm_new or self.confirm_restart or bool(
            self.sub is not None and getattr(self.sub, "captures_text", False))

    def anim(self) -> None:
        self.frame_i += 1
        if self.sub is not None and getattr(self.sub, "sfx", None):
            self.sfx = self.sub.sfx
            self.sub.sfx = None

    def strip(self) -> Any:
        """The message-box hint line (hint overhaul 2026-07-10)."""
        if self.sub is not None:
            return ""                  # the hosted panel owns the box (strip walker)
        if self.confirm:
            return menu.hints(("ENTER", t("opt_hint_erase_all", "erase it all")), ("ESC", t("opt_hint_keep", "keep")))
        if self.confirm_restart:
            return menu.hints(("ENTER", t("opt_hint_restart_now", "restart now")), ("ESC", t("opt_hint_later", "later")))
        if self.confirm_new:
            return menu.hints(("ENTER", t("opt_hint_retire", "retire")), ("ESC", t("opt_hint_keep", "keep")))
        return menu.hints(("↑↓", t("opt_snd_hint_pick", "pick")), ("ENTER", t("opt_hint_go", "go")), ("ESC", t("opt_hint_out", "out")))

    # ---- the update check (threaded: latest_if_newer blocks up to 4s) ----
    def _check_updates(self) -> None:
        if self._upd == "…":
            return                      # one probe at a time
        self._upd = "…"
        self.msg = t("opt_msg_chk_pypi", "checking PyPI…")

        def run() -> None:
            latest = update_check.latest_if_newer()
            self._upd = latest or ""
            self.msg = (t("opt_msg_chk_found", "tuipet {latest} is out — ENTER installs it").format(latest=latest)
                        if latest else t("opt_msg_chk_not_found", "no newer release found."))
        threading.Thread(target=run, daemon=True).start()

    def _install_update(self) -> None:
        """Install the newer release, off the UI thread (pip takes seconds).

        The running process keeps executing the OLD code -- Python imported it
        at launch -- so a success always ends in "restart tuipet".  We never
        pretend the swap happened live.
        """
        if self._installing:
            return
        self._installing = True
        self.msg = t("opt_msg_updating", "updating… (this takes a moment)")

        def run() -> None:
            ok, msg = update_check.run_upgrade()
            self.msg = msg
            self._installing = False
            if ok:
                self._upd = ""                # nothing left to offer
                self._updated = True
                # the restart OFFER (Joel 2026-07-18: "make it so the update
                # option asks to restart after update"): ENTER relaunches
                self.confirm_restart = True
                self.msg = t("opt_msg_updated_restart", "Updated! Restart now?  ENTER restarts · ESC later")
            # the completion ALSO rides the app's verdict channel (options
            # audit 2026-07-19, swallow class #4): pip takes seconds -- if
            # the player closed options meanwhile, the offer above lands on
            # a dead panel and they learn nothing.  The parked verdict
            # flashes wherever they are next home; a redundant note beside
            # the live offer is honest, a swallowed one is not.
            self.verdict(t("opt_msg_verdict_ok", "tuipet updated — restart to play the new version.")
                         if ok else t("opt_msg_verdict_err", "update: {msg}").format(msg=msg))
        threading.Thread(target=run, daemon=True).start()

    def _sub_done(self, r: Any) -> None:
        row, self._sub_row = self._sub_row, None
        if row == "theme":
            self.msg = t("opt_msg_theme_res", "theme: {theme}").format(theme=theme.current())
        elif row == "sound":
            self.msg = t("opt_snd_res", "sound: {val}").format(val=self._value('sound'))
        elif row == "account":
            if r:
                self._done = ("account",) + tuple(r)   # app does the heavy lifting
            else:
                self.msg = t("opt_msg_kept_account", "kept your account.")
        elif row == "language":
            if r:
                import tuipet.utils.persistence.settings_io as settings_io
                from tuipet.i18n.translator import set_language
                settings_io.set_saved_language(r[0])
                set_language(r[0])
                self.msg = t("opt_msg_lang_res", "language: {lang}").format(lang=r[0])

    def key(self, k: Any) -> Any:
        if self.sub_key(k, self._sub_done):
            if self._done is not None:
                r, self._done = self._done, None
                return ("done", r)
            return None
        if self.confirm_restart:
            if k in ("enter", "space"):
                return ("done", ("restart",))
            if k == "escape":
                self.confirm_restart = False
                self.msg = t("opt_msg_restart_later", "later — the update applies on your next launch")
            return None
        if self.confirm_new:
            if k in ("enter", "space"):    # SPACE = ENTER like the restart
                return ("done", ("new",))  # confirm right above (parity 07-18)
            if k == "escape":
                self.confirm_new = False
                self.msg = t("opt_msg_kept_pet", "{name} mantido.").format(name=self.pet.name)
            return None
        if self.confirm:
            if k == "escape":
                self.confirm, self.buf = False, ""
                self.msg = t("opt_msg_kept_everything", "tudo mantido.")
            elif k == "enter":
                if self.buf.strip().upper() == "YES":
                    return ("done", ("erase",))
                self.confirm, self.buf = False, ""
                self.msg = t("opt_msg_not_yes", "isso não foi SIM — tudo mantido.")
                self.sfx = "error"  # type: ignore
            elif k == "backspace":
                self.buf = self.buf[:-1]
            elif len(k) == 1 and k.isprintable():
                self.buf = (self.buf + k)[:8]
            return None
        if k in ("up", "k"):
            self.cursor = (self.cursor - 1) % len(_ROWS)
            self.msg = ""              # feedback yields to the new row's description
        elif k in ("down", "j"):
            self.cursor = (self.cursor + 1) % len(_ROWS)
            self.msg = ""
        elif k == "a" and _ROWS[self.cursor] == "update":
            # opt out of the launch auto-install (Joel 2026-07-14: it is ON by
            # default, but nobody should be forced to have pip run for them)
            on = persistence.set_auto_update(not persistence.get_auto_update())
            self.msg = (t("opt_msg_auto_upd_on", "auto-update on — new releases install at launch")
                        if on else t("opt_msg_auto_upd_off", "auto-update off — you'll be told, not updated"))
            self.sfx = "confirm"  # type: ignore
        elif k in ("enter", "space"):
            row = _ROWS[self.cursor]
            if row == "theme":
                self._sub_row = row  # type: ignore
                self.sub = ThemePanel(on_change=self.on_theme_change)  # type: ignore
            elif row == "sound":
                self._sub_row = row  # type: ignore
                self.sub = SoundPanel(self.sound_get, self.sound_toggle)  # type: ignore
            elif row == "account":
                from tuipet.ui.screens.accountscreen import AccountPanel
                self._sub_row = row  # type: ignore
                self.sub = AccountPanel(  # type: ignore
                    note=t("opt_msg_switch_login", "Switch: the pet parks with this login."))
            elif row == "cloud":
                on = persistence.set_cloud_sync(not persistence.get_cloud_sync())
                self.msg = (t("opt_msg_cloud_on", "cloud sync on — saves follow your account")
                            if on else t("opt_msg_cloud_off", "cloud sync off — this device saves locally only"))
                self.sfx = "confirm"  # type: ignore
            elif row == "update":
                # first ENTER checks; with a newer release known, the second
                # ENTER actually INSTALLS it (Joel 2026-07-13: "make the update
                # option actually update the game").  The game also installs
                # new releases for itself at launch -- `a` opts out of that.
                hint = self.update_hint() if self.update_hint is not None else ""
                if self._updated or "installed" in (hint or ""):
                    # a launch (or earlier) auto-update ALREADY wrote the new
                    # version to disk -- but this process is still running the
                    # OLD code it imported at startup, so there is nothing left
                    # to install: ENTER RESTARTS to apply it.  Without this the
                    # row read "restart to apply" (see _value) yet ENTER
                    # re-checked and said "up to date" -- current_version() reads
                    # the freshly-upgraded disk -- stranding the player on the
                    # old code with no way to relaunch from Options (Joel
                    # 2026-07-20: "the first reset should update the game").
                    return ("done", ("restart",))
                if self._upd and self._upd != "…":
                    self._install_update()
                else:
                    self._check_updates()
            elif row == "keys":
                self._sub_row = row  # type: ignore
                self.sub = KeysPanel(self.bindings)  # type: ignore
            elif row == "language":
                self._sub_row = row  # type: ignore
                self.sub = LanguagePanel()  # type: ignore
            elif row == "new":
                # a LIVING pet gets a confirm: "New egg" replaced it instantly
                # while Erase demanded a typed YES (sweep 2026-07-14).  A dead
                # pet or an unhatched egg hands off without ceremony.
                if getattr(self.pet, "dead", False) or self.pet.stage == "Egg":
                    return ("done", ("new",))
                self.confirm_new = True
                self.msg = t("opt_msg_retire_prompt", "retire {name} (gen {gen}) for a new egg?").format(name=self.pet.name, gen=self.pet.generation)
            elif row == "erase":
                self.confirm, self.buf = True, ""
                self.msg = t("opt_msg_erase_prompt", "erase EVERYTHING? type YES + ENTER")
        elif k in ("escape", "g"):     # g opened it; g also closes (nav-quit rule)
            return ("done", None)
        return None

    def _value(self, row: Any) -> Any:
        if row == "theme":
            return theme.current()
        if row == "sound":
            return _sound_value(self.sound_get(), with_volume=True)
        if row == "account":
            return persistence.get_account()[0] or t("opt_val_not_signed_in", "not signed in")
        if row == "cloud":
            import os as _o
            if _o.environ.get("TUIPET_NO_SYNC"):
                return t("opt_val_off_nosync", "off (TUIPET_NO_SYNC)")   # the env override outranks the toggle
            return t("opt_val_on", "on") if persistence.get_cloud_sync() else t("opt_val_off", "off")
        if row == "update":
            if self._installing:
                return t("opt_val_updating", "updating…")
            if self.confirm_restart:
                return t("opt_val_restart_now", "restart now? ENTER")
            hint = self.update_hint() if self.update_hint is not None else ""
            if self._updated or "installed" in (hint or ""):
                # (was getattr(self.pet, "_updated_to") -- a DEAD read: the
                # launch installer sets the flag on the APP, never the pet;
                # the update_hint lambda carries the app's message.  Bug-
                # report sweep 2026-07-19.)
                return t("opt_val_restart_apply", "restart to apply")
            if not persistence.get_auto_update():
                return t("opt_val_v_auto_off", "v{ver} · auto off").format(ver=update_check.current_version() or 'dev')
            if self._upd == "…":
                return t("opt_val_checking", "checking…")
            if self._upd:
                return t("opt_val_install", "{upd} · ENTER installs").format(upd=self._upd)
            if self._upd == "":
                return t("opt_val_uptodate", "up to date")
            if self.update_hint is not None and self.update_hint():
                return t("opt_val_new_ver", "new version out!")   # the boot check already knows
            return t("opt_val_v", "v{ver}").format(ver=update_check.current_version() or 'dev')
        if row == "keys":
            return t("opt_val_bindings", "{len} bindings").format(len=len(self.bindings))
        if row == "language":
            from tuipet.i18n.translator import get_language
            return get_language().upper()
        if row == "new":
            return t("opt_val_gen_next", "gen {gen} next").format(gen=self.pet.generation + 1)
        return t("opt_val_everything", "everything")          # the confirm page spells out what that means

    def text(self) -> Any:
        if self.sub is not None:
            return self.sub.text()
        out = menu.header(t("opt_hdr_options", "OPTIONS"), persistence.get_account()[0] or "")
        if self.confirm_restart:
            out.append_text(menu.blanks(1))
            out.append_text(menu.note(t("opt_conf_upd_1", "Update installed.")))
            out.append_text(menu.note(t("opt_conf_upd_2", "Restart into the new version now?")))
            out.append_text(menu.blanks(1))
            out.append_text(menu.note(t("opt_conf_upd_3", "Your save is already written.")))
            out.append_text(menu.blanks(2))
            out.right_crop(1)          # the strip owns the keys (QOL 2026-07-23)
            return out
        if self.confirm:
            out.append_text(menu.blanks(1))
            out.append_text(menu.note(t("opt_conf_erase_1", "This erases the pet, progress,")))
            out.append_text(menu.note(t("opt_conf_erase_2", "eggs and your login — for keeps.")))
            out.append_text(menu.blanks(1))
            out.append_text(menu.row(t("opt_conf_erase_prompt", "type YES:  {buf}_").format(buf=self.buf), True))
            out.append_text(menu.blanks(2))
            out.right_crop(1)          # the strip owns the keys (QOL 2026-07-23)
            return out
        for i, row in enumerate(_ROWS):
            out.append_text(menu.row(f"{_get_label()[row]:<16} {self._value(row)[:18]}",
                                     i == self.cursor))
        out.append_text(menu.blanks(7 - len(_ROWS)))
        out.append_text(menu.note(self.msg or _get_desc()[_ROWS[self.cursor]],
                                  tick=self.frame_i))
        out.right_crop(1)              # the strip owns the keys (QOL 2026-07-23)
        return out
