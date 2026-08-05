from __future__ import annotations
import tuipet.data.loaders.data as data
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
import tuipet.utils.theme as theme
class CloudMixin:
    def _start_sync(self) -> None:
            """Spin up the background cloud-save push client once an account exists
            (idempotent). The startup pull already ran in main(); this handles pushes."""
            from tuipet import SERVIDOR_ONLINE
            if not SERVIDOR_ONLINE or self._sync is not None:  # type: ignore
                return
            if not persistence.sync_enabled():
                return                       # opted out (TUIPET_NO_SYNC or the options toggle)
            name, pw = persistence.get_account()
            if not name:
                return                       # no account yet (first launch) — started after account setup
            self._sync = net.SyncClient(_lobby_uri(), name, pw)  # type: ignore
            self._sync_worker = self.run_worker(self._sync.run(), name="sync",  # type: ignore
                                                exclusive=False)

    def _stop_sync(self) -> None:
            """Tear the pusher down for real: the stop flag alone left the old
            account's connection parked in `async for` until the socket dropped --
            a live sync ghost in the roster after every account switch (netplay
            audit 2026-07-18).  Cancel the worker like the lobby's."""
            if self._sync is not None:
                self._sync._stop = True
                self._sync = None
            w = getattr(self, "_sync_worker", None)
            if w is not None:
                w.cancel()
                self._sync_worker = None

    def _push_cloud(self) -> None:
            """Queue the current pet's save for upload (no-op until the account/sync exists)."""
            from tuipet import SERVIDOR_ONLINE
            if SERVIDOR_ONLINE and self._sync is not None and self.pet is not None and persistence.sync_enabled():  # type: ignore
                self._sync.push_save(persistence.to_save_dict(self.pet))  # type: ignore

    def _warn_if_cloud_dropped(self) -> None:
            """The cloud is refusing (or we're refusing to send) this device's
            saves.  The local save is fine, but cross-device sync is dead -- and
            we used to never mention it (swallowed-failure sweep 2026-07-13), or
            worse, blame "a newer session" for every cause (audit 2026-07-18:
            format rejections and oversized saves wore the wrong warning)."""
            sync = getattr(self, "_sync", None)
            if sync is None:
                return
            if getattr(sync, "cloud_dropped", False):
                msg = ("⚠ Sincronização desligada — tuipet aberto em outra sessão. "
                       "This device saves locally only.")
            elif getattr(sync, "save_invalid", False):
                msg = ("⚠ Sincronização desligada — servidor rejeitou este save "
                       "format. This device saves locally only.")
            elif getattr(sync, "save_too_big", False):
                msg = ("⚠ Sincronização desligada — save muito grande "
                       "sync. This device saves locally only.")
            elif getattr(sync, "last_error", ""):
                msg = f"⚠ Problema de sincronização — {sync.last_error}"
            else:
                return
            if getattr(self, "_cloud_warned", None) == msg:
                return                       # one flash per distinct cause
            self._cloud_warned = msg
            self.flash(f"[{theme.NEG}]{msg}[/]")  # type: ignore

    def _flush_cloud_on_quit(self) -> None:
            """Best-effort blocking push so the final state is captured cloud-side."""
            if self._sync is None:
                return
            try:
                name, pw = persistence.get_account()
                cloudsync.push_save(_lobby_uri(), name, pw,  # type: ignore
                                    persistence.to_save_dict(self.pet), timeout=2.0)  # type: ignore
            except Exception:
                pass

