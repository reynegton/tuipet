import ast

with open("src/tuipet/ui/screens/adventurescreen.py", "r") as f:
    tree = ast.parse(f.read())

render_methods = [
    "_rows", "_road_bg", "_jx", "_condition_rows", "_march_frame", 
    "_standing_frame", "_heal_frame", "_nap_frame", "_refuse_frame", 
    "_glint_frame", "_held_icon", "_scene_frame", "_hazard_frame", 
    "_pulse_frame", "_parade_frame", "_gate_frame", "_teleport_frame", 
    "_summary_frame"
]

total = 0
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "AdventurePanel":
        for subnode in node.body:
            if isinstance(subnode, ast.FunctionDef) and subnode.name in render_methods:
                total += (subnode.end_lineno - subnode.lineno)

print("Renderer lines:", total)
