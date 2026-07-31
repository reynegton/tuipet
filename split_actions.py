import ast
import os

with open("src/tuipet/appactions.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/appactions.py", "r") as f:
    tree = ast.parse(f.read())

mixins = {
    "care": ["action_feed", "action_heal", "action_clean", "action_lights", "action_discipline", "action_train"],
    "nav": ["action_adventure", "action_battle", "action_tournament", "action_dna", "action_core", "action_eggs", "action_shop", "action_album", "action_scenes", "_after_title"],
    "system": ["action_help", "action_options", "action_bug", "action_quit"]
}

app_node = None
header_nodes = []
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "ActionsMixin":
        app_node = node
    else:
        header_nodes.append(get_node_text(node))

header = "".join(header_nodes)

funcs = {cat: [] for cat in mixins}
core_funcs = []
for node in app_node.body:
    if isinstance(node, ast.FunctionDef):
        matched = False
        for cat, names in mixins.items():
            if node.name in names or any(node.name.startswith(f"_after_{n.split('_')[1]}") for n in names if '_' in n):
                funcs[cat].append(get_node_text(node))
                matched = True
                break
        if not matched:
            core_funcs.append(get_node_text(node))

os.makedirs("src/tuipet/appactions", exist_ok=True)

for cat in mixins:
    with open(f"src/tuipet/appactions/{cat}_actions.py", "w") as f:
        f.write("from __future__ import annotations\n")
        f.write("import tuipet.data.loaders.data as data\n")
        f.write("import tuipet.utils.persistence as persistence\n")
        f.write("from tuipet.i18n.translator import t\n")
        f.write("from tuipet.core.pet import Pet\n")
        f.write("import tuipet.ui.screens.lobbyscreen as lobbyscreen\n")
        f.write(f"class {cat.capitalize()}ActionsMixin:\n")
        for text in funcs[cat]:
            f.write("    " + text.replace("\n", "\n    ").strip() + "\n\n")

# Re-write appactions.py to just re-export and combine
with open("src/tuipet/appactions/__init__.py", "w") as f:
    f.write("from .care_actions import CareActionsMixin\n")
    f.write("from .nav_actions import NavActionsMixin\n")
    f.write("from .system_actions import SystemActionsMixin\n")

mixin_classes = ", ".join(f"{cat.capitalize()}ActionsMixin" for cat in mixins)
with open("src/tuipet/appactions.py", "w") as f:
    f.write(header)
    f.write("from tuipet.appactions import *\n\n")
    f.write(f"class ActionsMixin({mixin_classes}):\n")
    for text in core_funcs:
        f.write("    " + text.replace("\n", "\n    ").strip() + "\n\n")

print("Created appactions submodules and re-wrote appactions.py")
