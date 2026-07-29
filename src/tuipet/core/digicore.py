"""The DigiCore DATA MODEL -- every page, row and core computation
(Joel 2026-07-17: "can we modularize digicore now. polish it up").

digicorescreen.py renders and routes keys; THIS module decides what the
core says.  The statusbox law applies here too: a row may only show LIVE
data -- the move purged the dead "Spirit" label (the disposition trait
wears its own name now) and the Ailing row's injury fragment (the injury
system left 2026-07-16; is_injured() is hard False).
"""
from __future__ import annotations
import tuipet.data.loaders.data as data
import tuipet.core.petbase as _petbase
import tuipet.utils.backgrounds as _bgs
import tuipet.core.egg as _egg
from tuipet.core import evolution
from tuipet.core import lines
from tuipet.i18n.translator import t


DIGICORE_BASE_RATE = 14            # DigicoreBaseRate (config.csv col 1)
# ViewUtil.getDigicoreBackground field -> backdrop file suffix
_CORE_BG = {"": "digicoreN", "None": "digicoreN", "DragonsRoar": "digicoreDr",
            "DeepSaver": "digicoreDs", "JungleTrooper": "digicoreJt",
            "MetalEmpire": "digicoreMe", "NatureSpirit": "digicoreNsp",
            "WindGuardian": "digicoreWg", "NightmareSoldier": "digicoreNs",
            "DarkArea": "digicoreDa", "VirusBuster": "digicoreVb"}


def has_next(pet):
    """Is ANY onward evolution waiting?  Line pets read their line chart;
    corpus/legacy pets read the corpus graph.  (Digicore audit 2026-07-18:
    core_number checked the corpus alone, so 22 line parents whose onward
    rows are line-only — the jogress/X-road Megas — showed the LIFE meter
    while the same page's Meter row said an evolution neared.)"""
    if lines.active(pet):
        return bool(lines.evo_rows(pet))
    return bool(data.load_evolutions().get(pet.num))


def core_number(pet):
    """setupDigicore's meter: an evolution countdown while a normal evolution is
    pending, otherwise an AGE meter counting up toward the elder line (the
    lifespan denominator left with the clock -- DSprite mortality 2026-07-22:
    age is what kills now, so age is what the core counts).  Floors at 1."""
    base = DIGICORE_BASE_RATE
    growth = pet.STAGE_DURATION.get(pet.stage)
    # Mega's 9e9 is the "never auto-evolves" sentinel, not a growth clock:
    # counting it as pending froze the meter at its top for any Mega with
    # onward (jogress/X) rows -- the count-up this docstring promises a
    # final form never appeared (gameplay audit 2026-07-19)
    pending = (growth is not None and growth < 9e8
               and pet.stage_seconds < growth and has_next(pet))
    if pending:
        denom = round(growth / base) or 1
        n = int(base - pet.stage_seconds / denom)
    else:
        from tuipet.core.petbase import AGE_DAY, GERIATRIC_AGE_DAYS
        denom = round(GERIATRIC_AGE_DAYS * AGE_DAY / base) or 1
        n = int(pet.age_seconds / denom)
    return max(1, n)


def core_badge_key(pet):
    """setupDigicore's badge: the per-Digimon special core (digicoreMenuConfig,
    IconX while X-antibody; "null" hides it), else the X-state badges."""
    cfg = data.load_digicore_config().get(pet.num, {})
    x = getattr(pet, "x_antibody", "None")
    pick = cfg.get("icon_x") if x != "None" else cfg.get("icon")
    if pick == "hidden":
        return None
    if pick:
        return pick
    if x != "None":
        return "core_xreq"                      # Permanent (binary since the X slim)
    return "core_xnone"


def core_background(pet):
    """The core swirl backdrop by the highest CHARGED DNA field (DNA.getHighestDNA:
    strict max over the charged array, ties yield none) -- else the pet's own field."""
    field = pet.highest_dna() or pet.field
    frames = data.load_backgrounds().get(_CORE_BG.get(field, "digicoreN"))
    return frames[0] if frames else None


