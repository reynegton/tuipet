import glob
import re

replacements = [
    (r"persistencetuipet\.utils\.persistence\.serializer\._heal_bag", r"tuipet.utils.persistence.serializer._heal_bag"),
    (r"serializertuipet\.utils\.persistence\.serializer\._heal_bag", r"tuipet.utils.persistence.serializer._heal_bag"),
    (r"persistio\._atomic_write_json", r"tuipet.utils.persistio._atomic_write_json"),
    (r"persistio\._pick_save_dir", r"tuipet.utils.persistio._pick_save_dir"),
    (r"persistio\._migrate_egg_index", r"tuipet.utils.persistio._migrate_egg_index"),
    (r"tuipet\.utils\.tuipet\.utils\.persistio\.", r"tuipet.utils.persistio."), # Fix duplicate prefixes
    (r"tuipet\.core\.data\.lines\.csv", r"tuipet.data.lines.csv"),
    (r"tuipet\.data\.loaders\.data\.lines\.csv", r"tuipet.data.lines.csv"),
    (r"tuipet\.core\.shop\._town_rows", r"tuipet.core.shop.catalog._town_rows"),
    (r"tuipet\.core\.shop\._MAP_SPECIALTY", r"tuipet.core.shop.catalog._MAP_SPECIALTY"),
    (r"tuipet\.data\.loaders\.data\._load_consumables", r"tuipet.data.loaders.data_shop._load_consumables"),
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
