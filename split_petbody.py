import ast
import os

with open("src/tuipet/core/petbody.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/core/petbody.py", "r") as f:
    tree = ast.parse(f.read())

class_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BodyMixin')

categories = {
    "sleep": ["_tick_asleep", "_tick_bedtime", "_tick_sleep_pressure", "_fall_asleep", "_wake", "_disturbed", "_near_bedtime", "_in_sleep_window", "_sleep_inc", "_calc_to_nap"],
    "mortality": ["_check_death_caps", "_tick_mortality", "_die"],
    "digestion": ["_tick_hunger", "_add_filth", "_start_poop", "_do_poop", "_filth_effects"],
    "growth": ["_tick_growth", "_tick_egg", "_birthday"],
    "autocare": ["_tick_auto_care"],
    "mind": ["_tick_mood_discipline", "_check_discipline_call", "_check_gift_call", "_special_idle", "_inc_mistake"]
}

all_names = [name for names in categories.values() for name in names]

funcs = {cat: [] for cat in categories}
for node in class_node.body:
    if isinstance(node, ast.FunctionDef) and node.name in all_names:
        body = get_node_text(node)
        
        # Replace signature self
        body = body.replace(f"def {node.name}(self", f"def {node.name}(pet")
        
        # Replace getattr/hasattr/setattr
        body = body.replace("getattr(self", "getattr(pet")
        body = body.replace("hasattr(self", "hasattr(pet")
        body = body.replace("setattr(self", "setattr(pet")
        
        # Dedent
        dedented = []
        for line in body.split('\n'):
            if line.startswith('    '):
                dedented.append(line[4:])
            else:
                dedented.append(line)
        
        # Replace self. with pet.
        text = "\n".join(dedented).replace("self.", "pet.")
        
        # Find category
        for cat, names in categories.items():
            if node.name in names:
                funcs[cat].append(text)
                break

os.makedirs("src/tuipet/core/pet/body", exist_ok=True)

for cat in categories:
    with open(f"src/tuipet/core/pet/body/{cat}.py", "w") as f:
        f.write("import random\nimport time\nimport math\n")
        f.write("import tuipet.data.loaders.data as data\n")
        f.write("import tuipet.utils.sound as sound\n")
        f.write("import tuipet.core.shop as shop\n")
        f.write("import tuipet.core.evolution as evolution\n")
        f.write("import tuipet.core.lines as lines_mod\n")
        f.write("from tuipet.core.petbase import *\n\n")
        for text in funcs[cat]:
            f.write(text + "\n\n")

# Re-write petbody.py bodies
replacements = []
for node in class_node.body:
    if isinstance(node, ast.FunctionDef) and node.name in all_names:
        args = [arg.arg for arg in node.args.args]
        if args[0] == 'self': args = args[1:]
        args_str = ", ".join(args)
        
        original = get_node_text(node)
        sig = original.split(":\n")[0] if ":\n" in original else original.split(":")[0]
        
        pass_args = "self" + (", " + args_str if args_str else "")
        
        cat = next(c for c, n in categories.items() if node.name in n)
        new_body = f"        return {cat}.{node.name}({pass_args})\n"
        
        replacements.append((node.lineno - 1, node.end_lineno, sig + ":\n" + new_body))

for start, end, new_code in reversed(replacements):
    lines[start:end] = [new_code]

with open("src/tuipet/core/petbody.py", "w") as f:
    # Add imports at the top
    import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("class BodyMixin"):
            import_idx = i
            break
    lines.insert(import_idx, "import tuipet.core.pet.body.sleep as sleep\n")
    lines.insert(import_idx, "import tuipet.core.pet.body.mortality as mortality\n")
    lines.insert(import_idx, "import tuipet.core.pet.body.digestion as digestion\n")
    lines.insert(import_idx, "import tuipet.core.pet.body.growth as growth\n")
    lines.insert(import_idx, "import tuipet.core.pet.body.autocare as autocare\n")
    lines.insert(import_idx, "import tuipet.core.pet.body.mind as mind\n")
    f.writelines(lines)

with open("src/tuipet/core/pet/body/__init__.py", "w") as f:
    for cat in categories:
        f.write(f"from .{cat} import *\n")

print("Created body submodules and updated petbody.py")
