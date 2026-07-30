"""Backgrounds — the scene picker (restored 2026-07-17: "add the e action
back to change backgrounds").

The clone's picker grammar, minus the price walls it had already dropped:
the LCD live-previews the pet standing in the browsed backdrop, the picker
line rides the #msg strip, ENTER commits.  Row 0 is the egg's own scene
(the default wiring stays the truth; a pick merely overrides it)."""
from __future__ import annotations
import tuipet.utils.backgrounds as bgs
import tuipet.data.loaders.data as data
import tuipet.utils.grid as grid

from tuipet.utils.theme import LCD_ON, LCD_BG, INK, INK_B, DIM, SEL    # noqa: F401  (theme.apply propagation)
import tuipet.ui.components.menu as menu
from tuipet.i18n.translator import t

COLS, ROWS = 40, 12


class BackgroundPanel:
    def __init__(self, pet):
        self.pet = pet
        self.rows = [""] + list(bgs.PICKS)          # "" = follow the egg
        self.cursor = next((i for i, k in enumerate(self.rows)
                            if k == pet.bg_pick), 0)
        self.frame_i = 0
        self.msg = t("bg_msg_intro", "pick a scene — it hangs behind the mon")
        self.sfx = None

    def anim(self):
        self.frame_i += 1

    def _key_of(self, row):
        """The scene a row previews (row 0 = the egg's own)."""
        return row or bgs.scene_for_egg(self.pet.egg_type)

    def key(self, k):
        if k in ("up", "k", "left", "h"):          # the strip reads sideways too
            self.cursor = (self.cursor - 1) % len(self.rows)
        elif k in ("down", "j", "right", "l"):
            self.cursor = (self.cursor + 1) % len(self.rows)
        elif k in ("pageup", "pagedown"):
            # 31 scenes one tap at a time was the worst walk in the game
            # (help audit 2026-07-21).  The browser previews ONE scene, so
            # there is no window to page -- an 8-row leap matches the VIS
            # stride every other list jumps by.
            self.cursor = menu.page_step(self.cursor, len(self.rows), 8, k)
        elif k in ("enter", "space"):
            key = self.rows[self.cursor]
            if key == self.pet.bg_pick:
                self.msg = t("bg_msg_already_up", "Already up.")
            else:
                self.msg = self.pet.pick_background(key)
                self.sfx = "confirm"
        elif k in ("escape", "n"):
            return ("done", self.msg)
        return None

    def _name(self, row):
        if not row:
            return t("bg_msg_eggs_own", "{name} (egg's own)").format(name=bgs.name(bgs.scene_for_egg(self.pet.egg_type)))
        return bgs.name(row)

    def _tag(self, row):
        return t("bg_msg_here", "● here") if row == self.pet.bg_pick else ""

    def strip(self):
        # budgeted to HUD_W 40 (menu-bounds law): the name field scrolls,
        # the chrome stands still
        from tuipet.utils.render import marquee
        return (f"[b]▸{marquee(self._name(self.rows[self.cursor]), 14, self.frame_i // 2)}[/]"
                f" {self.cursor + 1}/{len(self.rows)}"
                f" {t('bg_hint_footer', '[dim]←→ ENTER ESC[/]')}")

    def text(self):
        """The browsed backdrop AS A SCENE: the pet stands in it --
        window-shopping included (render-only preview)."""
        key = self._key_of(self.rows[self.cursor])
        fr = data.bob_frame(self.pet.num, self.frame_i,
                            egg_type=getattr(self.pet, "egg_type", 0))
        placements = [grid.center(grid.prep(fr, ph=ROWS * 2))] if fr else []
        return menu.paint(placements, self.pet.background(file=key),
                          rows=ROWS, cols=COLS)
