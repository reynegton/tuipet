"""Adventure — tuipet's OWN expedition (rebuild FOUNDATION, 2026-07-20).

This is the skeleton the expedition engine grows into: the menu action, the
can_adventure() gate, and the REAL canon teleport (SpriteAnim.teleportLeave /
teleportArrive / teleportAppear) carried VERBATIM from the pre-0.5.8 build --
leaving home and returning both ride the same striped-curtain wipe.

⛔ OWN-GAME LAW (Joel 2026-07-13, carried forward): DVPet is NOT canon for
adventures.  One biome per run, cross a zone in ~40 interactive travel actions,
victory teleport home.

Built so far: the teleport (verbatim); the MARCH -- the pet walks the run's one
backdrop while the journey rides a ribbon (adventure.Adventure), arrival
teleports it home with the verdict, ESC turns back; and WILD ENCOUNTERS -- a
per-leg roll pulls a real roster enemy that fights through BattlePanel (a
SubHost child), a loss costs an adventure life, and 0 lives fails the run home;
the real 26-ZONE GEOGRAPHY (adventure.ZONES from data.load_maps -- each zone its
own biome + wild table); the zone BOSS FIGHT -- the end opens the gate boss,
felling it is the win, a survivable loss stands the pet at the gate to try again
(SPACE) or turn back (ESC); TRAVEL DRAIN -- marching tires the pet (⚡ energy on
the strip), burns weight and tops effort; TOWNS -- a mid-zone rest that refills
lives + energy; and PROGRESSION -- the ZonePickPanel picks an unlocked zone,
felling a boss unlocks the next (pet.adv_progress); and FINDS -- spot loot on
the road, ENTER digs it into the bag; the home STATUS CARD; and TRANSPORT -- press T
mid-march to spend a town/danger warp item (skip ahead, rest or get ambushed).
Nothing here is faked.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from rich.cells import cell_len
from rich.text import Text
import tuipet.data.loaders.data as data
import tuipet.utils.grid as grid
import tuipet.ui.components.menu as menu
import tuipet.core.adventure as adventure
import tuipet.core.shop as shop
import tuipet.utils.strikefx as strikefx
from tuipet.core.adventure import Adventure, MAX_LIVES, ZONES
from tuipet.utils.theme import LCD_ON, LCD_BG, INK, INK_B, DIM, POS, NEG    # noqa: F401  (theme.apply propagation)
from tuipet.i18n.translator import t
COLS, ROWS = 40, 12           # the ONE locked LCD arena, like every other screen
PULSE_T = 54
PULSE_ON = ((5, 10), (15, 20), (25, 30), (35, 54))
STRIP_W = 40                  # the message box's CELL budget (== app.HUD_W;
HINT_BEAT = 20                # the road strip's key hint holds ~2s per step
PARADE_T = 40                 # ticks for one boss to march across (edge to
INV_WALK_T = 12               # walk-left leg
INV_REVEAL_T = 30             # dots done -> the reveal pose fires
INV_HOLD_T = 42               # reveal held (the find shown beside the cheer)
INV_END_T = 54                # walk-back (ReturnItem) complete
DIG_METER_T = 48              # one full 0..24..0 sweep, then the spade falls
HZ_TELE_T = 8                 # the "!" telegraph window
HZ_LUNGE_T = 8                # the pounce crosses the right half
HZ_END_T = 10                 # the verdict beat (the duck-under / the burst)
REFUSE_T = 24                 # the refusal head-shake (the fx convention)
WALK_BEAT = 5                 # idleWalk pose-flip cadence while marching
MARCH_PX = 0.5                # the march: px per 0.1s tick across the window
TRAVEL_TICKS = 8              # auto-march pace: ticks per travel step (~0.8s a leg)
TOWN_HOLD = 14                # ticks the pet rests at a town before marching on
NOTE_HOLD = 30                # ticks a road-item verdict rides the strip
_cells = cell_len             # budgets are CELLS, not chars (bug-#32 law)
def _fit(name: str, budget: Any) -> Any:
    """Ellipsis-trim a name to a cell budget: a strip's REQUIRED keys never
    ride the marquee for a long boss name (audit 2026-07-25)."""
    if _cells(name) <= budget:
        return name
    while name and _cells(name) + 1 > budget:
        name = name[:-1]
    return name + "…"
TELE_LEAVE_T = 50             # flashes 3..22, swallow 23, shrink 26..40 (the
TELE_ARRIVE_T = 46            # sliver zips in from the LEFT 0..5, expand
TELE_ON = ((3, 9), (15, 18), (21, 22))        # leave: curtain flash spans
TELE_APPEAR_ON = ((1, 2), (5, 8), (14, 20))   # arrive: flicker spans (t-23)
TELE_LEAVE_SNDS = {3: "strongHit", 15: "strongHit", 21: "strongHit",
                   26: "attackHit", 44: "attack"}
TELE_ARRIVE_SNDS = {1: "attack", 5: "attackHit",
                    24: "strongHit", 28: "strongHit", 37: "strongHit"}
def _brighten(bg: Any, f: Any) -> Any:
    """Lerp a backdrop toward white -- the LCD's zonePulse flash."""
    out = []
    for r in bg:
        row = []
        for i in range(0, len(r) - 5, 6):
            v = int(r[i:i + 6], 16)
            row.append("%02x%02x%02x" % tuple(
                round(c + (255 - c) * f)
                for c in ((v >> 16) & 255, (v >> 8) & 255, v & 255)))
        out.append("".join(row))
    return out
