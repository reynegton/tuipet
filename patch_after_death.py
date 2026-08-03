import sys
with open('src/tuipet/app_mixins/lifecycle.py') as f:
    t = f.read()
after_death = """
    def _after_death(self, result):
            if result == "new":
                self.action_new()
            else:
                self.repaint()
"""
t = t.replace('class LifecycleMixin:', 'class LifecycleMixin:' + after_death)
with open('src/tuipet/app_mixins/lifecycle.py', 'w') as f:
    f.write(t)
