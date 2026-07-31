import ast
import os

with open("src/tuipet/core/shop.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    return "".join(lines[node.lineno - 1:node.end_lineno])

with open("src/tuipet/core/shop.py", "r") as f:
    tree = ast.parse(f.read())

categories = {
    "catalog": [
        "tier_for_price", "tier_weight", "tier_stock", "adventure_open", 
        "key_for_icon", "icon_art", "icon_frame", "item_is_eaten", "item_script", 
        "relic_open", "_price", "_usable", "catalog", "entry", "categories", 
        "shelf", "crest_answer", "wave_status", "effect_line"
    ],
    "eggs": [
        "_sellable_eggs", "town_egg_stock", "egg_price", "town_egg_rows", "town_egg_buy"
    ],
    "store": [
        "buy", "resell_price", "sell", "_today_ordinal", "_town_maps", 
        "_econ_stub", "_base_rows", "_guest_deal", "_town_rows", "_open_rows", 
        "_deal_index", "town_deal_sid", "_home_deal_pool", "home_deal_key", 
        "home_band", "_ration_left", "home_stock", "_stocked", "_town_taken", 
        "town_stock", "town_buy", "town_sell_price"
    ]
}

os.makedirs("src/tuipet/core/shop", exist_ok=True)

# Find top-level class (Item) and assignment (_AUTHORED)
item_class = None
authored_dict = None

for node in tree.body:
    if isinstance(node, ast.ClassDef) and node.name == "Item":
        item_class = get_node_text(node)
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "_AUTHORED":
                authored_dict = get_node_text(node)

# Collect functions
funcs = {cat: [] for cat in categories}
for node in tree.body:
    if isinstance(node, ast.FunctionDef):
        for cat, names in categories.items():
            if node.name in names:
                funcs[cat].append(get_node_text(node))
                break

with open("src/tuipet/core/shop/catalog.py", "w") as f:
    f.write("from typing import NamedTuple\n")
    f.write("import tuipet.data.loaders.data as data\n")
    f.write("from tuipet.i18n.translator import t\n")
    f.write("from tuipet.core.petbase import *\n\n")
    f.write(item_class + "\n\n")
    f.write(authored_dict + "\n\n")
    for text in funcs["catalog"]:
        f.write(text + "\n\n")

with open("src/tuipet/core/shop/eggs.py", "w") as f:
    f.write("import math\n")
    f.write("import tuipet.data.loaders.data as data\n")
    f.write("import tuipet.core.egg as egg_mod\n")
    f.write("from tuipet.i18n.translator import t\n")
    f.write("from tuipet.core.petbase import *\n")
    f.write("import tuipet.core.shop.catalog as catalog\n\n")
    for text in funcs["eggs"]:
        f.write(text + "\n\n")

with open("src/tuipet/core/shop/store.py", "w") as f:
    f.write("import random\n")
    f.write("import datetime\n")
    f.write("import time\n")
    f.write("from math import gcd as _gcd\n")
    f.write("import tuipet.data.loaders.data as data\n")
    f.write("from tuipet.i18n.translator import t\n")
    f.write("from tuipet.core.petbase import *\n")
    f.write("import tuipet.core.shop.catalog as catalog\n")
    f.write("import tuipet.core.shop.eggs as eggs\n\n")
    for text in funcs["store"]:
        f.write(text + "\n\n")

# __init__.py re-exports everything
with open("src/tuipet/core/shop/__init__.py", "w") as f:
    f.write("from .catalog import *\n")
    f.write("from .store import *\n")
    f.write("from .eggs import *\n")

print("Created shop submodules.")
