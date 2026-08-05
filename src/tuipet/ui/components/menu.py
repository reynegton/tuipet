"""Shared chrome for the in-display menu panels: a consistent titled header
bar, selectable rows with a cursor, and a footer hint. Keeps every menu
looking the same and themed (colours come from theme via the INK/SEL names)."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from rich.text import Text
from tuipet.utils.theme import INK, INK_B, DIM, SEL
from wcwidth import wcswidth

def display_len(s: str) -> int:
    w = wcswidth(s)
    return len(s) if w < 0 else w

def slice_by_width(s: str, max_w: int) -> str:
    w = 0
    for i, c in enumerate(s):
        cw = wcswidth(c)
        w += 1 if cw < 0 else cw
        if w > max_w:
            return s[:i]
    return s

def ljust_width(s: str, max_w: int, fillchar: str = " ") -> str:
    w = display_len(s)
    if w >= max_w:
        return s
    return s + fillchar * (max_w - w)

W = 38  # content width inside the 40-wide LCD


def header(title: Any, right: str="") -> Any:
    """Title (left, bold) + optional right-aligned info, then a divider rule."""
    title = slice_by_width(title, W)
    t = Text()
    if right:
        gap = max(1, W - display_len(title) - display_len(right))
        t.append(title + " " * gap, style=INK_B)
        t.append(right, style=DIM)
    else:
        t.append(title, style=INK_B)
    t.append("\n")
    t.append("─" * W, style=DIM)
    t.append("\n")
    return t


def bar(title: Any, right: str="") -> Any:
    """Compact 1-line title (bold) + optional right-aligned info, no divider -
    for the scene-heavy activity screens that can't spare a line."""
    t = Text()
    title = slice_by_width(title, W)
    if right:
        gap = max(1, W - display_len(title) - display_len(right))
        t.append(title + " " * gap, style=INK_B)
        t.append(right, style=DIM)
    else:
        t.append(title, style=INK_B)
    t.append("\n")
    return t


def row(label: Any, selected: bool=False) -> Any:
    """A selectable list row with a ▸ cursor; selected rows render inverted."""
    prefix_and_label = ("▸ " if selected else "  ") + label
    line = ljust_width(slice_by_width(prefix_and_label, W), W)
    return Text(line + "\n", style=SEL if selected else INK)


NOTE_HOLD = 16   # marquee ticks held on the head each pass (~1.6s at the 10Hz clock)
NOTE_STEP = 2    # advance one character every N ticks (~5 chars/s, the HUD cadence)
NOTE_GAP = "      "

# the shared marquee clock: app.on_frame advances it at 10 Hz, so EVERY note
# scrolls when over-wide -- no screen can silently clip a message again (Joel
# 2026-07-15: "Too early to lay out the Futon" lost its tail in the bag).
# Panels may still pass their own frame counter; same cadence either way.
TICK = 0


