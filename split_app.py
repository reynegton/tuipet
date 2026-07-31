import ast
import os

with open("src/tuipet/app.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/app.py", "r") as f:
    tree = ast.parse(f.read())

mixins = {
    "hud": ["_hud", "_hud_marquee", "flash", "_need_message", "_evolve_msg", "_armed_field"],
    "timers": ["on_frame", "on_tick", "_drain_pms", "_drain_verdict", "_drain_beep_q"],
    "cloud": ["_start_sync", "_stop_sync", "_push_cloud", "_warn_if_cloud_dropped", "_flush_cloud_on_quit"],
    "sound": ["beep", "alarm_pattern", "_alarm_urgency", "_toggle_sound"],
    "lifecycle": ["_post_title", "_death_ceremony", "_grant_memory", "autosave", "_warn_if_unsaveable", "_note_progress", "_flush_dms_on_quit", "_hatch_new", "_whats_new"]
}

app_node = None
header_nodes = []
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "TuiPetApp":
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
            if node.name in names:
                funcs[cat].append(get_node_text(node))
                matched = True
                break
        if not matched:
            core_funcs.append(get_node_text(node))
    else:
        core_funcs.append(get_node_text(node))

os.makedirs("src/tuipet/app_mixins", exist_ok=True)

with open("src/tuipet/app_mixins/__init__.py", "w") as f:
    for cat in mixins:
        f.write(f"from .{cat} import {cat.capitalize()}Mixin\n")

for cat in mixins:
    with open(f"src/tuipet/app_mixins/{cat}.py", "w") as f:
        f.write("from __future__ import annotations\n")
        f.write("import tuipet.data.loaders.data as data\n")
        f.write("import tuipet.utils.persistence as persistence\n")
        f.write("from tuipet.i18n.translator import t\n")
        f.write(f"class {cat.capitalize()}Mixin:\n")
        for text in funcs[cat]:
            f.write("    " + text.replace("\n", "\n    ").strip() + "\n\n")

# Re-write app.py
mixin_classes = ", ".join(f"{cat.capitalize()}Mixin" for cat in mixins)
with open("src/tuipet/app.py", "w") as f:
    f.write(header)
    f.write("from tuipet.app_mixins import *\n\n")
    # TuiPetApp definition
    # Find original class def line in lines
    for line in lines:
        if line.startswith("class TuiPetApp("):
            new_line = line.replace("ActionsMixin, App", f"ActionsMixin, {mixin_classes}, App")
            f.write(new_line)
            break
    for text in core_funcs:
        f.write("    " + text.replace("\n", "\n    ").strip() + "\n\n")

print("Created app_mixins and re-wrote app.py")
