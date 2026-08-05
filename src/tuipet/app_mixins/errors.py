import tuipet.utils.theme as theme
import tuipet.network.net as net
from typing import Any
import os
from tuipet.appboot import _lobby_uri, host_platform
import tuipet.network.cloudsync as cloudsync
from tuipet.utils import persistence
from tuipet.i18n.translator import t

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from typing import Protocol, Any
    class AppProtocol(Protocol):
        pet: Any
        _boot_version: str
        def _verdict(self, msg: str) -> None: ...
        def beep(self, name: str, bell: bool = True) -> None: ...
        def repaint(self) -> None: ...
        def _stop_sync(self) -> None: ...
        def _start_sync(self) -> None: ...
        def _open_mode(self, panel: Any, on_close: Any = None) -> None: ...
        def _hatch_new(self, egg_type: Any, gen: int) -> None: ...
else:
    class AppProtocol:
        pass

class ErrorsMixin(AppProtocol):
    async def _send_bug(self, text: str, meta: Any, name: str) -> None:
            ok = await net.submit_bug(_lobby_uri(), text, meta, name=name)
            if ok:
                self._verdict(t("app_msg_bug_sent", "Bug report sent \u2014 thank you!"))
            elif persistence.add_pending_bug(dict(meta, text=text, name=name)):
                self._verdict(t("app_msg_bug_offline", "Offline \u2014 saved; it will send next time you are online."))
            else:
                # the stash failed too (a read-only save dir): do not promise a
                # send we cannot make (swallowed-failure sweep 2026-07-13)
                self._verdict(f"[{theme.NEG}]Couldn't send or save that report \u2014 sorry.[/]")

    async def _flush_bugs(self) -> None:
            """Best-effort resend of stashed bugs.  READ-then-rewrite (bug audit
            2026-07-19): the old take-then-send deleted the stash up front, so
            a quit mid-flush lost every unsent report (the round-5 PM lesson).
            A crash now leaves the original file -- a bounded duplicate send
            beats a lost report (the server's per-connection cap absorbs it)."""
            pending = persistence.peek_pending_bugs()
            if not pending:
                return
            left, outage = [], False
            for rec in pending:
                text, name = rec.get("text", ""), rec.get("name", "")
                if not text:
                    continue          # a damaged line: drop it, never re-stash forever
                if outage:            # already hit an outage: keep the rest, in order
                    left.append(rec)
                    continue
                meta = {kk: vv for kk, vv in rec.items() if kk not in ("text", "name")}
                if not await net.submit_bug(_lobby_uri(), text, meta, name=name):
                    left.append(rec)
                    outage = True
            persistence.write_pending_bugs(left)

    def _bug_meta(self) -> Any:
            import platform as _pf
            # the RUNNING build's version, captured at boot (audit 2026-07-25):
            # the in-session updater pip-installs the NEW release into this
            # environment, so a send-time metadata read attributed a bug to a
            # build that never touched the player's screen
            ver = self._boot_version
            p = self.pet
            return {"version": ver,
                    "platform": "%s py%s" % (host_platform(), _pf.python_version()),
                    "pet": {"num": getattr(p, "num", 0), "name": getattr(p, "name", ""),
                            "stage": getattr(p, "stage", ""),
                            "gen": getattr(p, "generation", 0)}}

    def _handle_exception(self, error: Exception) -> None:
            # Last-chance honesty (sweep 2026-07-14): save the pet, keep the
            # traceback, queue a bug report -- THEN let Textual show its crash
            # screen.  A raw panic used to be the whole story, with the last ~10s
            # of play lost and the reporter never offered.
            try:
                persistence.save(self.pet)
            except Exception:
                pass
            log = None
            try:
                log = persistence.write_crash_log(error)
            except Exception:
                pass
            try:
                import traceback
                tail = "".join(traceback.format_exception(
                    type(error), error, error.__traceback__))[-1500:]
                persistence.add_pending_bug(dict(
                    self._bug_meta(), name=persistence.get_account()[0],
                    text=f"[auto] crash: {error!r}\n{tail}"))
            except Exception:
                pass
            self._crash_note = ("tuipet crashed — your pet was saved."
                                + (f"  Details: {log}" if log else "")
                                + "  A report goes out next launch.")
            super()._handle_exception(error)  # type: ignore
