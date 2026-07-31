import ast
import os

with open("src/tuipet/core/pet/__init__.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/core/pet/__init__.py", "r") as f:
    tree = ast.parse(f.read())

class_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Pet')

categories = {
    "stats": ["_set_weight", "_set_calories", "_set_obedience", "_set_enthusiasm", "_set_energy", "_base_weight", "stomach_capacity", "_weight_limit_penalty", "energy_pct"],
    "evolution_state": ["new_egg", "from_num", "_hatch_into_fresh", "advance_hatch", "_maybe_evolve", "_become", "evolve_to", "_swap_form", "mode_change", "can_mode_change", "_set_xantibody"],
    "conditions": ["needs_care", "needs_attention", "near_bedtime", "is_fatigued", "is_injured", "is_frail", "is_freezing", "is_overheating", "condition", "status_word", "current_mood", "_is_failed_form", "ideal_temp", "age_days"],
    "traits": ["_rand_personality_traits", "_rand_on_champion", "_disposition", "_glutton", "_restless", "personality", "_personality_mood"],
    "intervals": ["_hunger_interval", "_poop_interval", "_strength_interval", "_growth_period"],
    "memory_state": ["save_from_death", "make_memory", "final_care_grade"],
    "misc": ["background", "pick_background", "_guard", "_set_anim", "good_nutrition", "_species_food", "_poop_size", "_phys"]
}

all_names = [name for names in categories.values() for name in names]

funcs = {cat: [] for cat in categories}
for node in class_node.body:
    if isinstance(node, ast.FunctionDef) and node.name in all_names:
        body = get_node_text(node)
        
        # Determine if it's a classmethod
        is_cls = any(isinstance(d, ast.Name) and d.id == 'classmethod' for d in node.decorator_list)
        
        # Replace signature self or cls with pet or cls
        if is_cls:
            pass # Keep cls
        else:
            body = body.replace(f"def {node.name}(self", f"def {node.name}(pet")
            
            # Replace getattr/hasattr/setattr
            body = body.replace("getattr(self", "getattr(pet")
            body = body.replace("hasattr(self", "hasattr(pet")
            body = body.replace("setattr(self", "setattr(pet")
            
            # Replace type(self)
            body = body.replace("type(self)", "type(pet)")
        
        # Remove @classmethod from the text as it will be a pure function
        if is_cls:
            body = "\n".join([line for line in body.split('\n') if not line.strip().startswith('@classmethod')])
        
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

for cat in categories:
    with open(f"src/tuipet/core/pet/{cat}.py", "w") as f:
        f.write("import random\nimport time\nimport math\n")
        f.write("import tuipet.data.loaders.data as data\n")
        f.write("import tuipet.utils.sound as sound\n")
        f.write("import tuipet.core.shop as shop\n")
        f.write("import tuipet.core.evolution as evolution\n")
        f.write("import tuipet.core.lines as lines_mod\n")
        f.write("import tuipet.utils.backgrounds as backgrounds\n")
        f.write("import tuipet.utils.theme as theme\n")
        f.write("from tuipet.i18n.translator import t\n")
        f.write("from tuipet.core.petbase import *\n\n")
        for text in funcs[cat]:
            f.write(text + "\n\n")

# Re-write __init__.py bodies
replacements = []
for node in class_node.body:
    if isinstance(node, ast.FunctionDef) and node.name in all_names:
        is_cls = any(isinstance(d, ast.Name) and d.id == 'classmethod' for d in node.decorator_list)
        
        args = [arg.arg for arg in node.args.args]
        if args and args[0] in ('self', 'cls'): args = args[1:]
        args_str = ", ".join(args)
        
        original = get_node_text(node)
        sig_lines = []
        for line in original.split('\n'):
            sig_lines.append(line)
            if line.strip().endswith(':'):
                break
        sig = "\n".join(sig_lines)
        
        pass_args = ("cls" if is_cls else "self") + (", " + args_str if args_str else "")
        
        cat = next(c for c, n in categories.items() if node.name in n)
        new_body = f"        return {cat}.{node.name}({pass_args})\n"
        
        replacements.append((node.lineno - 1, node.end_lineno, sig + "\n" + new_body))

for start, end, new_code in reversed(replacements):
    lines[start:end] = [new_code]

with open("src/tuipet/core/pet/__init__.py", "w") as f:
    import_idx = 0
    for i, line in enumerate(lines):
        if line.startswith("class Pet"):
            import_idx = i
            break
    for cat in categories:
        lines.insert(import_idx, f"import tuipet.core.pet.{cat} as {cat}\n")
    f.writelines(lines)

print("Created pet submodules and updated __init__.py")
