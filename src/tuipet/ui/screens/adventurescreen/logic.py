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

class AdventureLogicMixin:
    def _advance(self):
            """One leg of the march.  A wild encounter opens a battle; the zone's
            end opens the BOSS gate; a bossless crossing rides the teleport home."""
            r = self.adv.travel()
            if isinstance(r, tuple) and r[0] == "encounter":
                self._start_battle(r[1])
            elif isinstance(r, tuple) and r[0] == "boss":
                self._start_boss(r[1])
            elif isinstance(r, tuple) and r[0] == "find":
                self._find = r[1]                 # a glint: wait for the player to choose
                self._find_present = len(r) > 2 and r[2]   # a festival present?
            elif isinstance(r, tuple) and r[0] == "hazard":
                self._hazard = {"t": 0, "enemy": r[1], "dodged": False, "hit": False}
                self.sfx = "cancel"               # the rustle: the warning thunk
            elif isinstance(r, tuple) and r[0] == "refused":
                self._refuse_t = REFUSE_T         # the head-shake, then the stand
                self._refused = True
                self.sfx = "refuse"
            elif r == "town":
                self._town_prompt = True          # rested on arrival; now visit or walk on
            elif self.adv.boss_felled and not self._summary_shown:
                self._home_msg = f"{t('msg_adv_conquered', '{name} conquered!').replace('{name}', self.adv.name)}{self._bits_tail()}"
                self._summary_shown = True
            elif r == "arrived":
                self._home_msg = f"{self.adv.name} conquered!{self._bits_tail()}"
                self._go_home()

    def _use_transport(self, key):
            """Spend the chosen road item: a town warp rests (and opens the
            town's doors once the beat ends -- see anim), a danger warp
            ambushes, a life recovery refills the hearts in place."""
            r = self.adv.use_transport(key)
            self._transport = None
            if r == "town-warp":
                self._rest_t = TOWN_HOLD          # the warp-in rest beat
                self._refused = False             # rested = willing to walk again
            elif isinstance(r, tuple) and r[0] == "encounter":
                self._start_battle(r[1])          # the danger-warp ambush
            elif r == "life-recovery":
                # the second wind is VISIBLE now (anim audit A3, 2026-07-22):
                # the v0.5.164 heal was nothing but the heart glyphs ticking --
                # a happy beat + the verdict on the strip, the rest-beat grammar
                self._heal_t = TOWN_HOLD
                self._note, self._note_t = "⚡ " + self.adv.last, NOTE_HOLD
                self.sfx = "confirm"
            elif r == "danger-warp":
                # empty wild pool: the dash still happened -- say so instead of
                # silently eating the ticket (anim audit A12)
                self._note, self._note_t = "⚡ " + self.adv.last, NOTE_HOLD
            elif r == "skip-lift":
                # the safe Birdramon lift (expansion 2026-07-26): the road
                # slides by -- the verdict on the strip, the march resumes
                self._note, self._note_t = "⚡ " + self.adv.last, NOTE_HOLD
                self._refused = False             # lifted = willing to walk on
                self.sfx = "confirm"
            elif r == "camp-rest":
                # the Whamon camp: the heal beat, like the life recovery
                self._heal_t = TOWN_HOLD
                self._note, self._note_t = "⚡ " + self.adv.last, NOTE_HOLD
                self._refused = False             # rested = willing to walk on
                self.sfx = "confirm"

    def _dig(self):
            """ENTER on a glint: the OUTCOME lands now -- the bag gets the loot,
            the tally counts it -- then the investigateLeft playbook plays (the
            discover sequence, restored from the old build): walk out LEFT,
            suspense dig, the reveal, the carry back.  The beats are pure
            presentation, like a battle timeline; the verdict and the reward
            chime stay sealed until the reveal beat."""
            import tuipet.core.shop as shop
            from tuipet.ui.screens.battlescreen import mega_window
            key, self._find = self._find, None
            present, self._find_present = self._find_present, False
            self.pet.add_item(key)                # a CATALOG key: real, usable loot
            if key == "memory":               # a WILD chip carries a random
                self.pet.stash_wild_memory()      # trace (2026-07-24) -- one per item
            self.adv.finds += 1
            name = (shop.entry(key) or {}).get("name", "loot")
            # a festival present is dug up WRAPPED (the present box) and the
            # contents revealed like a home gift; a plain find shows its own icon
            if present:
                from tuipet.utils.arenafx import _PRESENT
                name = (shop.entry(key) or {}).get("name", "something")
                self._find_msg = t("msg_adv_present", "A present! It's {name}!").replace("{name}", name)
                icon = _PRESENT
            else:
                self._find_msg = t("msg_adv_dug", "Dug up {name}!").replace("{name}", name)
                icon = self._find_icon(key)
            lo, hi = mega_window(self.pet)        # the SHARED care-widened window
            self._scene = {"t": 0, "icon": icon, "key": key,
                           "name": name, "grade": None,
                           "meter": {"bar": 0, "dir": 1, "left": DIG_METER_T,
                                     "lo": lo, "hi": hi, "hist": []}}

    def _find_icon(self, key):
            """The find at HAND size, ~8px beside the 16px mon (old-build rule:
            scale by ceil(dim/8) so every icon reads held -- never crushed to a
            speck, never drawn as big as the pet)."""
            import tuipet.core.shop as shop
            from tuipet.utils.render import downsample
            art = shop.icon_art(key)
            raw = [f for f in (data.load_icons().get(shop.ICON_KEYS.get(key)) or [])
                   if f]
            icon = art or (raw[shop.icon_frame(key) % len(raw)] if raw else None)
            if icon:
                dim = max(len(icon), max(len(r) for r in icon))
                if dim > 8:
                    icon = downsample(icon, -(-dim // 8))
            return icon

    def _scene_tick(self):
            """Advance the playbook.  At the dig spot the TIMED-DIG meter holds
            the clock (the bar sweeps, the countdown burns, timeout locks the
            spade wherever the marker stands); after the lock, the dots and the
            reveal (reward chime) play on; the walk-back's end puts the mon
            back on the road."""
            from tuipet.ui.screens.battlescreen import BAR_MAX
            s = self._scene
            if s["t"] >= INV_WALK_T and s["grade"] is None:
                m = s["meter"]                    # the meter owns the beat
                m["hist"] = (m["hist"] + [m["bar"]])[-strikefx.LOCK_GRACE:]
                m["bar"] += m["dir"]
                if m["bar"] >= BAR_MAX or m["bar"] <= 0:
                    m["dir"] = -m["dir"]
                    m["bar"] = max(0, min(BAR_MAX, m["bar"]))
                m["left"] -= 1
                if m["left"] <= 0:
                    self._lock_dig()              # time's up: the spade falls
                return
            s["t"] += 1
            if s["t"] == INV_REVEAL_T:
                self.sfx = "reward"               # _discoverConsumable
            if s["t"] >= INV_END_T:               # carried home -> back on the road
                self._scene = None

    def _hazard_tick(self):
            """Advance the ambush.  Impact settles it: a duck already banked
            rings clean, an unducked pounce lands -- the ENGINE takes the toll
            -- and the verdict beat plays either way before the march resumes."""
            h = self._hazard
            h["t"] += 1
            if h["t"] == HZ_TELE_T + HZ_LUNGE_T:      # the pounce lands (or doesn't)
                if h["dodged"]:
                    self.sfx = "confirm"              # a clean duck-under
                else:
                    h["hit"] = True
                    self.adv.hazard_hit()             # the small energy toll
                    self.sfx = "attackHit"
            if h["t"] >= HZ_TELE_T + HZ_LUNGE_T + HZ_END_T:
                self._hazard = None                   # back to the march
                self._wx = float(grid.X0)             # ...from the wall the

    def _lock_dig(self):
            """The spade falls: grade through the ONE lock source
            (strikefx.grade_lock -- the latency grace, the 2px marker, the
            verbatim battles >= 999 never-whiff rule; this was the THIRD
            hand-copy, timing rework 2026-07-23).  Mega banks a SECOND copy
            of the find on the spot; normal keeps the honest single; a wide
            miss still scrapes the find out -- the meter is pure upside,
            only the verdict changes."""
            s = self._scene
            m = s.pop("meter")
            g = strikefx.grade_lock(m["hist"] + [m["bar"]], m["lo"], m["hi"],
                                    veteran=self.pet.battles >= 999)
            s["grade"] = g
            if g == "mega":
                self.pet.add_item(s["key"])       # the bonus copy, banked at the lock
                self._find_msg = t("msg_adv_dug_x2", "Dug up {name} ×2!").replace("{name}", s["name"])
            elif g == "miss":
                self._find_msg = t("msg_adv_scraped", "Scraped out {name}...").replace("{name}", s["name"])
            self.sfx = "confirm" if g != "miss" else "cancel"

    def _start_battle(self, enemy):
            """A wild fight rides BattlePanel as a child (SubHost): the road's biome
            is the fight's scene, wild=True gives the pre-bell flee.
    
            THE UNFIT BODY BALKS (audit 2026-07-25): the boss gate asks the
            device's question on every chosen fight -- but a wayside wild never
            did, so a sick or hurt walker could grind recorded bouts the home
            key refuses.  It slips away instead: no bout, no life, a grace leg
            -- the pilgrimage to the town's sickbed stays walkable."""
            if (cond := self.pet.battle_condition(check_energy=False)) is not None:
                self.adv.resolve(False, fled=True)
                self._note = f"{cond.rstrip('.!')} — slipped away."
                self._note_t = NOTE_HOLD
                self.travelling = True
                return
            from tuipet.ui.screens.battlescreen import BattlePanel
            self.travelling = False               # the march pauses during the fight
            self._fighting_enemy = enemy
            self.sub = BattlePanel(self.pet, enemy=enemy, wild=True, scene=self.adv.scene)

    def _start_boss(self, boss):
            """The gate boss fight -- same road biome, flagged so _battle_done knows
            to settle it as the zone's end, not a wayside wild.
    
            THE DEVICE'S GATE HOLDS ON A CHOSEN FIGHT (battle audit ruling,
            2026-07-25, Joel: "as close to bandai vpet as much as possible, so
            anything else is extra").  `battle_condition` is the device's own
            battle button asking whether this body can fight at all -- the home
            key, both cups and the lobby have always asked it, and the road
            never did, so an injured pet was told "Muito machucado para lutar" at home
            and then marched into a BOSS.  A wayside ambush keeps the carve-out
            (you cannot decline a pounce; that beat is tuipet's own extra), but
            the gate is a stop you choose to walk into, so it asks.  Refused,
            the pet STANDS at the gate -- ESC home and a town warp both still
            work, so this can never strand a run."""
            # check_energy=False: the road's energy law is its own (D3, the
            # adventure energy audit) -- a march ARRIVES drained by design, so
            # asking the home door's energy clause here shut the gate on every
            # honest run.  The body states still hold; see battle_condition.
            if (cond := self.pet.battle_condition(check_energy=False)) is not None:
                self.travelling = False
                self._at_gate = True
                self._fighting_enemy = boss
                self._gate_refusal = cond
                self.sfx = "refuse"
                return
            from tuipet.ui.screens.battlescreen import BattlePanel
            self.travelling = False
            self._at_gate = False
            self._gate_refusal = None
            self._fighting_boss = True
            self._fighting_enemy = boss
            self.sub = BattlePanel(self.pet, enemy=boss, wild=True, scene=self.adv.scene)

    def _battle_done(self, result):
            """Settle a finished fight.  result is the battle object (has .won) or
            None if the pet fled before the bell."""
            won = bool(getattr(result, "won", False)) if result is not None else False
            fled = result is None
            enemy, self._fighting_enemy = self._fighting_enemy, None
            if not fled:                          # a fought bout (not a pre-bell flee)
                self.adv.fights += 1
                if won:
                    self.adv.wins += 1
            self.adv.chain(won)                   # the streak: BEFORE the bounty, so
            #                                       this win's own chain pays it
            drop = None
            if won and enemy is not None:
                self.adv.award_bits(enemy)        # the bounty into the purse + run tally
                drop = self.adv.award_drop(enemy)  # the AUTHORED battle drop (2026-07-26)
            if self._fighting_boss:
                self._fighting_boss = False
                out = self.adv.resolve_boss(won, fled=fled)
                if out == "won":
                    unlocked = adventure.record_win(self.pet, self.adv.zone)   # progression
                    import tuipet.utils.persistence as persistence    # profile signals: unlocks
                    m = self.adv.zone.get("map")
                    map_done = (m is not None
                                and adventure.is_map_cleared(self.pet, m))
                    if map_done:
                        persistence.map_complete_add(m - 1)  # shop shelf + eggs (0-based)
                    if self.adv.holiday:                   # conquered on a festival day
                        persistence.festival_add(self.adv.holiday)  # gates the festival egg
                    tail = t("msg_adv_new_ground", " New ground opens!") if unlocked else ""
                    if drop:
                        e = shop.entry(drop) or {}
                        tail = f"{t('msg_adv_drops', ' It drops {name}!').replace('{name}', e.get('name', 'something'))}{tail}"
                    self._home_msg = (f"{t('msg_adv_boss_felled', '{boss} felled — ').replace('{boss}', self.adv.boss_name)}"
                                      f"{t('msg_adv_conquered', '{name} conquered!').replace('{name}', self.adv.name)}{self._bits_tail()}{tail}")
                    # the zoneChange CELEBRATION plays before the homecoming
                    # (restored from the old build): the pulse first; the map-
                    # conquered BossParade -- canon shows three.  ⚠ Keyed to the
                    # map ACTUALLY completing, the same test that files the
                    # unlock note above (theme-of-truth fix 2026-07-28): the
                    # road is difficulty-ordered, and map 1's authored
                    # parade_msg boss sits at road 19 while a map-1 zone waits
                    # at 21 -- the old parade_msg key celebrated "map conquered"
                    # two zones before the shop shelf and the egg gate agreed.
                    paraders = []
                    parade_msg = None
                    if map_done:
                        paraders = [b["num"] for z in ZONES if z.get("map") == m
                                    for b in z["bosses"]][:3]
                        # the victory line rides the map's AUTHORED parade boss,
                        # whichever zone actually finished the map
                        parade_msg = next((b.get("parade_msg")
                                           for z in ZONES if z.get("map") == m
                                           for b in (z.get("bosses") or [])
                                           if b.get("parade_msg")), None)
                    self._pulse = {"t": 0, "parade": paraders,
                                   "msg": parade_msg,
                                   # the flash must SAY what it celebrates
                                   # (Joel 2026-07-25 "flashing for what?") --
                                   # and FIT while saying it: the old line named
                                   # the boss twice (the zone embeds it) and ran
                                   # to 71 cells, cut mid-scroll on the biggest
                                   # wins (audit 2026-07-25).  The homecoming
                                   # verdict keeps the full sentence.
                                   "line": t("msg_adv_boss_conquered", "{boss} — conquered!").replace("{boss}", self.adv.boss_name)}
                elif out == "fled":
                    self._home_msg = f"{t('msg_adv_turned_boss', 'Turned back from {boss}.').replace('{boss}', self.adv.boss_name)}{self._bits_tail()}"
                    self._go_home()
                elif out == "failed":
                    self._home_msg = f"{t('msg_adv_defeated', 'Defeated by {boss}.').replace('{boss}', self.adv.boss_name)}{self._bits_tail()}"
                    self._go_home()
                else:                             # 'retry' -- stand at the gate, choose
                    self._at_gate = True
                return
            # a wayside wild
            out = self.adv.resolve(won, fled=fled)
            if out == "won" and drop:
                e = shop.entry(drop) or {}
                # the strip speaks the drop over the plain "road clears" line
                self.adv.last = t("msg_adv_drop_bagged", "It drops {name} — bagged!").replace("{name}", e.get('name', 'loot'))
            if out == "failed":
                self._home_msg = f"{t('msg_adv_driven_back', 'Driven back from {name}.').replace('{name}', self.adv.name)}{self._bits_tail()}"
                self._go_home()
            else:
                # (defensive: a wayside settle never belongs to the gate -- the
                # danger warp that once started one FROM the gate is hidden now)
                self._at_gate, self._gate_refusal = False, None
                self.travelling = True            # resume the march (a grace leg follows)

    def _bits_tail(self):
            """The run's purse for the homecoming verdict (empty if nothing won)."""
            return f" +{self.adv.bits_earned}b" if self.adv.bits_earned else ""

    def _town_done(self, _result):
            """Left the town hub -- back onto the road, the march resumes."""
            self._town_sub = False
            self._town_prompt = False
            if self.pet.dead:                     # a lethal town-bag item: the run
                self._summary_shown = True        # ends at the door, not 20 legs on
                self._go_home()

    def _go_home(self):
            """Conclude the run: show the results card first (a key rides the
            teleport home), unless there's nothing to summarise -- a bare turn-back
            goes straight to the canon teleport."""
            self.travelling = False
            a = self.adv
            if not self._summary_shown and (a.bits_earned or a.fights or a.finds or a.done):
                # a run of substance gets SCORED against the zone's standing
                # best (bare turn-backs skip the card AND the books)
                import tuipet.utils.persistence as persistence
                zi = adventure.zone_index(a.zone)
                self._new_best = (persistence.zone_best_set(zi, a.score())
                                  if zi is not None else False)
                self._summary = True              # results, then a key teleports
                return
            self._trans = {"dir": "out", "phase": "leave", "t": 0}

    def _outcome_word(self):
            if self.adv.done:
                return t("msg_adv_conquered_short", "Conquistado!")
            if self.adv.failed:
                return t("msg_adv_defeated_short", "Derrotado")
            return t("msg_adv_turned_back", "Recuado")

