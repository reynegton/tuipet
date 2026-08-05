"""App plumbing (tier-3 split, 2026-07-17): platform detection, the
sound-preference file, the lobby URI, and the launch preflight.  Nothing
here touches the running game."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

import os
import platform as _pf  # noqa: F401
import sys  # noqa: F401

import tuipet.data.loaders.data as data    # noqa: F401
import tuipet.utils.persistence as persistence

MIN_COLS, MIN_ROWS = 77, 24     # the fixed layout: #left 44 + #stats 30 + chrome


def host_platform() -> Any:
    """The platform name for bug reports (hostinfo owns the detection so the
    sound backend and the bug feed can never disagree about the host)."""
    import tuipet.utils.hostinfo as hostinfo
    return hostinfo.host_platform()


def _sound_path() -> Any:
    return os.path.join(persistence.SAVE_DIR, "sound.txt")


def _load_sound() -> Any:
    try:
        return open(_sound_path()).read().strip() != "off"
    except OSError:
        return True


def _save_sound(on: Any) -> None:
    try:
        os.makedirs(persistence.SAVE_DIR, exist_ok=True)
        with open(_sound_path(), "w") as fh:
            fh.write("on" if on else "off")
    except OSError:
        pass


def _lobby_uri() -> Any:
    return os.environ.get("TUIPET_LOBBY_URL", "wss://ff3mmo.com/tuipet/")  # live lobby (TLS); override for local dev


def _preflight() -> None:
    """Fail loud and in plain words BEFORE the UI takes the terminal over
    (sweep 2026-07-14): damaged assets exit with the fix; a cramped window or
    a non-UTF-8 locale get a readable warning, then the game runs anyway --
    a clipped game beats a locked-out player."""
    try:
        data.load_sprites()
        data.load_orbs()
    except data.AssetsError as e:
        print(e)
        raise SystemExit(1)
    import shutil
    import time as _t
    warn = []
    cols, rows = shutil.get_terminal_size()
    if cols < MIN_COLS or rows < MIN_ROWS:
        warn.append(f"⚠ tuipet lays out for {MIN_COLS}×{MIN_ROWS}; this terminal is "
                    f"{cols}×{rows} — expect clipping.\n  (Enlarge the window, shrink "
                    f"the font, or rotate the phone.)")
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    if enc and "utf" not in enc:
        warn.append(f"⚠ tuipet draws with Unicode but this terminal reports '{enc}'.\n"
                    f"  If the art looks wrong:  export LANG=C.UTF-8")
    if warn:
        print("\n".join(warn))
        _t.sleep(2.5)



def main() -> None:
    from tuipet.utils.persistence.settings_io import load_settings
    from tuipet.i18n.translator import set_language
    import os
    saved_lang = load_settings().get("language")
    if saved_lang and saved_lang in ("pt", "en", "es", "fr", "de", "it", "zh-CN", "ja", "ru"):
        lang_code = saved_lang
    else:
        env_lang = os.environ.get("LANG", "") or os.environ.get("LC_ALL", "")
        # For languages like zh-CN we need to keep the dash format if applicable, but standard getdefaultlocale() gives zh_CN
        if env_lang and "zh" in env_lang.lower():
            lang_code = "zh-CN"
        else:
            lang_code = env_lang[:2].lower() if env_lang else "en"
        if lang_code not in ("pt", "en", "es", "fr", "de", "it", "zh-CN", "ja", "ru"):
            lang_code = "en"
    set_language(lang_code)
    _preflight()
    other = persistence.acquire_instance_lock()
    if other and not os.environ.get("TUIPET_FORCE"):
        print(f"tuipet is already running (pid {other}) — two copies would fight "
              f"over one save.\nClose the other one first, or set TUIPET_FORCE=1 "
              f"to override.")
        raise SystemExit(1)
    # Cross-device: pull a newer cloud save down BEFORE the app loads the pet, so
    # the normal load path picks it up (no mid-session swapping). Fail-soft.
    if persistence.sync_enabled():
        try:
            name, pw = persistence.get_account()
            if name:
                # the pull BLOCKS the launch up to its timeout -- offline,
                # that read as a silent ~3s hang (QOL sweep 2026-07-23);
                # same pre-UI print style as _preflight's warnings
                print("checking cloud save…", flush=True)
            import tuipet.cloudsync as cloudsync
            cloudsync.sync_down_at_startup(_lobby_uri(), name, pw)
        except Exception:
            pass
    from tuipet.app import TuiPetApp
    app = TuiPetApp()
    try:
        app.run()
    finally:
        persistence.release_instance_lock()
    if getattr(app, "_restart_after_exit", False):
        # the update's restart offer: the terminal is back to normal here,
        # so exec the NEW install in place.  The console script re-execs
        # itself; a `python -m tuipet` launch falls back to the interpreter.
        import sys as _sys
        argv0 = _sys.argv[0]
        if argv0 and os.access(argv0, os.X_OK) and not argv0.endswith(".py"):
            os.execv(argv0, _sys.argv)
        os.execv(_sys.executable, [_sys.executable, "-m", "tuipet"])
    if getattr(app, "_crash_note", None):
        print(app._crash_note)          # after Textual restores the terminal
    elif persistence.save_failed:
        # never print "Saved" over a disk that refused (silent-failure law)
        print("⚠ tuipet couldn't save — set TUIPET_SAVE_DIR to a writable folder.")
    elif getattr(app, "pet", None) is not None:
        nm = getattr(app.pet, "name", "") or "your pet"
        print(f"Saved ✓ — {nm} will be waiting.")
if __name__ == "__main__":
    main()
