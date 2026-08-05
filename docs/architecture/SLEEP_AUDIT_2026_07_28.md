# THE SLEEP AUDIT, ROUND 2 — 2026-07-28

Joel: *"sleep system needs to be audited."*

Method unchanged from round 1 (2026-07-25): **run the system, don't read
it**, on a REAL hatched line pet — driven the way the APP drives it (tick +
advance_hatch), stepped in true CLOCK-LAW minutes (1 world_second = 1
game-minute; the probe itself was wrong twice before the system was ever
measured, which is the whole argument for probes over readings).

Scope: everything that has touched sleep since round 1 — the mood burial,
the sleeping pill's lights deferral (0.5.288), the futon's deep doze, the
cold_shower retirement, the exhausted-nag gate (0.5.287).

## THE ONE FINDING — S3 (FIXED): the pill's lights debt outlived its sleep

The 0.5.288 fix made the pill OWE the room to its eat show
(`pending_lights_out`, applied by the app's fx-end hook).  Measured: wake
the pet DURING that show — the alarm, any disturb — and the debt stayed
armed, so the hook then darkened the room around an **awake** pet.

Fixed on both sides, one law: **the debt dies with the sleep it served.**
Every wake family clears it — `_wake` (natural/doze), the alarm
(petcare's inline wake), and `_die` — and the hook itself refuses to
darken a room whose pet is awake.  Pin:
`test_a_wake_cancels_the_pills_owed_lights_out`.

## CLEARED — measured, not believed

* **The natural night**: authored bedtime → asleep; a fully lit sleeping
  stretch bills its lights mistakes; the 7:00 wake restores the lights.
* **The recovery doze** holds a drained pet in the dark to HALF tank; the
  **futon** deepens it to FULL and its flag is spent on wake.
* **The pill** sleeps NOW, keeps the room lit, and owes the switch to the
  show — the 0.5.288 ordering intact.
* **The sleep-exempt set** after the cold_shower cut is exactly
  {music_player, sleeping_pill, futon}; everything else disturbs.
* **The exhausted nag** stays quiet on a sleeper (0.5.287 intact).
* **Every sleep flavor round-trips** the save whole: night sleep, nap,
  futon doze — asleep/nap/futon_doze/lights/awake_lapse all survive.
* **The wake roll survived the mood burial**: mornings still vary.

Ships as **v0.5.301**.