def _curtain_pts(x: Any, y: Any, w: Any, h: Any) -> Any:
    """The evol curtain as overlay pixels: the canon stripe pattern (each 3-px
    band = 1 clear + 2 filled) over an LCD rect.  Rides paint()'s overlay so it
    covers the PET too, like canon's room-effect layer.  Window-law: the ink is
    cut at the window, so the sliver's off-edge travel reads as a lawful exit."""
    return [(px, py) for py in range(y, y + h)
            for px in range(x, x + w)
            if (px - x) % 3
            and grid.X0 <= px < grid.X1 and grid.TOP <= py < grid.FLOOR]

class AdventureRendererMixin:
    def strip(self) -> Any:
            if self.sub is not None:  # type: ignore
                return self.sub.strip()            # type: ignore
            if self._trans is not None:  # type: ignore
                return ""                          # the teleport plays out wordless
            if self._pulse is not None:  # type: ignore
                line = self._pulse.get("line")     # type: ignore
                return f"[b]★ {line}[/]" if line else ""
            if self._parade is not None:  # type: ignore
                msg = self._parade.get("msg")      # type: ignore
                return f"[b]★ {msg}[/]" if msg else ""
            if self._summary:  # type: ignore
                return menu.hints(("any key", t("msg_adv_any_key", "any key")), ("", t("msg_adv_home", "home")))
            if self._at_gate:                      # type: ignore
                hearts = "♥" * self.adv.lives + "[dim]♡[/]" * (MAX_LIVES - self.adv.lives)  # type: ignore
                if self._heal_t > 0 and self._note:  # type: ignore
                    return f"[b]{self._note}[/] {hearts}"   # type: ignore
                if self._gate_refusal:             # type: ignore
                    # single spacing: the hungriest clause + a held warp ran 41
                    # cells and put the outs on the marquee (audit 2026-07-25)
                    out = t("msg_adv_t_warp", "T warp · ") if self.adv.held_transports() else ""  # type: ignore
                    return f"[b]{self._gate_refusal}[/] [dim]· {out}{t('msg_adv_esc_home', 'ESC home')}[/]"  # type: ignore
                # CELL BUDGET (audit 2026-07-25: ten boss names ran 41-45 cells
                # and scrolled the required keys off the box): the hints + hearts
                # are fixed, the NAME takes what remains, ellipsis-trimmed
                held = "T " if self.adv.held_transports() else ""  # type: ignore
                tail = f" {hearts} [dim]· {t('msg_adv_space_fight', 'SPACE fight')} {held}{t('msg_adv_esc_home', 'ESC home')}[/]"
                plain = (f" {'♥' * self.adv.lives}{'♡' * (MAX_LIVES - self.adv.lives)}"  # type: ignore
                        f" · {t('msg_adv_space_fight', 'SPACE fight')} {held}{t('msg_adv_esc_home', 'ESC home')}")  # type: ignore  # type: ignore
                return f"{_fit(self.adv.boss_name, 40 - _cells(plain))}{tail}"  # type: ignore
            if self.travelling:  # type: ignore
                lost = MAX_LIVES - self.adv.lives  # type: ignore
                hearts = "♥" * self.adv.lives + "[dim]♡[/]" * lost  # type: ignore
                if self._transport is not None:  # type: ignore
                    import tuipet.core.shop as shop
                    key = self._transport[self._transport_cursor]  # type: ignore
                    name = (shop.entry(key) or {}).get("name", "Transporte")
                    nav = " ↑↓" if len(self._transport) > 1 else ""  # type: ignore
                    return f"[b]{t('msg_adv_transport', '⟿ {name}').replace('{name}', name)}[/]  [dim]{t('msg_adv_transport_hint', 'ENTER use{nav} · ESC').replace('{nav}', nav)}[/]"
                if self._town_prompt:  # type: ignore
                    return t("msg_adv_town", "[b]⌂ A town[/]") + "  [dim]" + t("msg_adv_town_hint", "ENTER visit · SPACE walk on") + "[/]"
                if self.pet.asleep:  # type: ignore
                    # unreachable today (the door disturbs sleepers, the pill
                    # refuses on the road) -- but a waiting state must name its
                    # key if it ever becomes reachable (SHOW-FLOW, audit 2026-07-25)
                    return f"[dim]{t('msg_adv_nap', 'zzZ — a roadside nap · ESC home')}[/]"
                if self._refuse_t > 0 or self._refused:  # type: ignore
                    # the refusal only ever fires PAST EMPTY (stop_travel_prob:
                    # negative energy only) -- say so, or the bare "SPACE urge"
                    # invites a dead mash (QOL sweep 2026-07-23).  HONEST outs
                    # only (energy audit 2026-07-23): energy cannot rise on the
                    # road itself -- a town's rest or home are the ways out.
                    out = (t("msg_adv_t_warp", "T warp · ") if self.adv.held_transports() else "")  # type: ignore
                    return f"[b]{t('msg_adv_refuses', 'Refuses — spent!')}[/]  [dim]{out}{t('msg_adv_esc_home', 'ESC home')}[/]"
                if self._scene is not None:  # type: ignore
                    s, t_val = self._scene, self._scene["t"]  # type: ignore
                    if s["grade"] is None and t_val >= INV_WALK_T:
                        return menu.hints(("SPACE", t("msg_adv_space_dig", "dig!")))   # the meter is live
                    if t_val >= INV_REVEAL_T:         # the reveal, unsealed
                        return f"[b]✦ {self._find_msg}[/]"  # type: ignore
                    if t_val >= INV_WALK_T:           # suspense: . .. ...
                        dots = "." * min(3, 1 + (t_val - INV_WALK_T) // 6)
                        return f"[dim]{dots}[/]"
                    return ""                     # the walk-out plays wordless
                if self._hazard is not None:  # type: ignore
                    h = self._hazard  # type: ignore
                    if h["t"] < HZ_TELE_T:        # the warning: DON'T press yet
                        if h.get("spent"):
                            return "[b]Jumped too soon![/]"
                        return "[b]! ! ![/]  [dim]wait for it…[/]"
                    if h["t"] < HZ_TELE_T + HZ_LUNGE_T:
                        if h["dodged"]:
                            return "[b]![/]  [dim]ducking...[/]"
                        if h.get("spent"):
                            return "[b]Jumped too soon![/]"
                        return "[b]NOW![/]  [dim]SPACE — duck![/]"
                    if h["dodged"]:
                        return "[b]Dodged the ambush![/]"
                    return f"[b]Ambushed![/]  ⚡-{adventure.HAZARD_ENERGY}"
                if self._find is not None:  # type: ignore
                    # <= 40 plain (budget sweep 2026-07-21: the long line ran 45)
                    return "[b]✦ A glint![/]  [dim]ENTER dig · SPACE pass[/]"
                if self._rest_t > 0:  # type: ignore
                    return f"[b]⌂ Town — rested up[/]  ⚡{self.pet.energy} {hearts}"  # type: ignore
                if self._heal_t > 0 or self._note_t > 0:  # type: ignore
                    # the road-item / balk verdict (A3/A12; the ⚡ moved into the
                    # transport notes -- a balk's verdict is not an energy event)
                    return f"[b]{self._note}[/] {hearts}" if self._note else ""  # type: ignore
                # the key hint CYCLES (Joel 2026-07-24 "anchor + rotate labels,
                # ~2s"): the bare key SET is the anchor, and between each one
                # labelled key rotates in -- so the full labels reach the player
                # without ever needing "SPACE walk · T warp · ESC home" on the
                # one packed 40-col line.  T (warp) only joins when a transport
                # is held.
                # EVERY beat is LABELLED (bug report 2026-07-28, "still seeing
                # space esc": the old anchor-and-rotate showed the bare keyset
                # "SPACE ESC" half the time -- an unlabelled key pair IS the
                # "space t" mystery this strip was rebuilt to end.  One key,
                # named, per beat; the set still cycles so every out reaches
                # the player, and the shorter line gives the ribbon more road).
                held = self.adv.held_transports()  # type: ignore
                steps = ([("SPACE", "walk")]
                         + ([("T", "warp")] if held else [])
                         + [("ESC", "home")])
                k, lbl = steps[(self.frame_i // HINT_BEAT) % len(steps)]  # type: ignore
                hint = f"[dim]· [/][b]{k}[/][dim] {lbl}[/]"
                chain = f" [b]×{self.adv.streak}[/]" if self.adv.streak >= 2 else ""  # type: ignore
                # the packed line must fit the box in CELLS or the anchor beat is
                # mutilated (bug report #32, v0.5.264 "what is space t?": '⚡' is
                # two cells wide, so the char budget passed while the render ran
                # 41 cells and 'ESC' wrapped onto the box's invisible second row).
                # The ribbon absorbs the squeeze -- energy/hearts/chain are LIVE
                # data and the hint is the whole point; a dot of road is not.
                tail = f" ⚡{self.pet.energy} {hearts}{chain}  {hint}"  # type: ignore
                w = max(6, min(14, STRIP_W - cell_len(Text.from_markup(tail).plain)))
                return f"[dim]{self.adv.ribbon(w)}[/]" + tail  # type: ignore
            return menu.hints(("ESC", "home"))

    def _rows(self, idx: int) -> Any:
            fr = data.frames_for(self.pet.num, getattr(self.pet, "egg_type", 0))  # type: ignore
            return grid.prep((fr[idx] if idx < len(fr) else None) or fr[0], ph=ROWS * 2)

    def _road_bg(self) -> Any:
            return self.pet.background(self.adv.scene)   # type: ignore

    def _jx(self, rows: Any, clamp: bool=True) -> Any:
            """Where the mon stands RIGHT NOW: the march position (it walks
            clear across the window while travelling -- old build 8ab28a0).
            Beats, reveals and stand-stills play at this spot; `clamp` pulls it
            fully inside the walkable band so a beat never plays half-off an
            edge.  Journey progress lives on the ribbon."""
            x = int(self._wx)  # type: ignore
            if clamp:
                lo, hi = grid.roam_bounds(grid.width(rows))
                x = min(max(x, lo), hi)
                if x != int(self._wx):  # type: ignore
                    # a beat that clamps also RE-ANCHORS the march (anim audit
                    # A6): the beat still never plays half-off an edge, and the
                    # resume now walks on from where the beat played -- one
                    # snap instead of a snap-there-and-back
                    self._wx = float(x)
            return x

    def _condition_rows(self, wi: Any) -> Any:
            """The pet's road sprite, CONDITION-aware (pass 3 restored): a SICK
            pet drags the idleUnwell collapse/weary trudge with its canon 1px
            shuffle; a GERIATRIC one walks the +9 aged frames (home stepFrame
            idiom); everyone else walks the frame given.  Returns (rows, dx)."""
            import tuipet.utils.anim as anim
            if self.pet.sick and self.pet.num != -1:  # type: ignore
                si, dx = anim.sick_frame(self.frame_i)  # type: ignore
                return self._rows(si), dx
            if self.pet.is_geriatric and self.pet.num != -1:  # type: ignore
                wi += 9                            # the aged shuffle
            return self._rows(wi), 0

    def _march_frame(self) -> Any:
            """The pet walking the road: the idleWalk pose-flip, FACING the way
            it's going, at the RAW march x -- partial edge exits ARE the journey
            (window law: exits are left/right, so the crossing clips at the
            play window, not the LCD border)."""
            wi = data.ROLES["walk"][(self.frame_i // WALK_BEAT) % 2]  # type: ignore
            rows, dx = self._condition_rows(wi)
            return menu.paint([(rows, self._jx(rows, clamp=False) + dx, True)],
                              self._road_bg(), rows=ROWS, cols=COLS,
                              clip=grid.WINDOW)

    def _standing_frame(self) -> Any:
            """The pet standing on the road: beats (glint, town, rest, gate)
            play WHERE IT STANDS -- the clamped march x -- not snapped back to
            centre (old build: "beats play wherever it stands")."""
            rows, dx = self._condition_rows(0)     # canon drawNumMirror(0, false)
            lo, hi = grid.roam_bounds(grid.width(rows))
            # re-clamp AFTER the sick shuffle's dx (audit A11: +1 at the right
            # bound poked the sprite a pixel past the window)
            x = min(max(self._jx(rows) + dx, lo), hi)
            return menu.paint([(rows, x, True)],
                              self._road_bg(), rows=ROWS, cols=COLS,
                              clip=grid.WINDOW)

    def _heal_frame(self) -> Any:
            """The Life Recovery beat (anim audit A3): the happy pose-flip where
            the pet stands -- the glint celebration frames -- while the hearts
            refill on the strip."""
            rows = self._rows((5, 7)[(self.frame_i // 5) % 2])  # type: ignore
            return menu.paint([(rows, self._jx(rows), True)], self._road_bg(),
                              rows=ROWS, cols=COLS, clip=grid.WINDOW)

    def _nap_frame(self) -> Any:
            """The roadside nap (pass 3): the sleep pose-flip where the pet lay
            down, the Zzz hanging at the band's top-right exactly like the home
            sleep scene (arenafx idiom: nothing above the band)."""
            import tuipet.utils.strikefx as strikefx
            rows = self._rows(data.ROLES["sleep"][(self.frame_i // 10) % 2])  # type: ignore
            px = self._jx(rows)
            overlay = []
            zz = data.load_effects().get("zzz")
            if zz:
                z = grid._crop(zz[(self.frame_i // 10) % len(zz)])  # type: ignore
                if z:
                    zw = len(z[0])
                    zx = grid.X1 - zw
                    if zx < px + grid.width(rows) + 1:
                        # a right-side sleeper sat UNDER the Zzz -- first-ink-
                        # wins merged them into one silhouette (anim audit A7);
                        # hang it on the free side instead (the glint rule)
                        zx = grid.X0
                    overlay = strikefx.blit(z, zx, grid.TOP)
            return menu.paint([(rows, px, True)], self._road_bg(),
                              rows=ROWS, cols=COLS, overlay=overlay,
                              clip=grid.WINDOW)

    def _refuse_frame(self) -> Any:
            """The travel refusal: the canon head-shake (refuse pose under the
            mirror toggle) while the shake runs, then the WEARY stand -- the
            planted pet is refusing because it's spent past empty."""
            if self._refuse_t > 0:  # type: ignore
                rows = self._rows(data.ROLES["refuse"][0])
                shake = ((REFUSE_T - self._refuse_t) // 6) % 2 == 0  # type: ignore
                return menu.paint([(rows, self._jx(rows), shake)], self._road_bg(),
                                  rows=ROWS, cols=COLS, clip=grid.WINDOW)
            rows = self._rows(data.ROLES["tired"][0])
            return menu.paint([(rows, self._jx(rows), True)], self._road_bg(),
                              rows=ROWS, cols=COLS, clip=grid.WINDOW)

    def _glint_frame(self) -> Any:
            """A glint spotted: the DiscoverCall attention bounce (happy 5<->7)
            with the atlas "!" riding the up-beats, side-flipped to the free
            side so it never clamps INTO the sprite -- restored from the old
            build (audit passes 1+2)."""
            import tuipet.utils.strikefx as strikefx
            rows = self._rows(data.ROLES["happy"][(self.frame_i // 6) % 2])  # type: ignore
            x = self._jx(rows)
            overlay = []
            att = data.load_effects().get("attention")
            if att:
                ef = att[(self.frame_i // 6) % len(att)]  # type: ignore
                ew = max((len(r) for r in ef), default=0)
                ex = x + grid.width(rows) + 1
                if ex + ew > grid.X1:                 # no room on the right
                    ex = max(grid.X0, x - ew - 1)
                overlay = strikefx.blit(ef, ex, grid.TOP)
            return menu.paint([(rows, x, True)], self._road_bg(), rows=ROWS,
                              cols=COLS, overlay=overlay, clip=grid.WINDOW)

    def _held_icon(self, icon: Any, x: Any, rows: Any, gap: Any) -> Any:
            """The find beside the mon, vertically centred in the band: in
            FRONT when the right has room, flipped BEHIND when it doesn't (the
            glint's side-flip rule).  The old right-wall pin (min(.., X1-iw))
            dropped the icon ONTO a pet returning from a right-side dig -- the
            exact clamped-onto-the-sprite bug its docstring claimed the pin
            prevented (anim audit A2, 2026-07-22)."""
            if not icon:
                return []
            import tuipet.utils.strikefx as strikefx
            iw = max(len(r) for r in icon)
            oy = grid.TOP + max(0, (grid.BAND - len(icon)) // 2)
            ox = x + grid.width(rows) + gap
            if ox + iw > grid.X1:                  # no room in front: carry behind
                ox = max(grid.X0, x - iw - gap)
            return strikefx.blit(icon, ox, oy)

    def _scene_frame(self) -> Any:
            """One frame of the investigateLeft playbook (the restored discover
            sequence): walk OUT to the left goal (native facing), the suspense
            dig under the pulsing "!", the cheer reveal with the find held up
            beside, then ReturnItem -- the carry back to the journey spot, the
            find riding IN FRONT of the walking mon."""
            import tuipet.utils.strikefx as strikefx
            s, bg = self._scene, self._road_bg()  # type: ignore
            t = s["t"]
            if t < INV_WALK_T:                        # walk out to the LEFT goal
                rows = self._rows((t // 3) % 2)
                x0 = self._jx(rows)
                x = round(x0 + (grid.X0 - x0) * (t / INV_WALK_T))
                return menu.paint([(rows, x, False)], bg, rows=ROWS, cols=COLS,
                                  clip=grid.WINDOW)   # faces left (native)
            if s["grade"] is None:                    # the TIMED DIG: the canon bar
                m = s["meter"]                        # owns the window, like the
                return menu.paint([], bg, rows=ROWS,  # drill and the battle bell
                                  cols=COLS, clip=grid.WINDOW,
                                  overlay=strikefx.timing_bar(m["bar"], m["lo"],
                                                              m["hi"]))
            if t < INV_REVEAL_T:                      # the suspense dig
                rows = self._rows(0)
                overlay = []
                att = data.load_effects().get("attention")
                if att and (t // 4) % 2:              # the "!" pulses, blink 4/4
                    ef = att[(t // 8) % len(att)]
                    overlay = strikefx.blit(ef, grid.X0 + grid.width(rows) + 1,
                                            grid.TOP)
                return menu.paint([(rows, grid.X0, False)], bg, rows=ROWS,
                                  cols=COLS, overlay=overlay, clip=grid.WINDOW)
            if t < INV_HOLD_T:                        # the reveal: cheer, find shown
                rows = self._rows(5)
                overlay = self._held_icon(s["icon"], grid.X0, rows, gap=2)
                return menu.paint([(rows, grid.X0, False)], bg, rows=ROWS,
                                  cols=COLS, overlay=overlay, clip=grid.WINDOW)
            rows = self._rows((t // 3) % 2)           # ReturnItem: the carry back
            x0 = self._jx(rows)
            p = min(1.0, (t - INV_HOLD_T) / (INV_END_T - INV_HOLD_T))
            x = round(grid.X0 + (x0 - grid.X0) * p)
            overlay = self._held_icon(s["icon"], x, rows, gap=1)
            return menu.paint([(rows, x, True)], bg, rows=ROWS, cols=COLS,
                              overlay=overlay, clip=grid.WINDOW)

    def _hazard_frame(self) -> Any:
            """The ambush, frame by frame: the "!" blinking at the road's right
            edge, one of the zone's own wilds pouncing in (attack pose, riding
            the overlay like fx do), then the duck-under -- the pouncer sails
            past and exits LEFT, never sharing the pet's cell (the gap IS the
            leap-over) -- or the eaten hit: the atlas burst over the hurt pose.
            All real art; window-law edges throughout."""
            import tuipet.utils.strikefx as strikefx
            h, t = self._hazard, self._hazard["t"]  # type: ignore
            impact = HZ_TELE_T + HZ_LUNGE_T
            if h["hit"]:
                prows = self._rows(9)                 # eaten: the hurt pose
            elif h["dodged"] and t >= HZ_TELE_T:
                prows = self._rows(4)                 # the duck (canon shield pose)
            else:
                prows = self._rows(1)                 # alert on the road
            # the pet SCRAMBLES to the left wall during the telegraph (anim
            # audit A1, 2026-07-22): the pounce lands at the pet's right edge,
            # and two 16px sprites only fit the 32px window with the pet at X0
            # -- anchored at the march x, the ambusher rendered half-cut on
            # most legs and fully OFF-window with the pet right of centre (the
            # pet reacted to nothing).  The scramble is animated, so it reads
            # as the startle, not a snap; the gate faceoff pins the same wall.
            x0 = h.setdefault("x0", self._jx(prows))
            if t < HZ_TELE_T:
                p = t / max(1, HZ_TELE_T - 1)
                px = round(x0 + (grid.X0 - x0) * min(1.0, p))
            else:
                px = grid.X0
            pw = grid.width(prows)
            overlay = []
            if t < HZ_TELE_T:                         # the telegraph
                att = data.load_effects().get("attention")
                if att and att[0] and (t // 2) % 2:   # urgent blink 2/2
                    ew = max((len(r) for r in att[0]), default=0)
                    ex = grid.X1 - ew - 1
                    if ex < px + pw + 1:              # scrambler still under it:
                        ex = max(grid.X0, px - ew - 1)   # flip (the glint rule,
                        #                                  audit A8 -- it drew
                        #                                  over the pet's head)
                    overlay = strikefx.blit(att[0], ex, grid.TOP)
            else:
                e = h["enemy"]
                fr = data.frames_for(e["num"])
                pose = data.ROLES["attack"][0]
                # prepped like every other arena actor (audit A9: the raw frame
                # floated above the y21 floor on bottom-padded rips and measured
                # its PADDED box in the overlap guards)
                bm = grid.prep((fr[pose] if pose < len(fr) else None) or fr[0],
                               ph=ROWS * 2)
                oy = grid.FLOOR - len(bm) if bm else grid.TOP
                if t < impact:                        # charging in from the right
                    p = (t - HZ_TELE_T) / max(1, HZ_LUNGE_T - 1)
                    x = round(grid.X1 - (grid.X1 - (px + pw)) * min(1.0, p))
                    if bm and x >= px + pw:           # never share the pet's cell
                        overlay = strikefx.blit(bm, x, oy)
                elif h["dodged"]:                     # the WHIFF (dodge fix
                    # 2026-07-22, Joel: "the space to dodge mechanic was
                    # glitchy"): the old sail-past hid the pouncer whenever its
                    # box touched the pet's columns -- and with the pet at the
                    # wall (audit A1) that was the ENTIRE tail, so a clean duck
                    # played as the attacker blinking out of existence.  Two
                    # 16px sprites cannot cross a 32px window without one
                    # hiding, so the duck now makes the strike WHIFF: the
                    # pouncer pulls up short of the crouch and retreats out the
                    # RIGHT edge -- the free side of the pet, visible for the
                    # whole beat, never a hidden frame.
                    p = (t - impact) / max(1, HZ_END_T - 1)
                    x = round((px + pw) + (grid.X1 - (px + pw)) * p)
                    if bm and x >= px + pw:           # never share the pet's cell
                        overlay = strikefx.blit(bm, x, oy)
                else:                                 # eaten: the burst covers the beat
                    hitfx = data.load_effects().get("hit")
                    if hitfx and hitfx[0] and (t - impact) < 6:
                        hw = max(len(r) for r in hitfx[0])
                        overlay = strikefx.blit(hitfx[0], min(px + pw, grid.X1 - hw),
                                                grid.TOP + 2)
            return menu.paint([(prows, px, True)], self._road_bg(), rows=ROWS,
                              cols=COLS, overlay=overlay, clip=grid.WINDOW)

    def _pulse_frame(self) -> Any:
            """The zoneChange pulse: the conqueror stands its ground while the
            world flashes bright on the canon beat spans (restored old build)."""
            rows = self._rows(0)
            bg = self._road_bg()
            if bg and any(on <= self._pulse["t"] < off for on, off in PULSE_ON):  # type: ignore
                bg = _brighten(bg, 0.6)            # the zonePulse light, on the LCD
            return menu.paint([(rows, self._jx(rows), True)], bg, rows=ROWS,
                              cols=COLS, clip=grid.WINDOW)

    def _parade_frame(self) -> Any:
            """BossParade: the map's bosses march across, one at a time (canon
            moveLeft; the one-mon LCD rule serialises canon's three-abreast) --
            over a BRIGHTENED stage, so dark marcher ink pops (old audit pass 2:
            a dim stage read worse)."""
            p = self._parade  # type: ignore
            i = min(p["t"] // PARADE_T, len(p["nums"]) - 1)
            t = p["t"] % PARADE_T
            fr = data.frames_for(p["nums"][i])
            wi = data.ROLES["walk"][(t // 3) % 2]
            rows = grid.prep((fr[wi] if wi < len(fr) else None) or fr[0],
                             ph=ROWS * 2)
            # each boss ENTERS off the right edge and EXITS off the left (anim
            # audit A10, 2026-07-22): the old roam-bounds interpolation popped
            # them in at x=20 and vanished them at x=4 mid-window -- the march's
            # own edge-crossing grammar, with the window clip doing the doors
            w = grid.width(rows)
            x = round(grid.X1 + ((grid.X0 - w) - grid.X1)
                      * (t / max(1, PARADE_T - 1)))
            bg = self._road_bg()
            if bg:
                bg = _brighten(bg, 0.45)
            return menu.paint([(rows, x, False)], bg, rows=ROWS, cols=COLS,
                              clip=grid.WINDOW)

    def _gate_frame(self) -> Any:
            """The GATE FACEOFF (restored from the old build, audit pass 1: a
            knocked-back gate showed the mon alone on empty road): squared up
            at the left, stepping in place, while the boss LOOMS half-emerged
            past the gate's right edge -- flush placement would read as one
            blob (two 16px sprites cannot share the 32px window with a gap)."""
            rows = self._rows((self.frame_i // 8) % 2)  # type: ignore
            placements = [(rows, grid.X0, True)]
            boss = self.adv.boss  # type: ignore
            bfr = data.frames_for(boss["num"]) if boss else []
            bf = next((f for f in bfr if f), None)
            if bf:
                brows = grid.prep(bf, ph=ROWS * 2)
                placements.append((brows, grid.X1 - grid.width(brows) * 3 // 4,
                                   False))
            return menu.paint(placements, self._road_bg(), rows=ROWS, cols=COLS,
                              clip=grid.WINDOW)

    def _teleport_frame(self) -> Any:
            """One frame of the canon teleport, on the side of the wipe the beat
            script says the world is showing (verbatim port)."""
            tr = self._trans  # type: ignore
            t, ph = tr["t"], tr["phase"]
            # which world is under the curtain: leaving-out and arriving-in show the
            # ROAD; leaving-in and arriving-out show HOME
            home_side = (tr["dir"] == "in") == (ph == "leave")
            bgimg = self.pet.background() if home_side else self._road_bg()  # type: ignore
            wx0, wy0, ww, wh = grid.X0, grid.TOP, grid.W, grid.BAND
            cx, cy = wx0 + (ww - 4) // 2, wy0 + (wh - 6) // 2
            pet_on, cur = False, None
            if ph == "leave":
                pet_on = t < 23                       # swallowed at t23
                if any(on <= t < off for on, off in TELE_ON) or t >= 23:
                    cur = (wx0, wy0, ww, wh)          # the full-window curtain
                if 26 <= t < 44:                      # shrinking to the sliver
                    k = t - 26
                    w, h = max(4, ww - 2 * k), max(6, wh - k)
                    cur = (wx0 + (ww - w) // 2, wy0 + (wh - h) // 2, w, h)
                elif t >= 44:                         # the sliver departs RIGHT
                    cur = (cx + 4 * (t - 44), cy, 4, 6)
            else:                                     # arrive
                if t <= 5:                            # the sliver zips in from the LEFT
                    cur = (wx0 - 4 + round((cx - wx0 + 4) * t / 5), cy, 4, 6)
                elif t < 23:                          # expands back to the full window
                    k = t - 5
                    w, h = min(ww, 4 + 2 * k), min(wh, 6 + k)
                    cur = (wx0 + (ww - w) // 2, wy0 + (wh - h) // 2, w, h)
                else:                                 # teleportAppear flicker
                    f = t - 23
                    pet_on = f >= 14                  # revealed on the third flash
                    # f==0 rides the expand's full curtain (audit C3: it used to
                    # render one frame of bare road between expand and flicker)
                    if f == 0 or any(on <= f < off for on, off in TELE_APPEAR_ON):
                        cur = (wx0, wy0, ww, wh)
            placements = []
            if pet_on:
                rows = self._rows(0)
                lo, hi = grid.roam_bounds(grid.width(rows))
                if home_side:
                    x, mirror = (lo + hi) // 2, False   # the home scene's centre
                else:
                    # ROAD side: the pet stands AT ITS MARCH SPOT facing the way
                    # it walks (anim audit A4+A5, 2026-07-22): the centred reveal
                    # popped ~8px left + flipped facing into the first march
                    # frame at every run start, and an ESC turn-back snapped a
                    # right-side marcher to centre before the curtain dropped
                    x, mirror = self._jx(rows), True
                placements = [(rows, x, mirror)]
            overlay = _curtain_pts(*cur) if cur else []
            # every arena frame clips to the window (audit C1: this was the one
            # unclipped paint -- safe only because the curtain self-clips)
            return menu.paint(placements, bgimg, rows=ROWS, cols=COLS,
                              overlay=overlay, clip=grid.WINDOW)

    def _summary_frame(self) -> Any:
            """The run-results card, shown on the LCD before the homecoming teleport."""
            a = self.adv  # type: ignore
            out = menu.header("ADVENTURE", "results")
            out.append(a.name[:26] + "\n", style=INK_B)
            word = self._outcome_word()  # type: ignore
            out.append(word + "\n", style={"Conquistado!": POS, "Derrotado": NEG}.get(word, DIM))
            out.append(f"Bits    +{a.bits_earned}\n", style=INK)
            out.append(f"Fights  {a.wins}W/{a.fights}\n", style=INK)
            out.append(f"Loot    {a.finds}\n", style=INK)
            hearts = "♥" * a.lives + "♡" * (MAX_LIVES - a.lives)
            out.append(f"Lives   {hearts}\n", style=INK)
            if a.best_streak >= 2:                 # a chain worth bragging about
                out.append(f"Streak  ×{a.best_streak} best\n", style=INK)
            out.append(f"Score   {a.score()}", style=INK_B)
            if getattr(self, "_new_best", False):
                out.append("  ★ new best!", style=POS)
            out.append("\n")
            if a.holiday:
                out.append(f"★ {a.holiday}\n", style=POS)
            # the card is 12 physical rows: pad only while both extras are absent
            if (1 if a.best_streak >= 2 else 0) + (1 if a.holiday else 0) < 2:
                out.append_text(menu.blanks(1))
            out.append_text(menu.footer("press any key — home"))
            return out

