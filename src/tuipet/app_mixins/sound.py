from __future__ import annotations
import tuipet.data.loaders.data as data
import tuipet.utils.persistence as persistence
from tuipet.i18n.translator import t
import tuipet.utils.sound as sound

class SoundMixin:
    def beep(self, name=None, bell=True):
            if not self.sound:
                return
            if name and sound.play(name):
                return
            if bell:
                self.bell()

    def alarm_pattern(self, n):
            """The care alarm's COUNT is the message (gameplay polish #8,
            2026-07-22): every need rang the identical single alarm, so by ear
            a player couldn't tell hunger from sickness from across the room.
            Same wav — no new-sample taste calls — differentiated by pattern:
            1× routine (hunger/effort/lights), 2× cleaning, 3× urgent
            (sick/exhausted/frail).  Extra rings queue onto the 10 Hz frame
            clock, 4 frames apart."""
            self.beep("alarm")
            if n > 1:
                q = getattr(self, "_beep_q", None)
                if q is None:
                    q = self._beep_q = []
                q.extend([4 * i for i in range(1, n)])

    def _alarm_urgency(self, p):
            """How many rings the standing need deserves (the _need_message
            precedence, classed): 3 = lethal-adjacent, 2 = the mess, 1 = routine."""
            if p.sick or p.is_injured() or p.energy <= 0 or p.is_frail():
                return 3
            if p.poop >= 3:
                return 2
            return 1

    def _toggle_sound(self):
            """The options-menu sound switch (the panel carries its own message)."""
            self.sound = not self.sound
            _save_sound(self.sound)
            if self.sound:
                self.bell()

