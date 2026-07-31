import ast
import os

with open("src/tuipet/ui/screens/adventurescreen.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/ui/screens/adventurescreen.py", "r") as f:
    tree = ast.parse(f.read())

mixins = {
    "renderer": [
        "_rows", "_road_bg", "_jx", "_condition_rows", "_march_frame", 
        "_standing_frame", "_heal_frame", "_nap_frame", "_refuse_frame", 
        "_glint_frame", "_held_icon", "_scene_frame", "_hazard_frame", 
        "_pulse_frame", "_parade_frame", "_gate_frame", "_teleport_frame", 
        "_summary_frame", "strip"
    ],
    "logic": [
        "_advance", "_use_transport", "_dig", "_find_icon", "_scene_tick", 
        "_hazard_tick", "_lock_dig", "_start_battle", "_start_boss", 
        "_battle_done", "_bits_tail", "_town_done", "_go_home", "_outcome_word"
    ]
}

core_methods = ["__init__", "anim", "key", "text"]

header_nodes = []
zone_pick_node = None
adv_panel_node = None

for node in tree.body:
    if isinstance(node, ast.ClassDef):
        if node.name == "AdventurePanel":
            adv_panel_node = node
        elif node.name == "ZonePickPanel":
            zone_pick_node = get_node_text(node)
    else:
        # includes imports, constants
        header_nodes.append(get_node_text(node))

header = "".join(header_nodes)

funcs = {cat: [] for cat in mixins}
core_funcs = []
for node in adv_panel_node.body:
    if isinstance(node, ast.FunctionDef):
        matched = False
        for cat, names in mixins.items():
            if node.name in names:
                funcs[cat].append(get_node_text(node))
                matched = True
                break
        if not matched:
            core_funcs.append(get_node_text(node))

os.makedirs("src/tuipet/ui/screens/adventure", exist_ok=True)

with open("src/tuipet/ui/screens/adventure/renderer.py", "w") as f:
    f.write(header + "\n")
    f.write("class AdventureRendererMixin:\n")
    for text in funcs["renderer"]:
        # Indent properly
        f.write("    " + text.replace("\n", "\n    ").strip() + "\n\n")

with open("src/tuipet/ui/screens/adventure/logic.py", "w") as f:
    f.write(header + "\n")
    f.write("class AdventureLogicMixin:\n")
    for text in funcs["logic"]:
        f.write("    " + text.replace("\n", "\n    ").strip() + "\n\n")

with open("src/tuipet/ui/screens/adventure/panel.py", "w") as f:
    f.write(header + "\n")
    f.write("from .renderer import AdventureRendererMixin\n")
    f.write("from .logic import AdventureLogicMixin\n\n")
    f.write("class AdventurePanel(AdventureRendererMixin, AdventureLogicMixin):\n")
    for text in core_funcs:
        f.write("    " + text.replace("\n", "\n    ").strip() + "\n\n")

with open("src/tuipet/ui/screens/adventure/zone_pick.py", "w") as f:
    f.write(header + "\n")
    f.write(zone_pick_node + "\n\n")

with open("src/tuipet/ui/screens/adventure/__init__.py", "w") as f:
    f.write("from .panel import AdventurePanel\n")
    f.write("from .zone_pick import ZonePickPanel\n")

print("Created adventure submodules.")
