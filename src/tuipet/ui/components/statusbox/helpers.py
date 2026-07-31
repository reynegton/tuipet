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

def gen_subtitle(pet):
    """'gen N', wearing the bought honor when one is worn (the honors board,
    prestige sink 2026-07-14)."""
    t = data.title_name(persistence.get_title_worn())
    return f"gen {pet.generation} · {t}" if t else f"gen {pet.generation}"


def age_compact(seconds):
    """d/h then h/m then m/s -- raw total minutes read as noise on an older
    pet ('4325m40s', status-box audit 2026-07-04)."""
    s = int(max(0, seconds))
    if s >= 86400:
        return f"{s // 86400}d{(s % 86400) // 3600:02d}h"
    if s >= 3600:
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"
    return f"{s // 60}m{s % 60:02d}s"


def care_deco(pet, word=None):
    """The care badges shown beside the status word -- one list, shared by the
    home Stats panel and every card that wants them.  Order is priority: the
    lowest ones drop first on overflow."""
    T = theme
    if word is None:
        word = pet.status_word()
    deco = []
    # ENERGY, not raw terminal blue (theme audit 2026-07-28): the Zzz was
    # the last hard-coded colour tag in the app, one shade on EVERY theme
    # beside siblings that all ride the palette.  Sleep restores energy;
    # the badge wears the energy readout's tint.
    if pet.asleep and word != t("status_asleep", "asleep"): deco.append(f"[{T.ENERGY}]{t('deco_zzz', 'Zzz')}[/]")
    if pet.sick and word != t("status_sick", "sick"): deco.append(f"[{T.NEG}]{t('deco_sick', '+sick')}[/]")
    # +hurt RESTORED (badge audit 2026-07-24, Joel "see if we are missing any
    # other badges"): injury came back with canon restoration but its badge
    # did not.  status_word ranks sick/asleep/elderly ABOVE injured, so a
    # sick+injured pet showed only "sick" -- the player pilled it and never
    # learned it also needed a BANDAGE (a different cure that coexists with
    # sickness by design).  Mirrors +sick: shown unless injured IS the word.
    # (the +tired badge stays gone -- is_fatigued() is hardwired False; the
    # +med/+bnd/+vit item badges stay gone with the medicine-ITEM system.)
    if pet.is_injured() and word != t("status_injured", "injured"): deco.append(f"[{T.NEG}]{t('deco_hurt', '+hurt')}[/]")
    if pet.is_frail(): deco.append(f"[{T.NEG}]{t('deco_frail', '+frail!')}[/]")
    if pet.poop: deco.append(f"[{T.COIN}]{t('deco_poop', '~poop x{count}').format(count=pet.poop)}[/]")
    # +rude (badge audit 2026-07-24): manners drives feed/train/battle
    # refusals below DISOBEY_BELOW, but the gauge lives only on datacore --
    # a pet "torce o nariz!" with no on-card reason.  This is the ONLY
    # signal that a refusal is EARNED disobedience, not a bug.  Below the
    # ailments/needs in priority: a hungry, defiant pet shows the hunger
    # first.  Discipline (praise/scold/p) or a Textbook lifts it back.
    if getattr(pet, "obedience", DISOBEY_BELOW) < DISOBEY_BELOW:
        deco.append(f"[{T.CARE}]{t('deco_rude', '+rude')}[/]")
    # (the ✦care-effect badge left with the Futon's careEffect runtime;
    # strict-DSprite items 2026-07-17)
    # the standing buffs, visible at HOME (QOL 2026-07-23): satiety and
    # auto-clean only ever showed in the transient eat readout, and a
    # hired assistant (billing per visit!) showed nowhere at all.  Lowest
    # priority: they drop first when the need badges pile up.
    def _left(until):
        s = int(until - pet.world_seconds)
        return f"{s // 3600}h" if s >= 3600 else f"{max(1, s // 60)}m"
    full = getattr(pet, "full_until", 0.0)
    if full and pet.world_seconds < full:
        deco.append(f"[{T.POS}]{t('deco_sated', 'sated')} {_left(full)}[/]")
    tidy = getattr(pet, "auto_clean_until", 0.0)
    if tidy and pet.world_seconds < tidy:
        deco.append(f"[{T.POS}]{t('deco_tidy', 'tidy')} {_left(tidy)}[/]")
    if getattr(pet, "auto_care", False):
        deco.append(f"[{T.COIN}]{t('deco_helper', 'helper')}[/]")
    return deco


def status_line(status, deco, width=26):
    """Assemble the status word + deco glyphs, bounded to `width` visible cols
    so the Stats box never wraps past its 16-row height. Drops the lowest-priority
    deco that would overflow (rare: only when asleep+sick+poop+effect pile up)."""
    from rich.text import Text
    used = len(status) + 3                      # the status word + 3 spaces
    shown = []
    for d in deco:
        vis = len(Text.from_markup(d).plain)
        add = vis + (2 if shown else 0)         # 2-space separator between glyphs
        if used + add <= width:
            shown.append(d)
            used += add
    return f"[b]{status}[/]   " + "  ".join(shown)


def wrap(text, max_lines, width=CARD_W):
    """Word-wrap PLAIN text into card rows on WORD boundaries (card audit
    2026-07-24, Joel "words are getting cut off").  The Options card used a
    raw text[:26] / [26:52] slice, which split "auto-install" mid-glyph and
    dropped a message's tail past 26 chars.  Caps at max_lines; an over-long
    tail ends the last kept line with an ellipsis instead of a silent
    amputation.  Callers wrap the result in their own markup."""
    # break_on_hyphens=False keeps "auto-install" whole rather than snapping
    # it at the hyphen; break_long_words still splits a lone word wider than
    # the card so nothing can silently overrun.
    lines = textwrap.wrap(text, width, break_on_hyphens=False) if text else []
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = lines[-1][:width - 1].rstrip() + "…"
    return lines


def card(app, title, lines, subtitle=""):
    """The shared card frame: bold title, divider, body."""
    app.stats_w.border_subtitle = subtitle
    body = [f"[b]{title}[/]", DIV] + lines
    app.stats_w.update("\n".join(body))


