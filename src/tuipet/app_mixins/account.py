from typing import Any
import tuipet.network.cloudsync as cloudsync
from tuipet.utils import persistence
from tuipet.appboot import _lobby_uri
from tuipet.core.pet import Pet
from tuipet.ui.screens import eggselectscreen
from tuipet.i18n.translator import t
from tuipet.app import _hud_esc

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

class AccountMixin(AppProtocol):
    async def _switch_account(self, name: str, pw: Any) -> None:
            """Sign in as another account (OPTIONS → Account).  The current pet is
            parked with the OLD account's cloud first (switch back any time), then
            the new account's cloud save replaces the local one — or the egg
            carousel opens when it has none.  A wrong password or an unreachable
            lobby aborts WITHOUT switching (probe distinguishes the two — pull_save
            can't, and a typo'd password must not strand the player on a fresh
            start).  Device-lifetime progress (album, lifetime wins, owned eggs)
            stays local, like canon's device-scoped Shared file."""
            import asyncio
            old_name, old_pw = persistence.get_account()
            self._verdict(t("app_msg_switch_acc", "Switching account…"))
            verdict, save = await asyncio.to_thread(
                cloudsync.probe, _lobby_uri(), name, pw)
            if verdict == "badpw":
                self._verdict(t("app_msg_wrong_pw", "Wrong password for that name."))
                self.beep("error", bell=False)
                return
            if verdict != "ok":
                self._verdict(t("app_msg_lobby_fail", "Can't reach the lobby — try again online."))
                self.beep("error", bell=False)
                return
            if save is not None:
                # validate BEFORE committing to the switch: an unreadable cloud
                # blob must not cost the player their current login (the same
                # strict probe sync_down_at_startup runs)
                pet_probe, _ = persistence.pet_from_save(dict(save),
                                                         strict=True)
                if pet_probe is None:
                    self._verdict(t("app_msg_cloud_bad", "That cloud save is unreadable — kept your account."))
                    self.beep("error", bell=False)
                    return
            persistence.save(self.pet)                   # type: ignore
            if old_name == name:
                # re-login to the SAME account: never park, never delete -- only
                # refresh from a STRICTLY newer cloud copy.  This path used to
                # skip the sync_down_at_startup timestamp guard, so a day-old
                # cloud save could overwrite a newer local pet -- and a cloud
                # with NO save yet fell through to delete() and destroyed the
                # local pet's only copies (gameplay audit 2026-07-19).
                if save is not None and (float(save.get("_saved_at") or 0)
                                         > persistence.local_saved_at()):
                    persistence.write_save_dict(save)
                    loaded, msg = persistence.load()
                    self.pet = loaded or Pet.new_egg()  # type: ignore
                    self._verdict(t("app_msg_signed_in", "Signed in as {name} — {msg}").format(name=_hud_esc(name), msg=msg or t('app_msg_welcome_back', 'welcome back!')))
                    self.repaint()
                else:
                    self._verdict(t("app_msg_signed_in_cur", "Signed in as {name} — this device is current.").format(name=_hud_esc(name)))
                return
            if old_name:
                parked = await asyncio.to_thread(        # last-write-wins guarded upload
                    cloudsync.push_save, _lobby_uri(), old_name, old_pw,
                    persistence.to_save_dict(self.pet))
                if not parked:
                    # push_save also answers False when the OLD cloud is already
                    # newer (another device carries this pet) -- that counts as
                    # parked.  Distinguish it from a real failed send.
                    cloud = await asyncio.to_thread(
                        cloudsync.pull_save, _lobby_uri(), old_name, old_pw)
                    parked = bool(cloud) and (float(cloud.get("_saved_at") or 0)
                                              >= persistence.local_saved_at())
                if not parked:
                    # the switch may not proceed until the pet has a durable copy
                    # somewhere -- the ignored push + delete() pair destroyed
                    # save.json AND .bak (gameplay audit 2026-07-19)
                    self._verdict(f"Couldn't park your pet with {_hud_esc(old_name)}"
                                  " — kept your account.")
                    self.beep("error", bell=False)
                    return
            self._stop_sync()                            # the old pusher must stop first
            #                                              (cancelled, not just flagged)
            persistence.set_account(name, pw)
            if save is not None:
                persistence.write_save_dict(save)
                loaded, msg = persistence.load()
                self.pet = loaded or Pet.new_egg()  # type: ignore
                self._start_sync()
                self._verdict(t("app_msg_signed_in", "Signed in as {name} — {msg}").format(name=_hud_esc(name), msg=msg or t('app_msg_welcome_back', 'welcome back!')))
                self.repaint()
            elif old_name:
                persistence.delete()                     # parked above: the old pet must not leak in
                self.pet = Pet.new_egg()  # type: ignore                 # placeholder until the carousel picks
                self._start_sync()
                self._verdict(t("app_msg_signed_in_fresh", "Signed in as {name} — a fresh start.").format(name=_hud_esc(name)))
                self._open_mode(eggselectscreen.EggSelectPanel(self.pet),
                                lambda et: self._hatch_new(et, 1))
            else:
                # no old account: the local pet was never parked ANYWHERE, and
                # deleting it here destroyed its only copies.  Adopt it into the
                # new account instead -- exactly what the first lobby login does:
                # the pet stays local and the sync pushes it up.
                self._start_sync()
                self._verdict(t("app_msg_signed_in_syncs", "Signed in as {name} — your pet syncs here now.").format(name=_hud_esc(name)))
                self.repaint()