def silhouette(rows):
    """ViewUtil.getSilhouetteImage on 1-bit art: black the sprite's OPAQUE
    MASK.  Canon blackens every non-transparent pixel; our 1-bit equivalent is
    an exterior flood fill -- any '0' NOT reachable from outside the sprite is
    enclosed body and goes black, while real gaps (between wings, under arms)
    stay clear.  (The old per-row scanline fill bridged every concavity into
    one melted blob -- Joel: 'the shape is out of resolution', 2026-07-04.)"""
    if not rows:
        return rows
    w = max(len(r) for r in rows)
    g = [list(r.ljust(w, "0")) for r in rows]
    h = len(g)
    # flood the EXTERIOR from every border '0' (4-connected)
    stack = [(x, y) for x in range(w) for y in (0, h - 1) if g[y][x] == "0"]
    stack += [(x, y) for y in range(h) for x in (0, w - 1) if g[y][x] == "0"]
    outside = set(stack)
    while stack:
        x, y = stack.pop()
        for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
            if 0 <= nx < w and 0 <= ny < h and g[ny][nx] == "0" and (nx, ny) not in outside:
                outside.add((nx, ny))
                stack.append((nx, ny))
    return ["".join("0" if (x, y) in outside else "1" for x in range(w))
            for y in range(h)]


def ghost(mask, phase=0):
    """The teaser's unresolved-data look: the mask's CONTOUR stays crisp while
    the interior renders as a 50% dither (the evolve strobe's own idiom),
    shimmering with `phase`.  A solid 16px mask carries no shape information
    -- it read as a broken blob (Joel: 'the shape is out of resolution');
    canon's solid silhouette only works at 48px."""
    if not mask:
        return mask
    w = max(len(r) for r in mask)
    g = [r.ljust(w, "0") for r in mask]
    h = len(g)
    out = []
    for y in range(h):
        row = []
        for x in range(w):
            if g[y][x] != "1":
                row.append("0")
                continue
            edge = (x == 0 or y == 0 or x == w - 1 or y == h - 1
                    or g[y][x - 1] == "0" or g[y][x + 1] == "0"
                    or g[y - 1][x] == "0" or g[y + 1][x] == "0")
            row.append("1" if edge or (x + y + phase) % 2 == 0 else "0")
        out.append("".join(row))
    return out


def next_evolution(pet):
    """The silhouette's subject (getCurrentNaturalEvol first entry): the ready
    candidate first, else the closest one; None past growth / at a final form."""
    if pet.num == -1:
        # canon setupDigicore counts an EGG's hatch as its next evolution
        # (the chart holds Egg -> Fresh), so the gaze teases the hatchling --
        # it said "final form" over an egg (audit 2026-07-05)
        import tuipet.core.egg as egg_mod
        targets = egg_mod.hatch_targets(getattr(pet, "egg_type", 0))
        return targets[0] if targets else None
    div = evolution.divergence_target(pet)
    if div is not None:
        # an ARMED DNA divergence fires FIRST (_maybe_evolve checks the
        # steer before the chart), so the gaze must tease the steer's
        # target -- it promised a line future that would NOT happen
        # (gameplay audit B3, 2026-07-22)
        return div
    if lines.active(pet):
        rows = lines.evo_rows(pet)      # line chart: ready first, else fewest-unmet
        if not rows:
            return None
        return sorted(rows, key=lambda r: (not r[2], r[3]))[0][0]
    try:
        cands = sorted(evolution.candidates(pet), key=lambda c: (not c[2], -c[3]))
    except Exception:
        cands = []
    return cands[0][0] if cands else None


def _mins(s):
    s = int(max(0, s))
    if s < 3600:
        return f"{s // 60}m{s % 60:02d}s"
    if s < 86400:
        return f"{s // 3600}h{(s % 3600) // 60:02d}m"
    return f"{s // 86400}d{(s % 86400) // 3600:02d}h"


