from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import textwrap
import tuipet.utils.backgrounds as backgrounds
import tuipet.data.loaders.data as data
import tuipet.core.egg as egg_mod
import tuipet.utils.persistence as persistence
import tuipet.utils.theme as theme
from tuipet.core.arena import bar, hearts
from tuipet.core.petbase import DISOBEY_BELOW
from tuipet.i18n.translator import t

CARD_W = 26
DIV = "[dim]" + "─" * CARD_W + "[/]"

from .helpers import *

def egg_lines(pet: Any) -> Any:
    mins, secs = divmod(int(pet.age_seconds), 60)
    return [
        f"[b]{t('egg_title', 'Egg')}[/] [dim]· {t('egg_subtitle', 'egg')}[/]",
        DIV,
        f"[dim]{t('egg_desc', 'a new life is warming')}[/]",
        "",
        t('egg_destined', 'Destined to hatch'),
        # the destined BABY, not the egg's display title ("Kera Egg"
        # promised an egg would hatch an egg); a pool keeps its mystery
        f"  [b]{egg_mod.destined_name(pet.egg_type) or '???'}[/]",
        DIV,
        f"{t('egg_age', 'Age').ljust(8)}{mins}m{secs:02d}s",
        # the wait has a shape now (gameplay polish #21, 2026-07-22): the
        # card said only "hatches on its own" over a rising Age -- with no
        # ETA the first minute read as a mystery stall.  LIVE data: the
        # real incubation clock.
        _hatch_line(pet),
        "",
        f"[dim]{t('egg_tip1', 'keep it cosy — it')}[/]",
        f"[dim]{t('egg_tip2', 'hatches on its own')}[/]",
    ]


def _hatch_line(pet: Any) -> Any:
    left = max(0, int(pet.EGG_DURATION - pet.stage_seconds))
    if left <= 0:
        return f"{t('egg_hatch', 'Hatch').ljust(8)}[b]{t('egg_hatch_now', 'any moment now…')}[/]"
    return f"{t('egg_hatch', 'Hatch').ljust(8)}{t('egg_hatch_time', 'in ~{left}s').format(left=left)}"


def grave_lines(pet: Any) -> Any:
    return [
        f"[b]{pet.name[:16]}[/] [dim]· {t('grave_subtitle', 'rest')}[/]",
        DIV,
        f"[dim]{t('grave_desc', 'a life remembered')}[/]",
        "",
        f"{t('grave_lived', 'Lived').ljust(9)}{age_compact(pet.age_seconds)}",
        f"{t('grave_reached', 'Reached').ljust(9)}{pet.stage}",
        # pre-fit: a long cause ran the 26-col card (run-off sweep
        # 2026-07-23) -- the label row holds 17 cause chars
        f"{t('grave_cause', 'Cause').ljust(9)}{(getattr(pet, 'death_cause', '') or t('grave_unknown', 'unknown'))[:17]}",
        f"{t('grave_attrib', 'Attrib').ljust(9)}{pet.attribute}",
        f"{t('grave_record', 'Record').ljust(9)}{pet.wins}W / {pet.battles}",
        DIV,
        f"[dim]{t('grave_tip1', 'gone, but not')}[/]",
        f"[dim]{t('grave_tip2', 'forgotten.')}[/]",
        "",
        f"[dim]{t('grave_new_egg', 'press N for a new egg')}[/]",
    ]


def eggselect(app: Any) -> None:
    m = app.mode
    # carousel = hatchable eggs ONLY (Joel 2026-07-12: no silhouettes,
    # no goals); the badge/shown branches below stay defensive in case a
    # locked egg ever leaks onto it.  Carousel polish 2026-07-18: the card
    # names the egg's wired HOME scene, keeps a multi-target egg's
    # mystery, and badges a never-raised species.
    idx = m.carousel[m.i] if m.carousel else 0
    state = m.states.get(idx, "owned")
    targets = egg_mod.hatch_targets(idx)
    if state == "locked":
        shown, badge = "???", "[dim]selado[/]"
    elif len(targets) > 1:
        shown, badge = "???", "[dim]dois destinos se agitam[/]"
    else:
        shown = egg_mod.destined_name(idx)     # the BABY, not the egg's title
        fresh = bool(targets) and \
            data.canonical_num(targets[0]) not in persistence.get_album()
        badge = ("[b]★ nunca criado[/]" if fresh
                 else {"temp": "[dim]só essa ger.[/]"}.get(state, "[dim]pronto[/]"))
    # the egg wears its NAME (Joel 2026-07-22: "shouldnt the egg carousel
    # screen show the name of the egg?") -- the browsed egg had no
    # label anywhere, so matching it to its egg-guide entry meant matching
    # art by eye.  The old title ruling only banned the egg's name on the
    # HATCH line (an egg must not promise to hatch an egg); the egg's own
    # title over the dossier is exactly what that line left room for.
    ename = "???" if state == "locked" else egg_mod.hatch_name(idx)
    scene = backgrounds.name(backgrounds.scene_for_egg(idx))
    card(app, "New Egg", [f"[dim]{m.i + 1} of {m.n} · {m.locked} locked[/]",
                          f"[b]{ename[:22]}[/]", "",
                          "Destinado a chocar", f"  [b]{shown}[/]",
                          f"  {badge}", "",
                          f"Casa   {scene[:18]}", "",
                          "[dim]←→ browse  ENTER pick[/]"])


def eggguide(app: Any) -> None:
    """EGG GUIDE: the browsed egg's dossier."""
    m = app.mode
    state = m.states.get(m.i, "locked")
    # the name shows for EVERY egg -- the guide's own list and detail
    # header always revealed it; the card's "???" mask was the one
    # surface disagreeing (round 34: the book's purpose is showing
    # what's out there)
    name = egg_mod.hatch_name(m.i)
    live = egg_mod.unlock_progress(m.i, m.prog)
    rule = m.rules.get(m.i)
    keeps = ("só essa ger." if rule is not None and not rule["can_perm"]
             else "para sempre")
    hints = ("←→ próx. ovo  ESC voltar" if m.detail
             else "ENTER história  ↑↓ navegar")     # phase-true (round 34)
    # the goal WRAPS to two card lines -- the one-slice clip froze the dual
    # map gate mid-word ("clear adventure map 1 (or", Joel 2026-07-28)
    goal = wrap(live, 2) if live and state == "locked" else [""]
    card(app, "Egg", [
        f"[dim]{m.i + 1} of {m.n}[/]", "",
        f"Choca    [b]{name[:16]}[/]",
        f"Estado   {state}",
        f"Guarda   {keeps}", ""]
        + [f"[b]{g}[/]" if g else "" for g in goal]
        + [f"[dim]{hints}[/]"])


def death(app: Any) -> None:
    p = app.pet
    days = int(getattr(p, "age_seconds", 0) // 86400)
    cause = getattr(p, "death_cause", "") or "old age"
    card(app, "In Memory", [
        f"[b]{p.name[:18]}[/]",
        f"[dim]{p.stage} · gen {p.generation}[/]", "",
        f"Lived  {days} day" + ("s" if days != 1 else ""),
        f"De     {cause[:20]}", "",
        "[dim]seus dados podem viver[/]",
        "[dim]no próximo ovo[/]"])


