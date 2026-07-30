"""The ALBUM — the cross-generation bestiary (Joel 2026-07-21: "lets build
the album screen").

The device has tracked every species ever raised since the collection
long-game arc (persistence album, canonical nums), but only ever SHOWED
the count on the datacore trophy page — a scoreboard pointing at a book
that didn't exist.  THIS is the book: every name-canonical roster form in
dex order, a discovered entry wearing its name and stage, the rest masked
"???" (the datacore hidden-evo reveal language).  ENTER opens one entry's
page — the REAL 16x16 rip bobbing live for a discovered form, its
silhouette (the core-gaze tease) for one still out there.  Data only:
roster = data.album_roster() (the trophy denominator's own set), seen =
persistence.get_album(); nothing here is guessed or drawn.

↑↓ browse, PgUp/PgDn leap, ENTER view, ←→ page inside the book, ESC out.
Opened from the datacore TROPHIES page (where its count already lived)."""
from __future__ import annotations
from rich.text import Text
import tuipet.data.loaders.data as data
import tuipet.ui.components.menu as menu
import tuipet.utils.persistence as persistence
from tuipet.utils.theme import INK, INK_B, DIM, LCD_ON, LCD_BG    # noqa: F401  (theme.apply propagation)
from tuipet.i18n.translator import t

VIS = 9                      # list rows shown at once (the egg-guide window)
IMG_W, IMG_H = 40, 16        # detail pixel area (8 character rows)


def route_hint(num):
    """How an undiscovered form is reached (gameplay polish #15,
    2026-07-22): the book was a completion checklist with the HOW
    invisible -- "keep raising" over hundreds of masked entries, while
    lines.load_lines() knew exactly which line holds each form.  Named
    routes only, never names of forms: the egg/line that raises it, else
    the off-chart door its own requirements declare (armor / jogress /
    a Field divergence).  Data only, nothing guessed."""
    import tuipet.core.egg as egg_mod
    import tuipet.core.lines as lines
    lids = {lid for lid, line in lines.load_lines().items()
            if num in line["members"]}
    if lids:
        for i in range(egg_mod.count()):
            for target in egg_mod.hatch_targets(i):
                _root, lid = lines.canonical_root(target)
                if lid in lids:
                    return t("album_raised_on_egg_line", "raised on the {name} line").format(name=egg_mod.hatch_name(i))
        return t("album_raised_on_line", "raised on a line")          # a line holds it; no listed egg
    req = data.load_requirements().get(num, {})
    if req.get("evol_item", -1) != -1:
        return t("album_armor_jump", "an armor jump reaches it")
    if req.get("special", "None") != "None":
        return t("album_jogress", "a jogress reaches it")
    _, by_num = data.load_sprites()
    field = (by_num.get(num) or {}).get("field", "") or ""
    if field and field != "None":
        return t("album_field_divergence", "a {field} divergence reaches it").format(field=data.pretty_field(field))
    return t("album_keep_raising", "keep raising")


