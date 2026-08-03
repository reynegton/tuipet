import sys
with open('src/tuipet/appactions/care_actions.py') as f:
    t = f.read()

funcs = """
    def action_sleep(self):
            self._do(self.pet.toggle_sleep())

    def action_assist(self):
            import tuipet.ui.screens.assistscreen as assistscreen
            self._open_mode(assistscreen.AssistPanel(self.pet), self._after_assist)

    def _after_assist(self, msg=None):
            if msg:
                self.flash(msg)
            self.repaint()
"""
t = t.replace('class CareActionsMixin:', 'class CareActionsMixin:' + funcs)
with open('src/tuipet/appactions/care_actions.py', 'w') as f:
    f.write(t)
