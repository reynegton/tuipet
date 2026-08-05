"""In-game help — the controls and a quick how-to, so a new player isn't left
staring at single-letter keys (Joel 2026-07-09).  Scrolls in the LCD box; open
with ? from anywhere on the home screen."""
from __future__ import annotations
from typing import Any, Dict, List, Optional, Tuple, Callable, Union
import tuipet.ui.components.menu as menu
from tuipet.utils.theme import INK, INK_B, DIM    # noqa: F401  (palette names bound for theme.apply propagation)
from tuipet.i18n.translator import t

VIS = 8                                   # lines shown at once in the box

# (text, kind): 2 = section head (bold), 1 = a control line, 0 = prose (dim)
def get_help() -> Any:
    res = [
        (t("help_txt_care", "CARE"), 2),
        (t("help_txt_feed", "f feed - meat fills; the pill"), 1),
        (t("help_txt_feed_2", "  cures sickness, free and infinite"), 0),
        (t("help_txt_heal", "h heal - bandage a battle injury,"), 1),
        (t("help_txt_heal_2", "  free (a wound also mends with time)"), 0),
        (t("help_txt_clean", "c clean poop"), 1),
        (t("help_txt_lights", "o lights   v assistant - paid help:"), 1),
        (t("help_txt_lights_2", "  a fee per visit + an hourly wage"), 0),
        (t("help_txt_lights_3", "  once it's Rookie or older"), 0),
        (t("help_txt_gift", "ENTER accepts a found gift"), 1),
        (t("help_txt_mistakes", "Ignored calls add ✗ care mistakes"), 0),
        (t("help_txt_mistakes_2", "(status card): they pick which form"), 0),
        (t("help_txt_mistakes_3", "comes next and reset each stage."), 0),
        (t("help_txt_fatal", "20 is fatal - and 2 days into an"), 0),
        (t("help_txt_fatal_2", "Ultimate/Mega stage just 5 can be."), 0),
        (t("help_txt_energy", "Energy fuels drills, fights and the"), 0),
        (t("help_txt_energy_2", "road; sleep refills it each night."), 0),
        (t("help_txt_ailments", "Two ailments: SICKNESS (filth or"), 0),
        (t("help_txt_ailments_2", "fat) takes the pill, free on F."), 0),
        (t("help_txt_ailments_3", "Battle INJURY takes H - free; a"), 0),
        (t("help_txt_ailments_4", "wound also closes with time. Both"), 0),
        (t("help_txt_ailments_5", "block fights and whisper to death."), 0),
        (t("help_txt_discipline", "p discipline - praise & scold:"), 1),
        (t("help_txt_discipline_2", "  scold a tantrum (+manners), praise"), 0),
        (t("help_txt_discipline_3", "  a proud win; ignored tantrums"), 0),
        (t("help_txt_discipline_4", "  cost a care mistake"), 0),
        (t("help_txt_alarms", "Alarms count the urgency: one beep"), 0),
        (t("help_txt_alarms_2", "routine, two a mess, three urgent."), 0),
        ("", 0),
        (t("help_txt_explore", "EXPLORE"), 2),
        (t("help_txt_battle", "m battle - fight a matched rival:"), 1),
        (t("help_txt_battle_2", "  a real bout (wins, exp, training)"), 0),
        (t("help_txt_battle_3", "  but no purse; costs 5 energy (10"), 0),
        (t("help_txt_battle_4", "  in the tank to start)"), 0),
        (t("help_txt_rival", "  every 3rd bout your named RIVAL"), 0),
        (t("help_txt_rival_2", "  answers - the feud's score lives"), 0),
        (t("help_txt_rival_3", "  on the datacore PERSON page"), 0),
        (t("help_txt_adv", "a adventure - head out on the road"), 1),
        (t("help_txt_adv_2", "  cross a zone, fell its boss, then"), 0),
        (t("help_txt_adv_3", "  rest in towns, find loot; towns"), 0),
        (t("help_txt_adv_4", "  sell eggs, map clears unlock them"), 0),
        (t("help_txt_drop", "  beaten foes can DROP their goods -"), 0),
        (t("help_txt_drop_2", "  bosses guard the rarest relics"), 0),
        (t("help_txt_raid", "r raid - the community boss: fight"), 1),
        (t("help_txt_raid_2", "  10-round volleys, break the shared"), 0),
        (t("help_txt_raid_3", "  pool together, claim the purse"), 0),
        (t("help_txt_cup", "u cup - hourly tournaments; win"), 1),
        (t("help_txt_cup_2", "  trophies to unlock new eggs; a"), 0),
        (t("help_txt_cup_3", "  champion banks the cup's own prize"), 0),
        (t("help_txt_lobby", "l lobby - go online: chat, and"), 1),
        (t("help_txt_lobby_2", "  battle / jogress other players"), 0),
        ("", 0),
        (t("help_txt_grow", "GROW"), 2),
        (t("help_txt_grow_1", "Eggs hatch, then evolve by HOW you"), 0),
        (t("help_txt_grow_2", "raise them - care, train, battles."), 0),
        (t("help_txt_grow_3", "Each egg has its own line to a Mega."), 0),
        (t("help_txt_train", "t train - time the strike: PERFECT"), 1),
        (t("help_txt_train_2", "  locks the power form your lobby"), 0),
        (t("help_txt_train_3", "  rivals will face"), 0),
        (t("help_txt_dna", "x DNA - steer the next evolution:"), 1),
        (t("help_txt_dna_2", "  wager bits, mash to bank a Field,"), 0),
        (t("help_txt_dna_3", "  charge ONE Field to its threshold;"), 0),
        (t("help_txt_dna_4", "  the next evolution takes that road"), 0),
        (t("help_txt_datacore", "d datacore - the pet's data book"), 1),
        (t("help_txt_datacore_2", "  ENTER on its trophy page opens the"), 0),
        (t("help_txt_datacore_3", "  ALBUM - every species, in dex order"), 0),
        (t("help_txt_legacy", "  on its LEGACY page, the HALL OF"), 0),
        (t("help_txt_legacy_2", "  MEMORY - every elder, remembered"), 0),
        (t("help_txt_egg_guide", "e egg guide - every egg + what"), 1),
        (t("help_txt_egg_guide_2", "  earns it, with live progress"), 0),
        ("", 0),
        (t("help_txt_manage", "MANAGE"), 2),
        (t("help_txt_shop", "s shop   b bag   n scenes"), 1),
        (t("help_txt_shop_2", "  the shop's last tab sells HONORS -"), 0),
        (t("help_txt_shop_3", "  titles that ride your status card"), 0),
        (t("help_txt_capsule", "  a CAPSULE opens into a surprise,"), 0),
        (t("help_txt_capsule_2", "  finer on festival days"), 0),
        (t("help_txt_opts", "g options   i report a bug   q quit"), 1),
        (t("help_txt_opts_2", "  themes, sound, cloud sync, your"), 0),
        (t("help_txt_opts_3", "  account, updates, every key"), 0),
        (t("help_txt_guide", "? this guide, any time you're home"), 1),
        (t("help_txt_guide_2", "SPACE doubles ENTER on most screens;"), 0),
        (t("help_txt_guide_3", "PgUp/PgDn leap through long lists."), 0),
        ("", 0),
        (t("help_txt_grave", "LEGACY"), 2),
        (t("help_txt_grave_1", "Neglect, hunger, sickness or age"), 0),
        (t("help_txt_grave_2", "take it in the end. The grave asks"), 0),
        (t("help_txt_grave_3", "what carries to the next one:"), 0),
        (t("help_txt_grave_4", "E grave os dados para o herdeiro"), 1),
        (t("help_txt_grave_5", "B guarde o bônus de cuidados"), 1),
        (t("help_txt_grave_6", "Only one etch may stand: if data is"), 0),
        (t("help_txt_grave_7", "already banked, E takes the new one,"), 0),
        (t("help_txt_grave_8", "K keeps the elder's."), 0),
        (t("help_txt_grave_9", "n starts the next egg."), 1),
        ("", 0),
        (t("help_txt_tips", "TIPS"), 2),
        (t("help_txt_tips_1", "Feed when hungry, clean the poop,"), 0),
        (t("help_txt_tips_2", "and let it sleep at night. Win cups,"), 0),
        (t("help_txt_tips_3", "fell raids, link with tamers, play a"), 0),
        (t("help_txt_tips_4", "festival - every egg is earned."), 0),
    ]
    return res

