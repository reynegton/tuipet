import sys
with open('tests/test_dead_gate.py') as f:
    t = f.read()

t = t.replace('from tuipet.app import SERVIDOR_ONLINE', 'from tuipet import SERVIDOR_ONLINE')

with open('tests/test_dead_gate.py', 'w') as f:
    f.write(t)
