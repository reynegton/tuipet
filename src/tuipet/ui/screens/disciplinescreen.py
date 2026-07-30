"""Discipline — praise & scold, RESTORED (canon restoration B,
2026-07-23, Joel: "it was wrongfully stripped... whatever is canon
bring back").

The device pair as a two-row picker: PRAISE answers a proud moment (a
battle win, a mega drill — a ~10 game-min window), SCOLD answers the
tantrum call.  The gauge is obedience 0..MAX_OBEDIENCE (canon 150).  Wrong-moment verbs cost
nothing but land nothing (the no-praise-farming rule); refusals stay
soft — discipline is the tantrum economy, not a leash.
"""
from __future__ import annotations

import tuipet.ui.components.menu as menu
from tuipet.core.petbase import MAX_OBEDIENCE
from tuipet.utils.theme import INK, INK_B, DIM, SEL    # noqa: F401  (theme.apply propagation)
from tuipet.i18n.translator import t

_ROWS = (
    ("disc_lbl_praise", "Praise", "disc_desc_praise", "warmth for a proud moment"),
    ("disc_lbl_scold", "Scold", "disc_desc_scold", "answer the tantrum call"),
)


class DisciplinePanel:
    def __init__(self, pet):
        self.pet = pet
        self.cursor = 1 if pet.discipline_call else 0   # an open call preselects Scold
        self.frame_i = 0
        self.sfx = None

    def anim(self):
        self.frame_i += 1

    def strip(self):
        return menu.hints(("ENTER", t("disc_hint_apply", "apply")), ("ESC", t("disc_hint_back", "back")))

    def key(self, k):
        if k in ("up", "down", "j", "k"):
            self.cursor = 1 - self.cursor
        elif k in ("enter", "space"):
            p = self.pet
            # did the verb LAND?  Read the moment BEFORE spending it: a
            # praise inside its window / a scold answering a real tantrum
            # earns the house-screen show, a wrong-moment verb earns only
            # the small pose (E1, 2026-07-23).  Detected on the MOMENT,
            # not on the gauge -- obedience at the 100 clamp would make a
            # landed praise look like it did nothing.  (The asleep/dead/
            # young guards live at the door in action_discipline, so a
            # panel that is open always reaches the verb.)
            if self.cursor == 0:
                landed, msg, show = (p.world_seconds <= getattr(p, "praise_window", 0.0),
                                     p.praise(), "cheer")
            else:
                landed, msg, show = bool(p.discipline_call), p.scold(), "jeer"
            return ("done", (str(msg), show if landed else None))
        elif k == "escape":
            return ("done", None)
        return None

    def _state_line(self):
        p = self.pet
        if p.discipline_call:
            return t("disc_msg_acting_up", "it is ACTING UP — a scold lands")
        if p.world_seconds <= getattr(p, "praise_window", 0.0):
            return t("disc_msg_proud", "a PROUD moment — praise lands")
        return t("disc_msg_calm", "all calm — neither will land")

    def text(self):
        out = menu.header(t("disc_hdr_disc", "DISCIPLINE"), t("disc_hdr_manners", "manners {ob}/{max}").format(ob=self.pet.obedience, max=MAX_OBEDIENCE))
        for i, (lbl_key, lbl_def, desc_key, desc_def) in enumerate(_ROWS):
            sel = i == self.cursor
            label = t(lbl_key, lbl_def)
            desc = t(desc_key, desc_def)
            out.append(f" {'▸' if sel else ' '} {label:<8}", style=SEL if sel else INK_B)
            out.append(f"{desc}\n", style=DIM)
        out.append("\n")
        out.append(f" {self._state_line()}\n", style=INK)
        out.append_text(menu.blanks(9 - 4))
        out.append_text(menu.footer(t("disc_footer_strip", "ENTER apply  ↑↓ pick  ESC out")))
        return out
