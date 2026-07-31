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

def feed(app):
    """FEED: the selected row's true effects beside the live gauges."""
    p, m = app.pet, app.mode
    # both rows disclose in FULL, weight included -- the meat row used to
    # hide its +1 while the pill admitted its +5 (feed audit 2026-07-19)
    # pre-fit to the 26-col card (run-off sweep 2026-07-23: the meat row
    # ran 29 and wrapped the card) -- full disclosure kept, across three
    # short rows instead of two long ones
    sel = min(getattr(m, "cursor", 0), 1)
    row = (t("feed_meat_row", "Meat — hunger +1,"), t("feed_pill_row", "Pill — cures sickness,"))[sel]
    tail = (t("feed_meat_tail", "weight +1 · the staple"), t("feed_pill_tail", "effort +1 · energy +7"))[sel]
    tail2 = ("", t("feed_pill_tail2", "weight +5"))[sel]
    if sel == 0:
        # meat's refusal gates, visible BEFORE the pick (QOL 2026-07-23):
        # the menu used to close on a refusal you couldn't see coming
        from tuipet.core.petcare import FULL_HUNGER
        T = theme
        if p.sick:
            tail2 = f"[{T.NEG}]{t('feed_refused_sick', 'refused — sick: the Pill')}[/]"
        elif p.poop:
            tail2 = f"[{T.NEG}]{t('feed_refused_clean', 'refused — clean first (C)')}[/]"
        elif p.hunger >= FULL_HUNGER:
            tail2 = f"[{T.NEG}]{t('feed_refused_full', 'refused — belly is full')}[/]"
    card(app, t("menu_feed", "Feed"), [
        f"{t('status_hunger', 'Hunger').ljust(8)}{hearts(p.hunger)}",
        f"{t('status_effort', 'Effort').ljust(8)}{hearts(p.strength)}",
        f"{t('status_weight', 'Weight').ljust(8)}{p.weight}g" + (f"   [b]{t('status_sick', 'sick')}[/]" if p.sick else ""),
        "", f"[b]{row}[/]", f"[b]{tail}[/]",
        f"[b]{tail2}[/]" if tail2 else "",
        "", f"[dim]↑↓ {t('hint_pick', 'pick')}  ENTER {t('hint_feed', 'feed')}[/]"],
        subtitle=gen_subtitle(p))


def eat(app):
    """The live feeding readout (plays while the eat fx runs).  What is live:
    the hunger hearts filling, weight, effort, and the premium-meat satiety
    window.  (The Fuel/calorie bar left 2026-07-20: calories is a DVPet-only
    mechanic with no DSprite basis and a drain-only buffer, so the readout
    charted a value feeding never touched.)"""
    p, T = app.pet, theme
    full = getattr(p, "full_until", 0.0)
    sated = full and p.world_seconds < full
    lines = [
        f"[b]{p.name[:14]}[/] [dim]· feeding[/]", DIV,
        f"Hunger   {hearts(p.hunger)}",
        DIV,
        f"Weight   {p.weight}g",
        f"Effort   {hearts(p.strength)}",
        (f"[{T.POS}]sated · {age_compact(full - p.world_seconds)} left[/]"
         if sated else ""),
    ]
    app.stats_w.border_subtitle = gen_subtitle(p)
    app.stats_w.update("\n".join(lines))


def shop(app):
    """SHOP/BAG: the selected entry's dossier."""
    import tuipet.core.shop as shop_mod
    T = theme
    p, m = app.pet, app.mode
    rows = m._rows()
    if not rows:
        card(app, "Shop" if m.mode == "shop" else "Bag",
             ["", "[dim]nada aqui[/]", "",
              f"Bits   [b]{p.bits}b[/]"])
        return
    e = rows[min(m.cursor, len(rows) - 1)]
    ttl = "Shop" if m.mode == "shop" else "Bag"
    if e.get("title_id") is not None:
        state = ("worn" if e.get("worn")
                 else "owned" if e.get("owned") else f"{e['price']}b")
        lines = [f"[b]{e['name'][:24]}[/]", "[dim]honra de domador[/]",
                 f"Status  {state}", "",
                 f"Bits    [b]{p.bits}b[/]", "",
                 "[dim]ENTER compra, depois usa[/]"]
    else:
        have = p.inventory.get(e["key"], 0)
        # word-wrap the effect blurb (card audit 2026-07-24): an effect_line
        # runs to 51 chars ("ride! weight -2 · energy -1 — shred the living
        # room") and a crest's answer list past 18 -- both were sliced flat.
        if str(e["key"]).startswith("egg_of_"):
            # the crest egg's LIVE answer (the same evolution.check the
            # item runs; shop polish 2026-07-17)
            names = shop_mod.crest_answer(p, e["key"])
            eff = ([f"[{T.POS}]{ln}[/]" for ln in wrap("answers: " + " / ".join(names), 2)]
                   if names else ["[dim]nada responde ainda[/]"])
        else:
            eff = [f"[dim]{ln}[/]" for ln in wrap(shop_mod.effect_line(e), 3)]
        if m.mode == "shop":
            short = e["price"] - p.bits
            price = (f"Preço   [{T.NEG}]{e['price']}b · falta {short}[/]"
                     if short > 0 else f"Preço   {e['price']}b")
        else:
            price = f"Sells   {shop_mod.resell_price(e)}b"
        lines = [f"[b]{e['name'][:24]}[/]", *eff, "",
                 price,
                 f"Owned   x{have}",
                 f"Bits    [b]{p.bits}b[/]", "",
                 ("[dim]ENTER comprar[/]" if m.mode == "shop"
                  else "[dim]ENTER usar  R vender[/]")]
    card(app, ttl, lines, subtitle=gen_subtitle(p))


