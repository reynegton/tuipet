import sys
with open('src/tuipet/appactions/system_actions.py') as f:
    t = f.read()

action_new_code = """
    def action_new(self):
            import tuipet.ui.screens.eggselectscreen as eggselectscreen
            if not self.pet.dead:
                persistence.bank_bonus_seed(self.pet.final_care_grade())
            persistence.snapshot_prev_gen(self.pet)
            gen = self.pet.generation + 1
            self._open_mode(eggselectscreen.EggSelectPanel(self.pet),
                            lambda et: self._hatch_new(et, gen))
"""

t = t.replace('class SystemActionsMixin:', 'class SystemActionsMixin:' + action_new_code)
with open('src/tuipet/appactions/system_actions.py', 'w') as f:
    f.write(t)