def _divergence_row(pet):
    """The armed DNA steer as a chart row -- (num, name, True, 0) -- or
    None while unarmed.  The hidden-evo mask is honored like any corpus
    row: the steer names its destination only once the album has seen it."""
    div = evolution.divergence_target(pet)
    if div is None:
        return None
    _, by = data.load_sprites()
    name = by.get(div, {}).get("name", "?")
    from tuipet import persistence as _p
    if data.load_requirements().get(div, {}).get("hidden_evo") \
            and not _p.album_seen(div):
        name = "???"
    return (div, name, True, 0)


def divergence_report(pet):
    """The armed steer's checklist (met, text) rows -- the EVOLVES detail
    for the divergence row.  lines.requirement_report would answer "not in
    this line" (true, and exactly the point): what fires this jump is the
    charge, so the sheet reports the charge."""
    field = pet.highest_dna()
    need = evolution.DIVERGE_NEED.get(pet.stage, 0)
    have = pet.dna_applied.get(field, 0)
    return [(True, t("digicore_diverge_armed", "{field} charge {have}/{need} — ARMED").format(field=field, have=have, need=need)),
            (None, t("digicore_steer_overrides", "the steer overrides the chart")),
            (None, t("digicore_charges_clear", "charges clear at every evolution"))]


def _evo_rows(pet):
    """The evolution line for the data book: (num, name, ready, unmet) per
    candidate, closest-first -- with an ARMED DNA divergence riding the top
    row, because that is what actually fires next (gameplay audit B3,
    2026-07-22: the page promised a line future the steer would override).
    unmet counts the failing checklist gates (evolution.requirement_report)
    -- the page shows it as distance-to-go.

    Canon shows the chart at EVERY stage -- DVPet's drawEvolutionMenu never
    gates on age, and setupDigicore counts hatching as the egg's own
    evolution (the "(too young)" stonewall was a pre-line-engine tuipet
    invention; Joel caught it 2026-07-10)."""
    if pet.num == -1:
        # an egg's next form is its hatchling; the multi-target mystery
        # digitama keeps its surprise (name masked, like hidden_evo)
        import tuipet.core.egg as egg_mod
        _, by = data.load_sprites()
        targets = egg_mod.hatch_targets(getattr(pet, "egg_type", 0))
        if not targets:
            return t("digicore_final_form_paren", "(final form)")
        if len(targets) > 1:
            return [(targets[0], "???", False, 0)]
        return [(t, by.get(t, {}).get("name", "?"), False, 0) for t in targets]
    armed = _divergence_row(pet)
    if lines.active(pet):
        # line pets: the line's own chart rows, in first-match order (the order
        # IS the information -- earlier rows win ties), with live unmet counts
        rows = lines.evo_rows(pet)
        if armed:
            # the steer tops the chart; the line rows stay below -- they
            # come BACK if another Field catches up and breaks the strict max
            return [armed] + [r for r in (rows or []) if r[0] != armed[0]]
        return rows or t("digicore_final_form_paren", "(final form)")
    try:
        # ready first, then HIGHEST fulfilled -- ascending put the form the
        # engine is LEAST likely to pick in the top "closest" row, against
        # the silhouette on the same screen (gameplay audit 2026-07-19)
        cands = sorted(evolution.candidates(pet), key=lambda c: (not c[2], -c[3]))
    except Exception:
        cands = []
    if not cands:
        return [armed] if armed else t("digicore_final_form_paren", "(final form)")
    rows = []
    from tuipet import persistence as _p
    reqs = data.load_requirements()
    for num, name, ready, dev in cands[:8]:
        unmet = sum(1 for met, _ in evolution.requirement_report(pet, num) if met is False)
        # HiddenEvolution (digicore audit 2026-07-06): canon's tree conceals
        # 130 flagged forms until FIRST reached -- the cross-generation album
        # is the reveal state (Evolution.setUnlocked).  The slot still shows
        # (position + distance-to-go intact), only the name is masked.
        if reqs.get(num, {}).get("hidden_evo") and not _p.album_seen(num):
            name = "???"
        rows.append((num, name, ready, unmet))
    if armed:
        rows = [armed] + [r for r in rows if r[0] != armed[0]]
    return rows


