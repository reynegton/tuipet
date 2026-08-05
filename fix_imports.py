import glob
import re

replacements = [
    # persistence refactors
    (r"persistence\._atomic_write_json", r"persistio._atomic_write_json"),
    (r"persistence\._pick_save_dir", r"persistio._pick_save_dir"),
    (r"persistence\._migrate_egg_index", r"persistio._migrate_egg_index"),
    # shop refactors
    (r"tuipet\.core\.shop\._MAP_SPECIALTY", r"tuipet.core.shop.catalog._MAP_SPECIALTY"),
    (r"tuipet\.core\.shop\._town_rows", r"tuipet.core.shop.catalog._town_rows"),
    (r"tuipet\.core\.shop\.catalog\._MAP_SPECIALTY", r"tuipet.core.shop.catalog._MAP_SPECIALTY"), # in case already there
    (r"tuipet\.core\.shop\.catalog\._town_rows", r"tuipet.core.shop.catalog._town_rows"),
    # data
    (r"tuipet\.data\.loaders\.data\._load_consumables", r"tuipet.data.loaders.data_shop._load_consumables"),
    # bag
    (r"\._heal_bag", r"tuipet.utils.persistence.serializer._heal_bag"),
]

for t in glob.glob("tests/**/*.py", recursive=True):
    with open(t, "r") as f:
        src = f.read()
    orig = src
    for pattern, replacement in replacements:
        src = re.sub(pattern, replacement, src)
    if orig != src:
        with open(t, "w") as f:
            f.write(src)
        print(f"Updated {t}")
