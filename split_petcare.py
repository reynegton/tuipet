import ast
import os

with open("src/tuipet/core/petcare.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/core/petcare.py", "r") as f:
    tree = ast.parse(f.read())

class_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CareMixin')

funcs = {}
for node in class_node.body:
    if isinstance(node, ast.FunctionDef):
        funcs[node.name] = get_node_text(node).replace("def " + node.name + "(self", "def " + node.name + "(pet")
        # Fix indentation (dedent 1 level)
        dedented = []
        for line in funcs[node.name].split('\n'):
            if line.startswith('    '):
                dedented.append(line[4:])
            else:
                dedented.append(line)
        # Fix self references
        text = "\n".join(dedented).replace("self.", "pet.")
        # But wait, self might be passed as an argument.
        funcs[node.name] = text

hygiene_names = ["clean", "heal", "set_auto_care", "toggle_lights"]
feeding_names = ["can_feed", "feed", "feed_meat", "feed_pill"]
discipline_names = ["check_refused", "manners_refusal", "refuse_attack", "stop_travel_prob", "stop_travel_effects", "check_stop_travel", "check_compliant", "_open_praise", "_open_scold", "_calm_discipline_call", "praise", "scold"]
gifts_names = ["_pick_gift", "claim_gift"]

os.makedirs("src/tuipet/core/pet/care", exist_ok=True)

def write_module(filename, names):
    with open(f"src/tuipet/core/pet/care/{filename}", "w") as f:
        f.write("import random\nimport time\nimport math\n")
        f.write("import tuipet.data.loaders.data as data\n")
        f.write("import tuipet.utils.sound as sound\n")
        f.write("from tuipet.core.petbase import FullHunger, FullStrength\n\n")
        for name in names:
            if name in funcs:
                f.write(funcs[name] + "\n\n")

write_module("hygiene.py", hygiene_names)
write_module("feeding.py", feeding_names)
write_module("discipline.py", discipline_names)
write_module("gifts.py", gifts_names)

with open("src/tuipet/core/pet/care/__init__.py", "w") as f:
    f.write("from .hygiene import *\nfrom .feeding import *\nfrom .discipline import *\nfrom .gifts import *\n")

print("Created modules")
