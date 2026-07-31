import ast
import os

with open("src/tuipet/ui/components/statusbox.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/ui/components/statusbox.py", "r") as f:
    tree = ast.parse(f.read())

categories = {
    "helpers": [
        "gen_subtitle", "age_compact", "care_deco", "status_line", "wrap", "card"
    ],
    "home_screen": [
        "_zone_display", "_frontier_name", "_where", "adventure_line", "home_lines"
    ],
    "egg_screen": [
        "egg_lines", "_hatch_line", "eggselect", "eggguide", "death", "grave_lines"
    ],
    "shop_screen": [
        "shop", "feed", "eat"
    ],
    "combat_screen": [
        "tournament", "battle", "raid"
    ],
    "menus_screen": [
        "title", "scenes", "lobby", "help_", "options", "bug", "assist", 
        "discipline", "training", "dna", "datacore"
    ],
    "registry": [
        "_registry", "painter_for", "__getattr__", "__init__" # these are for _SubView
    ]
}

subview_class = None
for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "_SubView":
        subview_class = get_node_text(node)

funcs = {cat: [] for cat in categories}
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        for cat, names in categories.items():
            if node.name in names:
                funcs[cat].append(get_node_text(node))
                break

os.makedirs("src/tuipet/ui/components/statusbox", exist_ok=True)

# common header
header = """from __future__ import annotations
import textwrap
import tuipet.utils.backgrounds as backgrounds
import tuipet.data.loaders.data as data
import tuipet.core.egg as egg_mod
import tuipet.utils.persistence as persistence
import tuipet.utils.theme as theme
from tuipet.core.arena import bar, hearts
from tuipet.core.petbase import DISOBEY_BELOW
from tuipet.i18n.translator import t

CARD_W = 26
DIV = "[dim]" + "─" * CARD_W + "[/]"
"""

with open("src/tuipet/ui/components/statusbox/helpers.py", "w") as f:
    f.write(header + "\n")
    for text in funcs["helpers"]:
        f.write(text + "\n\n")

for cat in ["home_screen", "egg_screen", "shop_screen", "combat_screen", "menus_screen"]:
    with open(f"src/tuipet/ui/components/statusbox/{cat}.py", "w") as f:
        f.write(header + "\n")
        f.write("from .helpers import *\n\n")
        for text in funcs[cat]:
            f.write(text + "\n\n")

with open("src/tuipet/ui/components/statusbox/registry.py", "w") as f:
    f.write("from .helpers import *\n")
    f.write("from .home_screen import *\n")
    f.write("from .egg_screen import *\n")
    f.write("from .shop_screen import *\n")
    f.write("from .combat_screen import *\n")
    f.write("from .menus_screen import *\n\n")
    if subview_class:
        f.write(subview_class + "\n\n")
    for text in funcs["registry"]:
        f.write(text + "\n\n")

# __init__.py re-exports
with open("src/tuipet/ui/components/statusbox/__init__.py", "w") as f:
    f.write("from .helpers import *\n")
    f.write("from .home_screen import *\n")
    f.write("from .egg_screen import *\n")
    f.write("from .shop_screen import *\n")
    f.write("from .combat_screen import *\n")
    f.write("from .menus_screen import *\n")
    f.write("from .registry import *\n")

print("Created statusbox submodules.")