def _trophy_rows(pet):
    """The trophy room: this life's cups (label + the day they fell) topped
    by the career totals -- lifetime cups persist across generations."""
    from tuipet import tournament as _t
    from tuipet import persistence as _p
    # "This life" is exactly the 9-char label column -- it rendered flush
    # against its value ("This lifenone yet"; egg-stage audit 2026-07-05)
    rows = [(t("digicore_lbl_this_pet", "This pet"), "\u2605" * min(pet.trophies, 12) or t("digicore_val_none_yet", "none yet"))]
    try:
        career = len(_p.get_progress().get("tourneys", ()) or ())
    except Exception:
        career = 0
    rows.append((t("digicore_lbl_career", "Career"), t("digicore_val_career_cups", "{career} cup(s), all generations").format(career=career)))
    # the collection long game ("ultimate v-pet" arc 2026-07-07): every raised
    # form lands in the cross-generation album; divergence/jogress/eggs are
    # the roads to the rest of the corpus
    try:
        seen = len(_p.get_progress().get("album", ()) or ())
    except Exception:
        seen = 0
    # the denominator must count what the numerator can actually REACH: the dex
    # carries 329 duplicate rows (one species can sit on several device pages --
    # five Petitmon, seven Omnimon MM), and album_add stores the CANONICAL num,
    # so `seen` tops out at the canonical count.  Comparing it to the raw row
    # count showed 1218/1547: an album that could never be completed, however
    # perfectly you played (roster audit 2026-07-14, Joel: "we have duplicate
    # mons??").  album_roster() = that canonical set, shared with the album
    # screen's pages (the book this count fronts for).
    total = len(data.album_roster())
    rows.append((t("digicore_lbl_album", "Album"), t("digicore_val_album_disc", "{seen}/{total} discovered").format(seen=seen, total=total)))
    # the Maps row became the Raids row (BASIC VPET 2026-07-16): adventure
    # left, and felled community bosses gate the old MapComplete eggs now
    try:
        felled = int(_p.get_progress().get("raids", 0) or 0)
    except Exception:
        felled = 0
    rows.append((t("digicore_lbl_raids", "Raids"), t("digicore_val_raids_felled", "{felled} raid bosses felled").format(felled=felled)))
    won = sorted((getattr(pet, "trophies_won", None) or {}).items())
    for tid, season in won[:4]:                     # keep the page at 9 rows max
        # trophy_name speaks every id space -- town cups included
        rows.append((_t.trophy_name(tid)[:12], season))   # (was 5: Maps row joined)
    if len(won) > 4:
        rows.append(("…", t("digicore_val_more", "+{count} more").format(count=len(won) - 4)))
    return rows


def _legacy_rows():
    """The LEGACY page: every retired generation's headstone, newest first --
    they were banked by snapshot_prev_gen and never shown (sweep 2026-07-14).
    Value budget is 30 cols (40 - the 9-char label gutter)."""
    from tuipet import persistence as _p
    try:
        elders = list(_p.load_settings().get("progress", {}).get("legacy", []))
    except Exception:
        elders = []
    if not elders:
        return [("—", t("digicore_no_elders_1", "no elders yet — this pet")), ("", t("digicore_no_elders_2", "is writing generation one"))]
    rows = []
    for r in reversed(elders[-8:]):                 # 8 headstones + the more row = 9
        # _mins: the book's own REAL-time formatter, same unit as the STATUS
        # Age row and the memorial epitaph.  (The old //1440 mis-cited the
        # clock law -- 1440 is game-MINUTES per game-day, not seconds -- and
        # inflated every headstone 60x: a 4.5-day life read "270d";
        # digicore audit 2026-07-19.)
        age = _mins(float(r.get("age", 0)))
        fate = "†" if r.get("dead") else ""         # fell vs retired to the next egg
        val = f"{str(r.get('name', '?'))[:12]} {r.get('stage', '?')} {age}{fate}"
        rows.append((f"gen {r.get('gen', '?')}", val[:30]))
    if len(elders) > 8:
        rows.append(("…", t("digicore_more_remembered", "+{count} more remembered").format(count=len(elders) - 8)))
    return rows


