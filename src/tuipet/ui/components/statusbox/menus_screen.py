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

def title(app: Any) -> None:
    card(app, "TUIPET", [f"[dim]{t('title_terminal_vpet')}[/]", "", "",
                         f"[dim]{t('title_creature_awaits')}[/]", "",
                         f"[dim]{t('title_press_enter')}[/]", f"[dim]{t('title_to_begin')}[/]"])


def scenes(app: Any) -> None:
    """The browsed scene's dossier: the LCD shows the SCENE, this card
    carries the words (picker restore 2026-07-17)."""
    m = app.mode
    row = m.rows[m.cursor]
    name = m._name(row)
    state = "picked" if row == app.pet.bg_pick else \
        ("the default" if not row and not app.pet.bg_pick else "a preview")
    # word-wrap the picker message (card audit 2026-07-24): "pick a scene —
    # it hangs behind the mon" (38) and "De volta à cena do próprio ovo." (28)
    # were sliced at [:26], losing the tail.
    sc_lines = [f"[dim]{m.cursor + 1} of {len(m.rows)}[/]", "",
                "Na parede", f"  [b]{name[:24]}[/]",
                f"  [dim]{state}[/]", ""]
    sc_lines += wrap(m.msg or "", 2)
    sc_lines.append("[dim]↑↓ browse  ENTER hang[/]")
    card(app, "Scenes", sc_lines)


def datacore(app: Any) -> None:
    """DATACORE: which data page is up, and whose core it is."""
    p, m = app.pet, app.mode
    page = m.pages[min(m.i, len(m.pages) - 1)][0]
    dc_lines = [
        f"[b]{p.name[:16]}[/]",
        f"[dim]{p.stage} · {p.attribute}[/]", "",
        f"Página [b]{page[:18]}[/]",
        f"[dim]{m.i + 1} of {len(m.pages)}[/]", ""]
    dc_lines += wrap(m.note or "", 2)          # note carries mode-change lines
    dc_lines.append("[dim]←→ páginas  SPACE núcleo[/]")
    card(app, "datacore", dc_lines, subtitle=gen_subtitle(p))


def lobby(app: Any) -> None:
    """LOBBY: your card and the room."""
    m = app.mode
    st = m.state
    if st is None or getattr(st, "me_id", None) is None:
        card(app, "Lobby", ["", "[dim]conectando…[/]"])
        return
    roster = list(getattr(st, "roster", []) or [])
    links = persistence.get_progress().get("connections", 0)
    card(app, "Lobby", [
        f"[b]{(m._last_name or '?')[:18]}[/]",
        f"[dim]{app.pet.name[:14]} rides along[/]", "",
        f"Here   {len(roster)} tamer" + ("s" if len(roster) != 1 else ""),
        f"Links  {links} lifetime", "",
        "[dim]datate p/ chat · ENTER[/]",
        "[dim]↑↓ escolha um domador[/]"])


def help_(app: Any) -> None:
    import tuipet.utils.update as update
    try:
        ver = update.current_version()
    except Exception:
        ver = "?"
    snd = "on" if app.sound else "off"
    card(app, "Help", [
        f"tuipet [b]v{ver}[/]", "",
        f"Sound  {snd}",
        f"Ger    {app.pet.generation}", "",
        "[dim]o guia rola[/]",
        "[dim]no display[/]", "",
        "[dim]↑↓ rolar  ESC sair[/]"])


def options(app: Any) -> None:
    import tuipet.ui.screens.optionsscreen as _opts
    m = app.mode
    row = _opts._ROWS[min(m.cursor, len(_opts._ROWS) - 1)]
    desc = _opts._get_desc().get(row, "")
    # word-wrap (card audit 2026-07-24): desc runs to 53 chars and the update
    # msg to ~49; the old [:26]/[26:52]/[:26] slices cut words mid-glyph and
    # dropped the msg's action hint.  Body budget = 14 rows (16 - title/DIV);
    # desc<=3 + msg<=4 + 5 fixed leaves headroom.
    lines = [f"[b]{_opts._get_label().get(row, row.title())}[/]", ""]
    lines += [f"[dim]{ln}[/]" for ln in wrap(desc, 3)]
    if m.msg:
        lines += [""] + [f"[yellow]{ln}[/]" for ln in wrap(m.msg, 4)]
        lines.append("")
    lines.append("[dim]ENTER alterna[/]")
    card(app, "Options", lines)


def bug(app: Any) -> None:
    m = app.mode
    n = len(getattr(m, "buf", ""))
    card(app, "Bug Report", [
        "[dim]direto pro dev[/]", "",
        f"Datatou {n} caracs", "",
        "[dim]diga o que você fez e[/]",
        "[dim]o que deu errado[/]", "",
        "[dim]ENTER enviar  ESC sair[/]"])


def assist(app: Any) -> None:
    from tuipet.core.pet import AUTO_CARE_VISIT_PRICE
    p = app.pet
    on = getattr(p, "auto_care", False)
    fee = AUTO_CARE_VISIT_PRICE.get(p.stage, 200)
    card(app, "Assistant", [
        f"Ajuda   [b]{'ativa' if on else 'inativa'}[/]", "",
        f"Visita  ~{fee}b",
        f"Bits    [b]{p.bits}b[/]", "",
        "[dim]limpa e alimenta[/]",
        "[dim]enquanto você está fora[/]", "",
        "[dim]ENTER contratar/dispensar[/]"])


