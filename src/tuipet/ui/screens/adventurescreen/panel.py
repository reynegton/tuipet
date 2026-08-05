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

from .renderer import AdventureRendererMixin
from .logic import AdventureLogicMixin

from tuipet.ui.components import menu

class AdventurePanel(menu.SubHost, AdventureRendererMixin, AdventureLogicMixin):  # type: ignore
    def __init__(self, pet: Any, zone: Optional[Any]=None) -> None:
            self.pet = pet
            self.adv = Adventure(pet, zone=zone)   # zone chosen by the picker (or the frontier)
            self.frame_i = 0
            self.sfx = None  # type: ignore
            self.sub = None
            self.auto_close = None
            self._landed = False
            self.travelling = False       # the march begins once the teleport lands
            self._travel_t = 0            # auto-march pacing counter
            self._home_msg = None         # type: ignore
            self._fighting_boss = False   # the current sub is the gate boss, not a wild
            self._fighting_enemy = None   # the enemy dict of the active fight (for the bounty)
            self._at_gate = False         # knocked back: standing before the boss
            self._gate_refusal = None      # ...or standing because the body said no
            #                                (the device's battle gate, 2026-07-25)
            self._rest_t = 0              # ticks left resting (transport town-warp beat)
            self._heal_t = 0              # ticks left on the Life Recovery second-wind beat
            self._note = ""               # a transient strip verdict (heal / bare warp)
            self._note_t = 0
            self._town_prompt = False     # standing at a town: visit the hub or walk on
            self._town_sub = False        # the current sub is the TownPanel, not a fight
            self._find = None             # a loot key spotted, awaiting dig/pass
            self._find_present = False     # ...and is it a wrapped festival present?
            self._scene = None            # type: ignore
            self._find_msg = None         # type: ignore
            self._hazard = None           # type: ignore
            self._refuse_t = 0            # ticks left on the refusal head-shake
            self._refused = False         # planted: SPACE re-issues the walk
            self._transport = None        # open transport menu: the held transport keys
            self._transport_cursor = 0
            self._summary = False         # showing the run-results card before homecoming
            self._summary_shown = False   # ...so _go_home only defers to it once
            self._pulse = None            # type: ignore
            self._parade = None           # a running BossParade (map beaten)
            self._wx = float(grid.X0)     # the march x: the pet CROSSES the window
            # leaving home rides the canon teleport (dir "in" == INTO the adventure:
            # leave-phase plays over HOME, arrive-phase materialises on the road)
            self._trans = {"dir": "in", "phase": "leave", "t": 0}

    def anim(self) -> None:
            if self.sub_anim():               # a wild fight owns the clock -- delegate
                return
            self.frame_i += 1
            if self._note_t > 0:              # the transient strip verdict decays
                self._note_t -= 1
            if self._trans is not None:
                # the teleport owns the screen both ways -- canon's state machine
                # holds every input until endAnim()
                tr = self._trans
                tr["t"] += 1  # type: ignore
                snds = TELE_LEAVE_SNDS if tr["phase"] == "leave" else TELE_ARRIVE_SNDS
                snd = snds.get(tr["t"])  # type: ignore
                if snd:
                    self.sfx = snd  # type: ignore
                if tr["phase"] == "leave" and tr["t"] >= TELE_LEAVE_T:  # type: ignore
                    # the sliver left the screen: the world swaps under the cut
                    # (canon teleportArrive frame 0 -- background changes, no anim)
                    tr["phase"], tr["t"] = "arrive", 0
                elif tr["phase"] == "arrive" and tr["t"] >= TELE_ARRIVE_T:  # type: ignore
                    self._trans = None  # type: ignore
                    if tr["dir"] == "out":
                        # home: the flag the body sim gates on (assistant billing,
                        # filth, gift call -- canon _isHome) comes back down.  The
                        # SETTER died with the old adventure and was never rewired
                        # (found 2026-07-21 via Joel's @-line question);
                        # _after_adventure is the one safety net (truthed
                        # 2026-07-25: no app-side death path clears it).
                        self.pet.away = False
                        self.pet.away_where = ""
                        self.auto_close = ("done", self._home_msg)   # type: ignore
                    else:
                        self._landed = True                # on the road -- the march begins
                        self.travelling = True
                        self.pet.away = True               # canon: the teleport toggles it
                        self.pet.away_where = self.adv.name   # the @-line's live zone
                return
            if self._pulse is not None:
                # zoneChange: four zonePulse beats, then home (or the parade)
                p = self._pulse
                if any(p["t"] == on for on, _off in PULSE_ON):
                    self.sfx = "select"           # the zonePulse chirp
                p["t"] += 1
                if p["t"] >= PULSE_T:
                    self._pulse = None
                    if p.get("parade"):
                        self._parade = {"t": 0, "nums": p["parade"],
                                        "msg": p.get("msg")}
                        self.sfx = "win"          # bossParade cue
                    else:
                        self._go_home()           # celebrated -- now the verdict
                return
            if self._parade is not None:
                self._parade["t"] += 1
                if self._parade["t"] >= PARADE_T * len(self._parade["nums"]):
                    self._parade = None
                    self._go_home()
                return
            if (self.pet.dead and self._trans is None and not self._summary
                    and self.sub is None):
                # A ROAD DEATH ENDS THE RUN NOW (audit 2026-07-25: the one
                # source is a lethal town-bag item; the corpse used to keep
                # marching, fighting and winning bits until homecoming, and
                # the memorial only spoke at the door).  Straight to the
                # teleport -- a grave outranks a score card.
                self._summary_shown = True
                self._go_home()
                return
            if self._at_gate and self._heal_t > 0:
                self._heal_t -= 1             # the second wind plays at the gate too
                return
            if self.travelling:
                if self.pet.asleep:           # the roadside nap: the journey waits
                    return                    #   -- no strides, no rolls, no march
                if self._refuse_t > 0:        # the head-shake plays out
                    self._refuse_t -= 1
                    return
                if self._refused:             # planted: SPACE re-issues the walk
                    return
                if self._scene is not None:   # the investigate playbook plays out
                    self._scene_tick()
                    return
                if self._hazard is not None:  # an ambush owns the beat
                    self._hazard_tick()
                    return
                if self._transport is not None:   # transport menu open: wait for input
                    return
                if self._find is not None:    # a glint spotted: wait for dig/pass
                    return
                if self._town_prompt:         # standing at a town: visit or walk on
                    return
                if self._rest_t > 0:          # a transport town-warp rest beat
                    self._rest_t -= 1
                    if self._rest_t == 0 and self.adv._in_town(self.adv.loc):
                        # the warp landed ON town ground -- open the same
                        # visit-or-walk-on door a walked-in arrival gets (Joel
                        # 2026-07-23: "shoukdnt town transports allow us to go
                        # to the shop, etc?").  A warp from PAST the span
                        # rested in place, so there is no town to enter.
                        self._town_prompt = True
                    return
                if self._heal_t > 0:          # the Life Recovery second wind
                    self._heal_t -= 1
                    return
                # THE MARCH (walking sequence restored from the old build,
                # 8ab28a0 -- Joel 2026-07-13: "mon should walk across the
                # screen"): the journey walk actually CROSSES the window -- off
                # the right edge, back in from the left, the lawful exits --
                # instead of stepping in place at an anchor.  A SICK pet
                # trudges at HALF pace (pass 3).
                self._wx += MARCH_PX * (0.5 if self.pet.sick else 1.0)
                if self._wx >= grid.X1:              # fully out the right side
                    # slide back in from JUST off-left of the real sprite (audit
                    # C2: the flat 16px offset over-hid narrow sprites for ticks)
                    self._wx = float(grid.X0 - grid.width(self._rows(0)))
                # auto-march: the pet walks the road on its own pace; arrival ends
                # the run and rides the same teleport back home (SPACE hurries a leg)
                self._travel_t += 1
                if self._travel_t >= TRAVEL_TICKS:
                    self._travel_t = 0
                    self._advance()

    def key(self, k: Any) -> Any:
            if self.sub is not None:              # a fight or the town hub owns input
                self.sub_key(k, self._town_done if self._town_sub else self._battle_done)
                return None
            if (self._trans is not None or self._scene is not None
                    or self._pulse is not None or self._parade is not None):
                # the teleport / investigate / celebration beats own the screen
                # (no skips: own-game law 2026-07-13 -- the beats play out).
                # ONE exception: SPACE locks a LIVE timed-dig meter -- that's
                # the arcade input, not a skip
                s = self._scene
                if (s is not None and s.get("meter") and s["grade"] is None
                        and s["t"] >= INV_WALK_T and k in ("space", "enter")):
                    self._lock_dig()
                return None
            if self._rest_t > 0 or self._heal_t > 0:
                # the rest / second-wind beat plays out -- keys used to fall
                # through to the march and SPACE walked 5 silent legs behind a
                # motionless rested pet (audit 2026-07-25)
                return None
            if self._town_prompt:                 # at a town: visit the hub or walk on
                if k in ("enter",):
                    from tuipet.ui.screens.townscreen import TownPanel
                    self.sub = TownPanel(self.pet, self.adv.town_at(self.adv.loc))
                    self._town_sub = True
                elif k in ("space", "escape"):
                    self._town_prompt = False     # walk on, the march resumes
                return None
            if self._summary:                     # results card up: any key rides home
                self._summary = False
                self._summary_shown = True
                self._go_home()                   # the latch makes this teleport now
                return None
            if self._refuse_t > 0:
                return None                       # the head-shake plays out
            if self._refused and self._transport is None:   # planted on the road
                #                                 (an open warp menu keeps its keys)
                if k == "space":
                    self._refused = False         # re-issue the walk: canTravel
                    self._advance()               # re-rolls on the very next leg
                elif k == "t":
                    held = self.adv.held_transports()
                    if held:                      # a town warp is the way out
                        self._transport, self._transport_cursor = held, 0
                elif k == "escape":
                    self._home_msg = f"{t('msg_adv_turned_zone', 'Turned back from {name}.').replace('{name}', self.adv.name)}{self._bits_tail()}"
                    self._go_home()
                return None
            if self._hazard is not None:          # the ambush: SPACE ducks it
                # a REAL reflex window now (dodge rework 2026-07-23, Joel: "the
                # whole space to dodge thing... its sloppy as fuck").  The old
                # rule banked a duck ANYWHERE in the 1.6s beat -- and SPACE is
                # also the hurry-the-march key, so the mash bled in and won the
                # dodge by accident before the ! even registered.  New grammar,
                # ONE press per ambush: during the telegraph it's TOO SOON (the
                # duck is spent -- the anti-mash rule); during the lunge it's
                # the clean duck.  ! ! ! means WAIT FOR IT.
                h = self._hazard
                if (k in ("space",) and not h["dodged"] and not h["hit"]
                        and not h.get("spent")
                        and h["t"] < HZ_TELE_T + HZ_LUNGE_T):
                    h["spent"] = True
                    if h["t"] >= HZ_TELE_T:       # inside the lunge: the duck
                        h["dodged"] = True
                return None                       # everything else rides the beat
            if self._find is not None:            # a glint spotted: dig or pass
                if k in ("enter",):
                    self._dig()
                elif k in ("space", "escape"):
                    self._find = None             # walk on, leave it
                return None
            if self._transport is not None:       # transport menu: choose / use / cancel
                n = len(self._transport)
                if k in ("up", "k"):
                    self._transport_cursor = (self._transport_cursor - 1) % n
                elif k in ("down", "j"):
                    self._transport_cursor = (self._transport_cursor + 1) % n
                elif k in ("enter", "space"):
                    self._use_transport(self._transport[self._transport_cursor])
                elif k in ("escape",):
                    self._transport = None        # back to the road
                return None
            if self._at_gate:                     # knocked back before the boss
                if k == "space":
                    self._start_boss(self.adv.boss)   # face it again (the gate
                    #                                   asks the body first now)
                elif k == "t":
                    # the same honest out the planted-on-the-road refusal offers
                    # (energy audit 2026-07-23): a town rest is a real answer to
                    # a drained, sick or hurt body.  BOTH gate arms take it now
                    # -- the retry arm (knocked back, lives short) used to leave
                    # a held Life Recovery inert at the exact moment it exists
                    # for (audit 2026-07-25)
                    held = self.adv.held_transports()
                    if held:
                        self._transport, self._transport_cursor = held, 0
                elif k == "escape":
                    self._home_msg = f"{t('msg_adv_turned_boss', 'Turned back from {boss}.').replace('{boss}', self.adv.boss_name)}{self._bits_tail()}"
                    self._go_home()
                return None
            if k in ("t",) and self.travelling:
                held = self.adv.held_transports()  # open the transport menu if any held
                if held:
                    self._transport, self._transport_cursor = held, 0
            elif k in ("space",) and self.travelling:
                self._advance()                   # hurry the next leg
            elif k in ("escape",):
                # turn back: the SAME teleport the other way; anim() auto-closes
                # the mode once it lands (canon teleportArrive/endAnim)
                self._home_msg = f"{t('msg_adv_turned_zone', 'Turned back from {name}.').replace('{name}', self.adv.name)}{self._bits_tail()}"
                self._go_home()
            return None

    def text(self) -> Any:
            if self.sub is not None:
                return self.sub.text()             # the fight owns the screen
            if self._trans is not None:
                return self._teleport_frame()
            if self._pulse is not None:
                return self._pulse_frame()         # the zoneChange light
            if self._parade is not None:
                return self._parade_frame()        # the map's bosses march past
            if self._summary:
                return self._summary_frame()       # the run-results card
            if self._at_gate:
                return self._gate_frame()          # the FACEOFF: squared up at the gate
            if self.travelling:
                if self.pet.asleep:
                    return self._nap_frame()       # the roadside nap
                if self._refuse_t > 0 or self._refused:
                    return self._refuse_frame()    # the head-shake / planted feet
                if self._scene is not None:
                    return self._scene_frame()     # the investigate playbook
                if self._hazard is not None:
                    return self._hazard_frame()    # the ambush beat
                if self._find is not None:
                    return self._glint_frame()     # the attention bounce at the spot
                if self._heal_t > 0:
                    return self._heal_frame()      # the second-wind celebration
                if (self._transport is not None or self._rest_t > 0
                        or self._town_prompt):
                    return self._standing_frame()  # menu / rest / town: stand still
                return self._march_frame()
            return self._standing_frame()

