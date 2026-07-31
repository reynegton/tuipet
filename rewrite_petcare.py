import ast

with open("src/tuipet/core/petcare.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/core/petcare.py", "r") as f:
    tree = ast.parse(f.read())

class_node = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'CareMixin')

hygiene_names = ["clean", "heal", "set_auto_care", "toggle_lights"]
feeding_names = ["can_feed", "feed", "feed_meat", "feed_pill"]
discipline_names = ["check_refused", "manners_refusal", "refuse_attack", "stop_travel_prob", "stop_travel_effects", "check_stop_travel", "check_compliant", "_open_praise", "_open_scold", "_calm_discipline_call", "praise", "scold"]
gifts_names = ["_pick_gift", "claim_gift"]

mapping = {}
for name in hygiene_names: mapping[name] = "hygiene"
for name in feeding_names: mapping[name] = "feeding"
for name in discipline_names: mapping[name] = "discipline"
for name in gifts_names: mapping[name] = "gifts"

replacements = []
for node in class_node.body:
    if isinstance(node, ast.FunctionDef) and node.name in mapping:
        mod = mapping[node.name]
        
        # Get signature parameters
        args = [arg.arg for arg in node.args.args]
        if args[0] == 'self': args = args[1:]
        
        args_str = ", ".join(args)
        
        # Keep original signature but replace body
        original = get_node_text(node)
        sig = original.split(":\n")[0] if ":\n" in original else original.split(":")[0]
        
        pass_args = "self" + (", " + args_str if args_str else "")
        new_body = f"    return {mod}.{node.name}({pass_args})\n"
        
        replacements.append((node.lineno - 1, node.end_lineno, sig + ":\n" + new_body))

# Apply backwards
for start, end, new_code in reversed(replacements):
    lines[start:end] = [new_code]

# Add imports to top
lines.insert(1, "from .pet.care import hygiene, feeding, discipline, gifts\n")

with open("src/tuipet/core/petcare.py", "w") as f:
    f.writelines(lines)

print("Rewrote petcare.py")