class HelpPanel:
    def __init__(self, pet: Any) -> None:
        self.pet = pet
        self.top = 0
        self.frame_i = 0
        self.msg = t("help_msg_intro", "Como jogar tuipet.")

    def anim(self) -> None:
        self.frame_i += 1

    def strip(self) -> Any:
        return menu.hints(("↑↓", t("help_hint_scroll", "scroll")), ("ESC", t("help_hint_out", "out")))

    def _max_top(self) -> Any:
        return max(0, len(get_help()) - VIS)

    def key(self, k: Any) -> Any:
        if k in ("up", "k"):
            self.top = max(0, self.top - 1)
        elif k in ("down", "j"):
            self.top = min(self._max_top(), self.top + 1)
        elif k == "pageup":                  # page jumps, lobby-chat style
            self.top = max(0, self.top - (VIS - 1))
        elif k == "pagedown":
            self.top = min(self._max_top(), self.top + (VIS - 1))
        elif k in ("escape", "question_mark"):
            # ? (the opening key) also closes; q now falls through to the
            # global save-and-quit like every other screen -- help was the
            # one panel where q meant something else (tidy audit 2026-07-18)
            return ("done", None)
        return None

    def _more_cue(self) -> Any:
        """A scroll affordance for the footer -- it says THERE IS more (the
        message strip already says HOW to move), so the two never echo."""
        up, dn = self.top > 0, self.top < self._max_top()
        if up and dn:
            return t("help_more_both", "▲▼ more")
        if dn:
            return t("help_more_below", "▼ more below")
        if up:
            return t("help_more_above", "▲ more above")
        return ""

    def text(self) -> Any:
        HELP = get_help()
        self.top = max(0, min(self.top, self._max_top()))
        pos = "%d-%d/%d" % (self.top + 1, min(self.top + VIS, len(HELP)), len(HELP))
        out = menu.header(t("help_hdr_help", "HELP"), pos)
        for text, kind in HELP[self.top:self.top + VIS]:
            style = INK_B if kind == 2 else (INK if kind == 1 else DIM)
            out.append((text or " ") + "\n", style=style)
        out.append_text(menu.footer(self._more_cue()))
        return out

# module-level alias so tests can 'from helpscreen import HELP'
HELP = get_help()
