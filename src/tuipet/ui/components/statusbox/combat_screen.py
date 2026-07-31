from __future__ import annotations
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

def raid(app):
    """RAID: the boss, the shared pool, your standing — ALL the numbers
    live HERE (scene-screen law, raid uncramp 2026-07-23: the LCD page
    duplicated every one of these lines and crushed the boss for it)."""
    from tuipet.ui.screens.raidscreen import _fmt as _fmt_dmg
    m = app.mode
    v = m.view or {}
    b = m._boss()
    if not b:
        card(app, "Raid", ["", "[dim]chamando o portal…[/]"])
        return
    pool, mx = int(b.get("hp", 0)), max(1, int(b.get("max_hp", 1)))
    pct = max(0, min(100, pool * 100 // mx))
    rank, mine = (list(v.get("you") or (0, 0)) + [0, 0])[:2]
    standing = m._standing()
    left = max(0, int((b.get("end" if standing else "start", 0)
                       - v.get("now", 0))))
    when = "%dd %dh" % (left // 86400, left % 86400 // 3600)
    top = v.get("top") or []
    lead = (f"{str(top[0][0])[:10]} · {_fmt_dmg(top[0][1])}" if top else "—")
    card(app, "Raid", [
        f"[b]{b.get('name', '?')[:18]}[/]",
        (f"Pool   {bar(pct, 11, theme.NEG)} {pct}%" if standing
         else "[dim]chefe a caminho[/]"),
        (f"[dim]{when} left[/]" if standing else f"[dim]em {when}[/]"),
        "",
        (f"You    #{rank} · {_fmt_dmg(mine)}" if rank
         else "Você   [dim]— não classificado[/]"),
        f"Top    {lead}",
        f"Tries  {v.get('attempts', 0)} today",
        ("[b]recompensa pronta — C[/]" if v.get("award") else ""),
        "[dim]SPACE raid  C coletar[/]"],
        subtitle=gen_subtitle(app.pet))


def tournament(app):
    # (the cup's own sub->battle hand-off moved into painter_for -- the
    # dispatcher lends every host's card to its embedded fight now)
    p, t, T = app.pet, app.mode.tourney, theme
    app.stats_w.border_subtitle = gen_subtitle(p)
    if t is None:                      # cup-select phase (no bout yet)
        card(app, "Cup", ["", "Escolha uma", "copa p/ entrar."],
             subtitle=gen_subtitle(p))
        return
    if t.over and t.champion:
        lines = [f"[b]{p.name[:14]}[/] [dim]· cup[/]", DIV,
                 f"[b]{t.name[:24]}[/]", "",
                 f"[{T.POS}]★ CHAMPION ★[/]", "",
                 f"Troféu   [{T.COIN}]★{p.trophies}[/]",
                 f"Prêmio   [{T.COIN}]+{t.reward_bits}b[/]", DIV,
                 "[dim]você venceu a copa![/]"]
    elif t.over:
        lines = [f"[b]{p.name[:14]}[/] [dim]· cup[/]", DIV,
                 f"[b]{t.name[:24]}[/]", "",
                 f"[{T.NEG}]eliminado[/]",
                 f"[dim]no(a) {t.round_name}[/]", "",
                 f"Troféu   [{T.COIN}]★{p.trophies}[/]", DIV,
                 "[dim]treine e tente de novo[/]"]
    else:
        # WHO YOU FACE (cup audit 2026-07-25): the faceoff and the
        # introductions used to name the challenger in a caption row UNDER
        # a full-height arena -- four rows past the LCD, so it was clipped
        # off screen and the fight opened against a stranger.  The card is
        # where a fight's context lives (the battle card's own law), so the
        # foe lives here now.
        opp = t.current_opponent() if not t.over else None
        foe = (f"vs [b]{opp['name'][:12]}[/][dim][{opp['attribute'][:2]}][/]"
               if isinstance(opp, dict) else "")
        lines = [
            f"[b]{p.name[:14]}[/] [dim]· cup[/]", DIV,
            f"[b]{t.name[:24]}[/]",
            f"Match    {t.round + 1} / 3",
            foe,
            f"Troféu   [{T.COIN}]★{p.trophies}[/]",
            DIV,
            f"Effort   {hearts(p.strength)}",
            f"Energy   {bar(p.energy_pct(), 11, T.ENERGY)}",
            f"Form     {getattr(p, 'saved_hit_type', 'normal')}",
            DIV,
            "[dim]lute pela copa[/]",
        ]
    app.stats_w.update("\n".join(lines))


def battle(app):
    p, m, T = app.pet, app.mode, theme
    b = m.battle                    # None until the timing bar locks (0.5)
    app.stats_w.border_subtitle = gen_subtitle(p)
    enemy = m.enemy or {}
    raid = bool(getattr(m, "raid", False))
    tag = f" [{T.NEG}]BOSS[/]" if enemy.get("boss") else ""
    from tuipet.core.battle import RAID_PLAYER_HP
    dflt = RAID_PLAYER_HP if raid else 5   # pre-lock: the raid fights from 10
    pet_max = b.pet_max if b else dflt
    foe_max = b.enemy_max if b else 5
    php = getattr(m, "hud_php", b.pet_hp if b else dflt)
    fhp = getattr(m, "hud_fhp", b.enemy_hp if b else 5)
    pp = int(100 * php / pet_max) if pet_max else 0
    fp = int(100 * fhp / foe_max) if foe_max else 0
    if raid:
        # the boss's real health is the COMMUNITY POOL (raid audit
        # 2026-07-23: the card leaked RaidBout's 5/5 display stub -- a
        # 5.5M shared boss shown as a five-heart foe)
        pool = enemy.get("pool")
        if pool:
            phv, pmx = int(pool[0]), max(1, int(pool[1]))
            pct = max(0, min(100, phv * 100 // pmx))
            foe_line = f"Pool {bar(pct, 11, T.NEG)} {pct}%"
        else:
            foe_line = "Pool [dim]compartilhado pelo portal[/]"
    else:
        foe_line = f"Foe  {bar(fp, 11, T.NEG)} {fhp}/{foe_max}"
    lines = [
        f"[b]{p.name[:14]}[/] [dim]· {'raid' if raid else 'batalha'}[/]", DIV,
        f"vs [b]{enemy.get('name', '?')[:14]}[/]{tag}", "",
        f"You  {bar(pp, 11, T.POS)} {php}/{pet_max}",
        foe_line,
        DIV,
    ]
    # the locked grade, VISIBLE (transparency 2026-07-23: training showed
    # its Grade, battle showed NOTHING -- the intro-mash bug locked a miss
    # and the player had no way to see it happen.  Never again: every
    # fight wears its lock.)
    if getattr(m, "locked", None):
        g = m.locked
        gsty = T.POS if g == "mega" else (T.NEG if g == "miss" else "")
        lines.append(f"Trava [{gsty}]{g}[/]" if gsty else f"Trava {g}")
    if m.done_anim and raid:
        res = (f"[{T.POS}]RESISTIU[/]" if m.won
               else f"[{T.NEG}]NOCAUTEADO[/]")
        lines += [res, f"[b]causou {getattr(b, 'dealt', 0)}[/] [dim]→ ao portal[/]",
                  "", "[dim]SPACE  continuar[/]"]
    elif m.done_anim:
        res = f"[{T.POS}]VITÓRIA![/]" if m.won else f"[{T.NEG}]DERROTA[/]"
        lines += [res, f"[dim]{(b.reward if b else '') or ''}"[:30] + "[/]",
                  "", "[dim]SPACE  continuar[/]"]
    elif getattr(m, "phase", "") == "ready":
        # readiness_line is <=26, but the result-anim note ("a draw — counts
        # as a loss · record 12W/30", ~40) also rides hud_note -- wrap so it
        # is not sliced (card audit 2026-07-24).
        lines += [f"[dim]{ln}[/]" for ln in wrap(m.hud_note or "", 2)]
        lines += ["", "[dim]SPACE  travar barra[/]"]
    else:
        lines += [f"[dim]{ln}[/]" for ln in wrap(m.hud_note or "", 2)]
        lines += ["", "[dim]SPACE pular · ESC terminar[/]"]
    app.stats_w.update("\n".join(lines))


