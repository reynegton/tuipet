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
inventory_names = [
    "add_item", "take_item", "spend_bits", "_compensate_attrs", "use_item",
    "_crest_egg", "_energy_drink", "_snack", "_giga_meal", "_vitamin", "_bandage",
    "_caffeine", "_miracle_drink", "_cold_compress", "_textbook", "heal_bandage",
    "_attr_chip", "_dna_crystal", "_toy", "_deadly", "_junk", "_premium_meat",
    "_smart_potty", "_sleep_pill", "_alarm", "_time_gear", "_anti_evo", "_x_item",
    "_training_pack", "_revive_item", "stash_wild_memory", "peek_memory",
    "_inherit_memory", "_super_carrot", "_csv_snack", "_med_item", "_elixir",
    "_vitamin_g", "_gold_pill", "_supplement", "_board_game", "_computer_game",
    "_toy_oven", "_futon", "_x_program", "_textbook_lite", "_hedonism", "_evo_key",
    "_capsule", "_chocolate_egg"
]

for node in class_node.body:
    if isinstance(node, ast.FunctionDef) and node.name in inventory_names:
        body = get_node_text(node)
        
        # Replace signature self
        body = body.replace("def " + node.name + "(self", "def " + node.name + "(pet")
        
        # Replace getattr(self,
        body = body.replace("getattr(self", "getattr(pet")
        # Replace hasattr(self,
        body = body.replace("hasattr(self", "hasattr(pet")
        # Replace setattr(self,
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
        funcs[node.name] = text

# Write inventory.py
with open("src/tuipet/core/pet/care/inventory.py", "w") as f:
    f.write("import random\nimport time\nimport math\n")
    f.write("import tuipet.data.loaders.data as data\n")
    f.write("import tuipet.utils.sound as sound\n")
    f.write("from tuipet.core.petbase import *\n\n") # Just wildcard for safety with constants
    for name in inventory_names:
        if name in funcs:
            f.write(funcs[name] + "\n\n")

# Re-write petcare.py bodies
replacements = []
for node in class_node.body:
    if isinstance(node, ast.FunctionDef) and node.name in inventory_names:
        args = [arg.arg for arg in node.args.args]
        if args[0] == 'self': args = args[1:]
        args_str = ", ".join(args)
        
        original = get_node_text(node)
        sig = original.split(":\n")[0] if ":\n" in original else original.split(":")[0]
        
        pass_args = "self" + (", " + args_str if args_str else "")
        new_body = f"        return inventory.{node.name}({pass_args})\n"
        
        replacements.append((node.lineno - 1, node.end_lineno, sig + ":\n" + new_body))

for start, end, new_code in reversed(replacements):
    lines[start:end] = [new_code]

with open("src/tuipet/core/petcare.py", "w") as f:
    f.writelines(lines)

# Update __init__.py
with open("src/tuipet/core/pet/care/__init__.py", "a") as f:
    f.write("from .inventory import *\n")

print("Created inventory.py and updated petcare.py")