class AlbumPanel:
    def __init__(self, pet=None):
        self.pet = pet
        self.roster = data.album_roster()
        self.seen = set(persistence.get_album()) & set(self.roster)
        self.n = len(self.roster)
        self.i = 0
        self.detail = False
        self.frame_i = 0
        self.sfx = None

    # ---- panel protocol --------------------------------------------------
    def anim(self):
        self.frame_i += 1

    def strip(self):
        if self.detail:
            return menu.hints(("←→", t("album_key_browse", "browse")), ("ESC", t("album_key_back", "back")))
        return menu.hints(("↑↓", t("album_key_browse", "browse")), ("ENTER", t("album_key_view", "view")),
                          ("ESC", t("album_key_out", "out")))

    def key(self, k):
        if self.detail:
            if k in ("left", "h", "up", "k"):
                self.i = (self.i - 1) % self.n
            elif k in ("right", "l", "down", "j"):
                self.i = (self.i + 1) % self.n
            elif k == "pageup":                # the list's leap, in the book too
                self.i = (self.i - (VIS - 1)) % self.n
            elif k == "pagedown":
                self.i = (self.i + (VIS - 1)) % self.n
            elif k == "escape":
                self.detail = False
            return None
        # the list wraps like every sibling cursor list (and like this
        # screen's own detail view) -- it was the longest list in the game
        # with a dead key at each end (QOL sweep 2026-07-23)
        if k in ("up", "k"):
            self.i = (self.i - 1) % self.n
        elif k in ("down", "j"):
            self.i = (self.i + 1) % self.n
        elif k == "pageup":                  # page jumps, lobby-chat style
            self.i = max(0, self.i - (VIS - 1))
        elif k == "pagedown":
            self.i = min(self.n - 1, self.i + (VIS - 1))
        elif k in ("enter", "space"):
            self.detail = True
        elif k == "escape":
            return ("done", None)
        return None

    # ---- the list ----------------------------------------------------------
    def _rec(self, num):
        return data.load_sprites()[1].get(num) or {}

    def _note(self, num):
        if num not in self.seen:
            return t("album_not_yet_disc", "not yet discovered")
        rec = self._rec(num)
        fld = data.pretty_field(rec.get("field", "") or "")
        return t("album_no", "No. #{num}").format(num=num) + (f" · {fld}" if fld else "")

    def _list_scene(self):
        out = menu.header(t("album_hdr_album", "ALBUM"), f"{len(self.seen)}/{self.n}")

        def fmt(num, j):
            cur = j == self.i
            seen = num in self.seen
            body = INK_B if cur else (INK if seen else DIM)
            t = Text()
            t.append(("▸" if cur else " ")
                     + ("✓" if seen else "✗") + " ", style=body)
            name = self._rec(num).get("name", "?") if seen else "???"
            t.append(f"{name[:22]:<23}", style=body)
            tag = self._rec(num).get("stage", "")[:10] if seen else ""
            t.append(f"{tag:>10}\n", style=INK_B if cur else DIM)
            return t

        self.i = menu.list_window(out, self.roster, self.i, VIS, fmt)
        out.append_text(menu.note(self._note(self.roster[self.i]),
                                  tick=self.frame_i))
        out.right_crop(1)     # keys ride the strip (the egg-guide law)
        return out

    # ---- one entry's page ----------------------------------------------------
    def _detail_scene(self):
        from tuipet.core.datacore import silhouette
        num = self.roster[self.i]
        seen = num in self.seen
        rec = self._rec(num)
        name = rec.get("name", "?") if seen else "???"
        out = menu.header(t("album_hdr_name", "ALBUM  {name}").format(name=name[:20].upper()), f"#{num}")
        rows = (data.bob_frame(num, self.frame_i) if seen
                else silhouette(data.frames_for(num)[0])) or []
        buf = [[0] * IMG_W for _ in range(IMG_H)]
        w = max((len(r) for r in rows), default=0)
        ox, oy = (IMG_W - w) // 2, (IMG_H - len(rows)) // 2
        for y, line in enumerate(rows):
            for x, ch in enumerate(line):
                if ch == "1" and 0 <= oy + y < IMG_H and 0 <= ox + x < IMG_W:
                    buf[oy + y][ox + x] = 1
        bt = Text()
        for cy in range(IMG_H // 2):
            ty, byy = cy * 2, cy * 2 + 1
            for cx in range(IMG_W):
                tc = LCD_ON if buf[ty][cx] else LCD_BG
                bc = LCD_ON if buf[byy][cx] else LCD_BG
                bt.append("▀", style=f"{tc} on {bc}")
            bt.append("\n")
        out.append_text(bt)
        if seen:
            info = " · ".join(x for x in (
                rec.get("stage", ""), rec.get("attribute", ""),
                data.pretty_field(rec.get("field", "") or ""),
                rec.get("element", "")) if x)
        else:
            # the route home rides the note (marquee handles the length);
            # cached per entry -- the egg sweep is loads, not per-frame work
            self._routes = getattr(self, "_routes", {})
            if num not in self._routes:
                self._routes[num] = route_hint(num)
            info = t("album_not_yet_disc_route", "not yet discovered — {route}").format(route=self._routes[num])
        out.append_text(menu.note(info, tick=self.frame_i))
        out.right_crop(1)     # keys ride the strip (the egg-guide law)
        return out

    def text(self):
        return self._detail_scene() if self.detail else self._list_scene()
