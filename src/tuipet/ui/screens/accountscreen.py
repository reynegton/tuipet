"""The name+password login card (split out of the lobby; modularize 2026-07-17).
(Round 35: the split's stranded boilerplate -- dead imports and the unused
MAX_PVP_* clamp constants (_clamp_card in lobbybout owns the real bounds) --
was cut; the cell-width law finally reached the name field.)"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union

from rich.cells import cell_len
from rich.text import Text

import tuipet.ui.components.menu as menu
from tuipet.utils.theme import INK, INK_B, DIM, SEL    # noqa: F401  (theme.apply propagation)
from tuipet.i18n.translator import t

_NAME_MAX = 24                  # the server's MAX_NAME: what you SEE is what
#                                 logs in (round 35: the buffer held 64 and
#                                 the confirm silently trimmed)
_PW_MAX = 64
_FIELD_W = 26                   # input cells shown (38 - the 12-col label)


def _tail(s: Any, w: Any) -> Any:
    """The LAST w CELLS of s -- an emoji/CJK glyph is two cells, and the old
    character slice let a wide name overrun the 40-col box (the CELL-WIDTH
    LAW, finally applied here -- round 35)."""
    while cell_len(s) > w:
        s = s[1:]
    return s


class AccountPanel:
    """Name + password entry. Tab/Up/Down switch fields; Enter on the password
    confirms when both are filled. Returns ("done", (name, password)), or
    ("done", None) on Esc. Used at first launch and to recover a failed login."""

    def __init__(self, name: str="", note: Optional[Any]=None) -> None:
        self.name_buf = name[:_NAME_MAX]
        self.pw_buf = ""
        self.field = "pw" if name else "name"
        self.note = note if note is not None else t("acc_msg_intro", "Name + password — the name is yours.")
        self.sfx = None
        self.frame_i = 0                # the note's marquee clock
        self.captures_text = True       # typing a name/password — never treat q as quit

    def anim(self) -> None:
        self.frame_i += 1

    def strip(self) -> Any:
        # "field", the grammar sweep's verb -- the lobby's login strip and
        # this one said different words for the same key (round 35)
        return menu.hints(("TAB", t("acc_hint_field", "field")), ("ENTER", t("acc_hint_go", "go")), ("ESC", t("acc_hint_back", "back")))

    def key(self, k: Any) -> Any:
        if k == "escape":
            return ("done", None)
        if k in ("tab", "up", "down"):
            self.field = "pw" if self.field == "name" else "name"
            return None
        if k == "enter":
            if self.field == "name":
                self.field = "pw"
                return None
            name = self.name_buf.strip()
            if name and self.pw_buf:
                return ("done", (name, self.pw_buf))
            # a missing field used to fail SILENTLY (round 35)
            self.note = t("acc_msg_both_please", "Name and password both, please.")
            self.sfx = "error"  # type: ignore
            return None
        attr = "name_buf" if self.field == "name" else "pw_buf"
        cur = getattr(self, attr)
        if k == "backspace":
            cur = cur[:-1]
        elif k == "space":
            cur = cur + " "
        elif len(k) == 1 and k.isprintable():
            cur = cur + k
        setattr(self, attr, cur[:_NAME_MAX if attr == "name_buf" else _PW_MAX])
        return None

    def text(self) -> Any:
        t_out = Text()
        t_out.append(t("acc_hdr_account", "  TUIPET ACCOUNT\n\n"), style=INK_B)
        # tail-window long input BY CELLS so a line never overruns the 40-col
        # LCD (the box CLIPS overflow live -- lobby audit 2026-07-04; the
        # password renders as 1-cell stars, so its char slice is safe)
        nm = _tail(self.name_buf + ("_" if self.field == "name" else ""), _FIELD_W)
        # the LAST typed character shows in plain while the field is active
        # (the phone-keyboard pattern): the first login CREATES the account,
        # so an unverifiable typo became the permanent sync password
        # (QOL sweep 2026-07-23).  Leaving the field stars it fully.
        stars = ("*" * (len(self.pw_buf) - 1) + self.pw_buf[-1]
                 if self.field == "pw" and self.pw_buf else "*" * len(self.pw_buf))
        pw = (stars + ("_" if self.field == "pw" else ""))[-_FIELD_W:]
        t_out.append(t("acc_lbl_name", "  name:     "), style=DIM)
        t_out.append(nm + "\n", style=INK_B if self.field == "name" else INK)
        t_out.append(t("acc_lbl_password", "  password: "), style=DIM)
        t_out.append(pw + "\n\n", style=INK_B if self.field == "pw" else INK)
        # keys ride the strip (round 35: the in-LCD hint line doubled it)
        # the note MARQUEES when over-wide (QOL sweep 2026-07-23: the hard
        # [:38] clip ate the actionable tail of long server rejections)
        t_out.append_text(menu.footer_note("  " + self.note, tick=self.frame_i))
        return t_out