def build_pages(pet):
    appetite = [t("digicore_glutton_picky", "picky"), t("digicore_glutton_normal", "normal"), t("digicore_glutton_greedy", "greedy")][pet._glutton() + 1]
    temperament = [t("digicore_temp_mellow", "mellow"), t("digicore_temp_steady", "steady"), t("digicore_temp_restless", "restless")][pet._restless() + 1]
    disp = [t("digicore_disp_sour", "sour"), t("digicore_disp_even", "even"), t("digicore_disp_sunny", "sunny")][pet._disposition() + 1]
    status = [
        (t("digicore_lbl_name", "Name"), pet.name or t("digicore_val_dash", "—")),
        # an egg has no dex number yet -- "#-1" leaked the internal sentinel
        # (egg-stage audit 2026-07-05)
        (t("digicore_lbl_no", "No."), t("digicore_val_dash", "—") if pet.num < 0 else f"#{pet.num}"), (t("digicore_lbl_stage", "Stage"), pet.stage),
        (t("digicore_lbl_attrib", "Attrib"), pet.attribute), (t("digicore_lbl_field", "Field"), data.pretty_field(pet.field) or t("digicore_val_dash", "—")),
        (t("digicore_lbl_gen", "Gen"), str(pet.generation)),
        # (the "Life Xd left" row left with the lifespan clock -- DSprite
        # mortality 2026-07-22: nothing counts down anymore, Age counts up)
        (t("digicore_lbl_age", "Age"), _mins(pet.age_seconds)),
        (t("digicore_lbl_battles", "Battles"), f"{pet.wins}W / {pet.battles} · {pet.bits}b"),
    ]
    # the POWER page is the BATTLE ledger (framing fixed, gameplay polish
    # #17 2026-07-22): the Va/D/Vi attribute powers stopped gating growth
    # when those checks left evolution.check() -- lines never read them
    # either.  What still feeds evolution here is Level (LV gates), KO6 and
    # Effort; the attribute trio, Form and Training feed the FIGHT
    # (hit_chance / roll_damage).  The weight/bits/battles bookkeeping
    # moved beside its kin (weight -> CONDITION; battles/bits -> STATUS;
    # trophies have their own page).
    power = [
        (t("digicore_lbl_vaccine", "Vaccine"), str(pet.vaccine)), (t("digicore_lbl_data", "Data"), str(pet.data_power)),
        (t("digicore_lbl_virus", "Virus"), str(pet.virus)), (t("digicore_lbl_effort", "Effort"), f"{pet.strength}/4"),
        (t("digicore_lbl_form", "Form"), getattr(pet, "saved_hit_type", t("digicore_val_normal", "normal"))),
        (t("digicore_lbl_level", "Level"), f"{lines._pet_level(pet)} ({getattr(pet, 'exp', 0)} exp)"),
        # both training terms of the hit formula on one row (Joel
        # 2026-07-23 "is there a stat somewhere i can see that shows
        # this?"): lifetime (the +20% term, never resets) · this stage
        # (the +10% term AND the TR evolution gate; resets on evolve) --
        # stage_trainings was live everywhere but visible nowhere.
        # Named TRAINING, not "Drills", since 2026-07-25: a bout feeds
        # both counters now (+2), so a row that says drills would be
        # naming one of its two sources (the liveness law).
        (t("digicore_lbl_training", "Training"), t("digicore_val_this_stage", "{total} · {stage} this stage").format(total=getattr(pet, 'total_trainings', 0), stage=getattr(pet, 'stage_trainings', 0))),
        (t("digicore_lbl_ko6", "KO6"), t("digicore_val_mega_felled", "{kills} Mega felled").format(kills=pet.mega_kills)),
    ]
    if pet.x_antibody != "None":
        power.append((t("digicore_lbl_xanti", "X-Anti"), pet.x_antibody))   # keep the page at its 9-row max
    # (the Likes/Dislikes clock rows left with the timeRanks system --
    # BASIC VPET 2026-07-17)
    person = [
        # ("Spirit" was the dead spirit system's word -- the row shows the
        # DISPOSITION trait, which is alive; label polish 2026-07-17)
        (t("digicore_lbl_type", "Type"), pet.personality()), (t("digicore_lbl_nature", "Nature"), disp),
        (t("digicore_lbl_appetite", "Appetite"), appetite), (t("digicore_lbl_pace", "Pace"), temperament),
        # the manners gauge, LIVE again (canon restoration B, 2026-07-23)
        (t("digicore_lbl_manners", "Manners"), f"{getattr(pet, 'obedience', 0)}/{_petbase.MAX_OBEDIENCE}"),
    ]
    if getattr(pet, "rival_name", ""):
        # the named rival's head-to-head (Joel 2026-07-26) — appears once
        # the first challenge mints the tamer, dies with the generation
        person.append((t("digicore_lbl_rival", "Rival"),
                       f"{pet.rival_name} · {pet.rival_wins}W-{pet.rival_losses}L"))
    core = data.load_digicore_icons().get(pet.num)
    if core:
        person.append((t("digicore_lbl_core", "Core"), f"{chr(0x25C6)} {core}"))   # DVPet digicore badge
    return [
        (t("digicore_pg_status", "STATUS"), status),
        (t("digicore_pg_power", "POWER"), power),
        (t("digicore_pg_condition", "CONDITION"), [
            (t("digicore_lbl_hunger", "Hunger"), f"{pet.hunger}/4"), (t("digicore_lbl_energy", "Energy"), f"{int(pet.energy)}/{pet.max_energy}"),
            (t("digicore_lbl_weight", "Weight"), f"{pet.weight}g"),
            # two ailments, two words: INJURY returned with the canon
            # restoration (2026-07-23) but this row kept the removal-era
            # sick-only read -- the data book could never say "hurt".
            # Sick outranks hurt, same as the feed cursor (audit 2026-07-25)
            (t("digicore_lbl_ailing", "Ailing"), t("digicore_val_sick", "sick") if pet.sick else
             (t("digicore_val_hurt", "hurt") if pet.is_injured() else t("digicore_val_no", "no"))),
            # (no nutrition row: the macro system was REMOVED 2026-07-16 --
            # its fields are frozen starter values; cards only show LIVE data)
            (t("digicore_lbl_poop", "Poop"), str(pet.poop)),
            (t("digicore_lbl_care", "Care"), t("digicore_val_care_stage", "{mistakes} this stage").format(mistakes=pet.care_mistakes)),
            (t("digicore_lbl_disturb", "Disturb"), str(pet.disturb)),
        ]),
        (t("digicore_pg_home", "HOME"), [
            # the household page (data-page polish 2026-07-17): the scene
            # honors the E pick.  (The staple-fixture stock rows left with
            # the props: strict-DSprite items, 2026-07-17.)
            (t("digicore_lbl_scene", "Scene"), _bgs.name(getattr(pet, "bg_pick", "")
                                or _bgs.scene_for_egg(getattr(pet, "egg_type", 0)))),
            (t("digicore_lbl_egg", "Egg"), _egg.hatch_name(getattr(pet, "egg_type", 0))),
            (t("digicore_lbl_helper", "Helper"), t("digicore_val_hired", "hired") if getattr(pet, "auto_care", False) else t("digicore_val_off", "off")),
        ]),
        (t("digicore_pg_person", "PERSON"), person),
        (t("digicore_pg_trophies", "TROPHIES"), _trophy_rows(pet)),
        (t("digicore_pg_legacy", "LEGACY"), _legacy_rows()),
        (t("digicore_pg_evolves", "EVOLVES"), _evo_rows(pet)),
    ]


