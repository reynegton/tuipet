# VISUAL AUDIT — 2026-07-25

Joel (overnight order): *"do a full blown visual audit and polish. make
sure all animations are wired in correctly."*  Method: run the system —
soak batteries through the REAL compositors, no grepping for wiring (the
E4 lesson: variable call sites hide fx names from greps).  Shipped
v0.5.263; pins in `tests/test_visual_audit.py` (56).

## V1 — The crash-loop defense crashed  ✅ FIXED

`record_for` exists so a save carrying an unknown num (data refresh,
downgrade, lobby peer on a newer roster) "wears the placeholder" instead
of dying in a relaunch loop — the .bak holds the same num, so a first-paint
crash is a crash *loop* (audit 2026-07-13).  But the stand-in sheet was
ONE copymon frame, and `data.ROLES` indexes up to 10 (`exhausted`), so
`_pose_rows` — the one role fetch with no index guard; `paint()` and
`bob_frame` both guard — raised IndexError on nearly every pose: the
first care fx, the sleep pose, the sick collapse, even idle's phase 1.
The defense held for exactly one frame.

**Fix, both levels**: `placeholder.FRAMES` pads to 11 slots (same rip,
every raw index answers — the geriatric +9 shuffle tops at 10 too), and
`_pose_rows` falls back like its siblings.  Pinned from three sides:
sheet width, the unknown-num pose sweep, and a monkeypatched short sheet
(defense in depth if the pad ever shrinks).

## Soaked clean (no action)

- **The fx engine**: all 15 home-screen kinds (eat/cheer/jeer/clean/spit/
  evolve/dying/dna_charge/play/poop/poopdance/yawn/losing/gift/inherit)
  × lit/dark/filthy/sick/Champion states — every one runs to completion
  through the real `advance_fx` + `_paint_fx` + `render_screen`, renders
  every step, and terminates (chains included: clean→cheer, evolve→cheer).
- **All 15 itemfx scripts** (Play/AngrySurprise/Interact×5/Study/Lift/
  Bathe/Shower/Ride/Bounce/Bandaging/PortToilet) complete and resolve
  into their canon end (cheer / jeer).
- **All 4 assistant visits** (clean/feed/strength/lights) complete; the
  feed/strength chain into the real eat plays through.
- **Role closure**: 1548 species × 24 roles × both phases resolve to
  renderable rows ≤16×16 — the sweep that found V1.
- **The hatch**: all ~30 crack beats of the 3s sequence paint, ending on
  the first Fresh frame.
- **The E4 un-swept moments** (REAL_VPET_ARC board, open since
  2026-07-23) — all five now verified:
  - *raid verdicts*: start `cheer`/`losing` (both soaked);
  - *jogress*: the converge→reveal scene produces 93 distinct frames over
    400 ticks (first measurement said 1 — that probe compared `.plain`,
    and bitmap scenes carry the image in styles; measured on markup);
  - *hatch*: beat-by-beat paint clean;
  - *lights*: assist-lights plays lit to its final beat, dark-room fx
    show nothing, filth unlit (v0.5.261);
  - *lobby outcomes*: `cheer`/`losing` on bout end.
  **E4 is CLOSED.**
- **The main-screen paint soak**: every anim role × sick/geriatric/
  4-pile/dark/asleep states × (Rookie / Champion / unknown-num / EMPTY
  cell), 24 ticks each — no crash, no out-of-window geometry.
- Panels: already armored by `test_panel_smoke` (every panel, key-walked);
  adventure/battle/cup theaters by their own audit suites.
