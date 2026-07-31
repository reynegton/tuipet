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
from rich.cells import cell_len
from rich.text import Text
import tuipet.data.loaders.data as data
import tuipet.utils.grid as grid
import tuipet.ui.components.menu as menu
import tuipet.core.adventure as adventure
import tuipet.core.shop as shop
import tuipet.utils.strikefx as strikefx
from tuipet.core.adventure import Adventure, MAX_LIVES, ZONES
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
def _fit(name, budget):
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
def _brighten(bg, f):
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
def _curtain_pts(x, y, w, h):
    """The evol curtain as overlay pixels: the canon stripe pattern (each 3-px
    band = 1 clear + 2 filled) over an LCD rect.  Rides paint()'s overlay so it
    covers the PET too, like canon's room-effect layer.  Window-law: the ink is
    cut at the window, so the sliver's off-edge travel reads as a lawful exit."""
    return [(px, py) for py in range(y, y + h)
            for px in range(x, x + w)
            if (px - x) % 3
            and grid.X0 <= px < grid.X1 and grid.TOP <= py < grid.FLOOR]

class ZonePickPanel:
    """The embark screen: pick an UNLOCKED zone to run.  Progression phase --
    zones unlock as their gate boss is felled (pet.adv_progress); a conquered
    zone can be replayed, the frontier is the next challenge.  Returns the
    chosen zone dict on ENTER, or None on ESC (back out of Adventure)."""

    VIS = 8

    def __init__(self, pet):
        import tuipet.utils.persistence as persistence
        self.pet = pet
        self.frame_i = 0
        self.indices = adventure.unlocked_indices(pet)   # unlocked zone indices, in order
        self.cursor = len(self.indices) - 1              # default: the frontier (newest)
        self.holiday = adventure.active_holiday()        # festival banner + double rewards
        self.bests = persistence.zone_bests()            # standing run scores per zone

    def anim(self):
        self.frame_i += 1

    def key(self, k):
        n = len(self.indices)
        if k in ("up", "k"):
            self.cursor = (self.cursor - 1) % n
        elif k in ("down", "j"):
            self.cursor = (self.cursor + 1) % n
        elif k in ("pageup", "pagedown"):       # up to 26 zones unlock
            self.cursor = menu.page_step(self.cursor, n, self.VIS, k)
        elif k in ("enter", "space"):
            return ("done", ZONES[self.indices[self.cursor]])   # embark
        elif k in ("escape", "a"):
            return ("done", None)                               # back out
        return None

    def strip(self):
        return menu.hints(("↑↓", "pick"), ("ENTER", "go"), ("ESC", "back"))

    def _fmt(self, zi, _i):
        z = ZONES[zi]
        mark = "✓" if adventure.is_conquered(self.pet, zi) else "★"   # conquered vs the frontier
        best = self.bests.get(zi)
        if best:                               # the standing score: chase it
            # ellipsis, not the silent mid-word cut (audit 2026-07-25:
            # "MasterTyrannomon's Factory Nig" the moment it had a best)
            return _fit(f"{mark} {z['name']}", 27).ljust(27) + f"{best:>6}"
        return _fit(f"{mark} {z['name']}", 34)

    def _bounty_claimed(self, zi):
        """Today's replay bounty already paid for this zone (the ration)."""
        import tuipet.core.shop as shop
        led = getattr(self.pet, "road_bounty", None) or {}
        return led.get("day") == shop._today_ordinal() and led.get(str(zi))

    def text(self):
        right = "★ FESTIVAL" if self.holiday else f"{len(self.indices)}/{len(ZONES)}"
        out = menu.header("ADVENTURE", right)
        self.cursor = menu.list_window(out, self.indices, self.cursor, self.VIS, self._fmt)
        if self.holiday:
            out.append_text(menu.note(f"★ {self.holiday}: 2× bits · more loot!"))
        elif adventure.is_conquered(self.pet, self.indices[self.cursor]):
            # the VETERAN ROAD tease (replay scaling 2026-07-21) -- the
            # festival note owns the slot on the rarer festival days; the
            # rationed bounty says so up front (audit 2026-07-25)
            if self._bounty_claimed(self.indices[self.cursor]):
                # <= 38 so it HOLDS STILL (a marqueeing ration notice reads
                # as decoration)
                out.append_text(menu.note("✓ veteran — bounty claimed today"))
            else:
                out.append_text(menu.note("✓ veteran road: foes fight trained "
                                          "· bounties +50%"))
        else:
            # a steady card: the note row never blinks in and out as the
            # cursor crosses a conquered row (audit 2026-07-25: the footer
            # hopped a row)
            out.append_text(menu.note(""))
        out.append_text(menu.footer("↑↓ pick   ENTER go   ESC back"))
        return out