def discipline(app: Any) -> None:
    from tuipet.core.petbase import MAX_OBEDIENCE as _MAXOBED
    """The praise/scold picker's card (canon restoration B): the gauge,
    the open moment, and what each verb would land."""
    p, T = app.pet, theme
    app.stats_w.border_subtitle = gen_subtitle(p)
    if p.discipline_call:
        moment = f"[{T.NEG}]dando chilique![/]"
    elif p.world_seconds <= getattr(p, "praise_window", 0.0):
        moment = f"[{T.POS}]um momento de orgulho[/]"
    else:
        moment = "[dim]calmo[/]"
    lines = [f"[b]{p.name[:14]}[/] [dim]· lessons[/]", DIV,
             # bar() takes a PERCENT -- the gauge is 0..MAX_OBEDIENCE (150,
             # canon), so scale it or a 100/150 pet reads as full
             f"Manners  {bar(p.obedience * 100 // _MAXOBED, 11, T.POS)}"
             f" {p.obedience}",
             f"Moment   {moment}", DIV,
             "[dim]repreenda chilique: +25[/]",
             "[dim]elogie vitória: +10[/]",
             "[dim]chiliques ignorados custam ✗[/]"]
    app.stats_w.update("\n".join(lines))


def training(app: Any) -> None:
    """The 0.5 drill's card (2026-07-17): one timing bar, so one card --
    the four-drill readouts left with the classic training system."""
    p, tp, T = app.pet, app.mode, theme
    app.stats_w.border_subtitle = gen_subtitle(p)
    eff = hearts(p.strength)
    energy = bar(p.energy_pct(), 11, T.ENERGY)
    window = tp.mega_hi - tp.mega_lo + 1
    form = getattr(p, "saved_hit_type", "normal")
    if tp.phase == "bar":
        lines = [f"[b]{p.name[:14]}[/] [dim]· train[/]", DIV,
                 "[b]acerte o tempo[/]", "",
                 f"Window   {window}px",
                 f"Form     {form}",
                 f"Effort   {eff}", f"Energy   {energy}",
                 DIV, "[dim]SPACE trava a barra[/]"]
    else:
        lines = [f"[b]{p.name[:14]}[/] [dim]· train[/]", DIV,
                 "[b]o ataque[/]", "",
                 f"Grade    {tp.grade or ''}",
                 f"Energy   {energy}", DIV, ""]
    app.stats_w.update("\n".join(lines))


def dna(app: Any) -> None:
    p, m, T = app.pet, app.mode, theme
    app.stats_w.border_subtitle = gen_subtitle(p)
    f = m.field
    same = f == p.field
    own, chg = p.dna_owned.get(f, 0), p.dna_applied.get(f, 0)
    # the charge bill, TRUTHFULLY (modularize audit 2026-07-17): the old
    # line billed "spirit/mood" -- both systems are gone.  applyDNA's real
    # cost is ENERGY: 1/unit on your own Field, doubled off-Field (and the
    # off-field sickness risk left with the sickness rebuild).
    cost = "energia -1/cada (mesmo)" if same else "energia -2/cada (outro)"
    import tuipet.core.evolution as evolution
    reqs = data.load_requirements()
    dna_t = [t for t in data.load_evolutions().get(p.num, [])
             if reqs.get(t) and any(g[0] != "None" for g in reqs[t]["dna"].values())]
    unlocked = sum(1 for t in dna_t if evolution._dna_ok(p, reqs[t]))
    screen = {"home": "menu", "charge": "carga", "stats": "stats",
              "reqs": "requisitos", "bet": "gerar", "mash": "gerar",
              "result": "gerar"}.get(m.phase, "menu")
    import textwrap
    last_rows = [f"[dim]{s}[/]" for s in textwrap.wrap(m.last or "", 24)[:2]]
    last_rows += [""] * (2 - len(last_rows))
    lines = [
        # dynamic fit (run-off sweep 2026-07-23: a 14-char name + 'DNA ·
        # generate' ran 30 cols): the NAME gives way, the tail stays whole
        f"[b]{p.name[:max(4, CARD_W - 9 - len(screen))]}[/]"
        f" [dim]· DNA · {screen}[/]", DIV,
        f"Bits     [{T.COIN}]{p.bits}[/]",
        f"Campo    {data.pretty_field(f)}" + ("  [dim](seu)[/]" if same else ""),
        f"Guardado {own:<2}    Carga   {chg}",
        f"Afinid.  {p.dna_percent(f)}%    [dim]x{m.amount}[/]",
        f"Libera   [b]{unlocked}[/]/{len(dna_t)} forma(s)",
        DIV,
        f"[dim]{cost}[/]",
        *last_rows,
        "[dim]cargas locais são baratas[/]",
        "[dim]ESC volta[/]",
    ]
    app.stats_w.update("\n".join(lines))