def _scrolled(msg: str, tick: Any) -> Any:
    """The marquee window over an over-wide line (note()'s cadence: hold on
    the head, then one character per NOTE_STEP ticks, wrap through NOTE_GAP)."""
    if tick is None:
        tick = TICK
    loop = msg + NOTE_GAP
    cycle = len(loop) + NOTE_HOLD                 # hold on the head again each wrap
    pos = (tick // NOTE_STEP) % cycle
    off = max(0, pos - NOTE_HOLD)
    return slice_by_width((loop + loop)[off:], W)


def note(msg: str, tick: Optional[Any]=None) -> Any:
    """A status line (bold).  A message wider than the LCD used to CLIP silently
    (the battle menu's 'It IGNORED you!' vanished off the end -- audit 2026-07-04;
    then the bag's futon gate lost its tail -- 2026-07-15).  Long messages ALWAYS
    marquee now: panels pass their frame counter or inherit the module TICK."""
    if display_len(msg) <= W:
        return Text(msg + "\n", style=INK_B)
    return Text(_scrolled(msg, tick) + "\n", style=INK_B)


def footer(hint: Any) -> Any:
    """Control hints (dim), no trailing newline."""
    return Text(slice_by_width(hint, W), style=DIM)


def footer_note(msg: str, tick: Optional[Any]=None) -> Any:
    """A MESSAGE riding the footer slot (dim, no trailing newline).  Control
    footers still never marquee (the shop-tease pin) -- this variant is for
    data-driven lines that cannot be pre-fit: the egg-unlock teaser was
    silently clipping 32 of 46 hints mid-word (tidy sweep 2026-07-18)."""
    if display_len(msg) <= W:
        return Text(msg, style=DIM)
    return Text(_scrolled(msg, tick), style=DIM)


def hints(*pairs: Any) -> Any:
    """The MESSAGE-BOX hint line (hint overhaul, Joel 2026-07-10): keys bright,
    labels dim, dot-separated -- '[b]KEY[/][dim] label[/] [dim]·[/] ...'.  One
    convention for every screen's strip(); keep the PLAIN text <= 40 cols so
    the line holds still (live hints never marquee)."""
    return " [dim]·[/] ".join(f"[b]{k}[/][dim] {lbl}[/]" for k, lbl in pairs)


def blanks(n: Any) -> Any:
    return Text("\n" * max(0, n), style=INK)


def scene_ink(bgimg: Any) -> Any:
    """The paint() rule: sprites over a background image render as dark
    silhouettes (SIL_SCENE), plain LCD ink otherwise -- NEVER white over a bg.
    This one-line invariant lived in 13 hand-rolled copies across the scene
    screens (refactor 2026-07-05)."""
    from tuipet.utils.theme import SIL_SCENE, LCD_ON    # read late: theme.apply retints
    return SIL_SCENE if bgimg else LCD_ON


def paint(placements: Any, bgimg: Any, rows: int=12, cols: int=40, overlay: Optional[Any]=None, clip: Optional[Any]=None, overlay_free: Optional[Any]=None, free_ink: Optional[Any]=None) -> Any:
    """render_scene under the paint() rule -- the whole-LCD scene call the
    scene screens share (screens that reuse one ink across several render
    calls take scene_ink directly).  `clip` forwards the window-law rect --
    pass grid.WINDOW ONLY from callers whose canvas is a verified full-LCD
    12-row scene; screens that stage their own cinematics leave it None."""
    from tuipet.utils.render import render_scene
    from tuipet.utils.theme import LCD_BG
    return render_scene(placements, cols, rows, scene_ink(bgimg), LCD_BG,
                        overlay=overlay, bgimg=bgimg, clip=clip,
                        overlay_free=overlay_free, free_ink=free_ink)


IC_W, IC_ROWS = 10, 4   # the selected-item icon cell every icon view shares


def icon_cell(src: Any) -> Any:
    """Rasterise one sprite bitmap into the IC_W x IC_ROWS icon cell,
    auto-downsampled to fit both dimensions so it never clips."""
    blank = [" " * IC_W] * IC_ROWS
    sh = len(src) if src else 0
    sw = max((len(r) for r in src), default=0) if src else 0
    if not sw:
        return blank
    from tuipet.utils.render import downsample, bitmap_text
    from tuipet.utils.theme import LCD_ON, LCD_BG    # read late: theme.apply retints
    factor = max(1, -(-sw // IC_W), -(-sh // (2 * IC_ROWS)))
    bm = downsample(src, factor)
    if not max((len(r) for r in bm), default=0):
        return blank
    lines = [t.plain.ljust(IC_W)                # w <= IC_W (factor guarantees it)
             for t in bitmap_text(bm, LCD_ON, LCD_BG)]
    # short art anchors to the BASELINE, not the ceiling: foods sit on
    # plates, props sit on the ground -- a top-floated icon over a dead
    # bottom row reads as clipped (Joel's report 2026-07-19: "giga meal
    # sprite might be getting cut off in shop?" -- the 24x18 rip is
    # complete; the float was the lie)
    return (blank + lines)[-IC_ROWS:]


def item_icon(e: Any) -> Any:
    """A consumable/egg entry's icon as IC_ROWS cell lines.  ONE lookup for
    every icon view -- the shop, the bag, the feed menu and the town shops
    (refactor 2026-07-05); shop eggs ride their real egg frames."""
    fr = None
    if e and e.get("egg_idx") is not None:
        import tuipet.core.egg as egg_mod
        fr = egg_mod.frames(e["egg_idx"])
    elif e:
        import tuipet.data.loaders.data as data
        fr = data.load_icons().get(e.get("key"))
    import tuipet.core.shop as shop
    art = shop.icon_art(e.get("key")) if e else None
    if art:                       # a substitute rip outranks the sheet frame
        return icon_cell(art)     # (and works even for a key with no sheet)
    if not fr:
        return [" " * IC_W] * IC_ROWS
    return icon_cell(fr[shop.icon_frame(e.get("key")) % len(fr)])


def icon_info(out: Any, icon: Any, info: Any) -> None:
    """The selected-item block: icon column + info column, first line bold --
    the ONE layout shared by every icon view."""
    tw = W - IC_W - 2
    for r in range(IC_ROWS):
        tx = info[r] if r < len(info) else ""
        out.append(icon[r] + "  ", style=INK)
        out.append(slice_by_width(tx, tw) + "\n", style=INK_B if r == 0 else INK)

def list_window(out: Any, rows: Any, cursor: Any, vis: Any, fmt: Any, empty: Optional[Any]=None) -> Any:
    """The shared scrolling list body: a vis-row window centred on the cursor,
    each row through fmt(item, index), padded with blanks.  Retires seven
    hand-rolled copies (audit 2026-07).  fmt returns a plain label (rendered
    via row() with the ▸ cursor) OR a styled Text owning its whole line incl.
    the newline -- for lists with their own row grammar (datacore EVOLVES).
    Returns the clamped cursor so callers can keep theirs in range."""
    n = len(rows)
    cursor = min(cursor, max(0, n - 1))
    if not n:
        if empty:
            out.append_text(row(empty))
        out.append_text(blanks(vis - (1 if empty else 0)))
        return cursor
    lo = max(0, min(cursor - vis // 2, n - vis))
    shown = 0
    for i in range(lo, min(lo + vis, n)):
        lbl = fmt(rows[i], i)
        out.append_text(lbl if isinstance(lbl, Text) else row(lbl, i == cursor))
        shown += 1
    out.append_text(blanks(vis - shown))
    return cursor


def page_step(cursor: Any, n: Any, vis: Any, k: Any) -> Any:
    """PgUp/PgDn for a CURSOR list: a vis-1 leap, clamped at both ends (never
    wrapped -- a page key is "get me across this list", and wrapping past the
    end reads as a bug).  Returns the new cursor, or None when k isn't a page
    key so the caller's elif chain falls through untouched.

    Help and the README have promised "PgUp/PgDn leap through long lists"
    since 0.5.64, but only the top/window scrollers (help, egg guide, datacore,
    options, lobby) ever implemented it -- the CURSOR lists, including the
    31-row scene picker and the 24-slot cup board, silently ate the key
    (help audit 2026-07-21).  One helper so the claim stays true everywhere."""
    if k not in ("pageup", "pagedown"):
        return None
    if n <= 0:
        return 0
    step = max(1, vis - 1)
    delta = -step if k == "pageup" else step
    return max(0, min(n - 1, cursor + delta))


def scroll_window(out: Any, rows: Any, off: Any, vis: Any, fmt: Any) -> Any:
    """list_window's cursor-less cousin: a vis-row window at a raw scroll
    OFFSET (requirement checklists, logs) -- no selection, no centring.  Same
    fmt contract (plain label or a styled whole-line Text).  Returns the
    clamped offset."""
    off = max(0, min(off, max(0, len(rows) - vis)))
    shown = 0
    for i in range(off, min(off + vis, len(rows))):
        lbl = fmt(rows[i], i)
        out.append_text(lbl if isinstance(lbl, Text) else row(lbl))
        shown += 1
    out.append_text(blanks(vis - shown))
    return off


class SubHost:
    """Mixin for panels that host a child panel in `self.sub` (battle inside
    adventure, town inside adventure, battle inside town/cup).  One home for
    the anim-delegate + sfx-bubble seam that was hand-rolled three ways --
    the flee-boss bug lived in exactly this kind of drift (audit 2026-07)."""

    sub = None

    def sub_anim(self) -> Any:
        """Delegate a frame to the child; bubble its sfx up.  True if handled.
        A child with no anim() (ShopPanel) is simply held -- the host's own
        clock pauses either way (adventure road-keys 2026-07-07)."""
        if self.sub is None:
            return False
        if hasattr(self.sub, "anim"):
            self.sub.anim()
        self.sfx = getattr(self.sub, "sfx", None) or getattr(self, "sfx", None)
        if getattr(self.sub, "sfx", None):
            self.sub.sfx = None
        return True

    def sub_key(self, k: Any, on_done: Any) -> Any:
        """Route a key to the child.  When the child finishes (('done', r)),
        clear it and hand r to on_done.  Returns True if the child had the key."""
        if self.sub is None:
            return False
        r = self.sub.key(k)
        if r is not None and r[0] == "done":
            self.sub = None
            on_done(r[1])
        return True
