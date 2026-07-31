"""
Correções cirúrgicas finais dos 36 testes quebrados.
Cada grupo de problemas é resolvido na fonte (src/) ou no teste — o que
for mais simples e menos arriscado.
"""
import re
import os


def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()


def write(p, text):
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def replace_import(path, old, new):
    text = read(path)
    if old in text:
        write(path, text.replace(old, new))
        print(f"  fixed: {os.path.basename(path)}: {old!r} -> {new!r}")


# ===========================================================================
# 1. ADVENTURESCREEN — expor constants no __init__ do pacote
# ===========================================================================
adv_init = "src/tuipet/ui/screens/adventurescreen/__init__.py"
write(adv_init, """\
from .panel import AdventurePanel
from .zone_pick import ZonePickPanel
from .renderer import (
    HZ_TELE_T, HZ_LUNGE_T,
    INV_WALK_T, INV_REVEAL_T, INV_HOLD_T,
)
""")
print("fixed: adventurescreen/__init__.py — exported timing constants")

# ===========================================================================
# 2. DATACORESCREEN — adicionar alias DigiCorePanel e DIGICORE_BASE_RATE
# ===========================================================================
dc = "src/tuipet/ui/screens/datacorescreen.py"
text = read(dc)
if "DigiCorePanel" not in text:
    # add aliases after the class definition comment block
    text = text.replace(
        "DATACORE_BASE_RATE = core.DATACORE_BASE_RATE",
        "DATACORE_BASE_RATE = core.DATACORE_BASE_RATE\nDIGICORE_BASE_RATE = core.DATACORE_BASE_RATE  # legacy alias"
    )
    # also alias the class
    text += "\n# legacy aliases kept for test imports\nDigiCorePanel = datacorePanel\n"
    write(dc, text)
    print("fixed: datacorescreen.py — added DigiCorePanel + DIGICORE_BASE_RATE aliases")

# ===========================================================================
# 3. SHOP — expor _town_maps no __init__ de shop
# ===========================================================================
shop_init = "src/tuipet/core/shop/__init__.py"
text = read(shop_init)
if "_town_maps" not in text:
    text += "\nfrom .catalog import _town_maps  # exposed for tests\n"
    write(shop_init, text)
    print("fixed: core/shop/__init__.py — exported _town_maps")

# ===========================================================================
# 4. TESTS — corrigir imports errados
# ===========================================================================

# lobbychat: estava em tuipet.ui.screens ou tuipet.core  →  tuipet.network.lobbychat
for fn in [
    "tests/test_honors.py",
    "tests/test_lobby.py",
    "tests/test_lobby_screens.py",
    "tests/test_menu_runoffs.py",
]:
    replace_import(fn, "from tuipet.ui.screens import lobbychat",
                   "from tuipet.network import lobbychat")
    replace_import(fn, "from tuipet.core import lobbychat",
                   "from tuipet.network import lobbychat")

# cloudsync: está em tuipet.network.cloudsync
for fn in [
    "tests/test_persistence_audit.py",
    "tests/test_sync.py",
]:
    replace_import(fn, "from tuipet.ui.screens import cloudsync",
                   "from tuipet.network import cloudsync")
    replace_import(fn, "from tuipet import cloudsync",
                   "from tuipet.network import cloudsync")

# digicore: o test usa datacorescreen diretamente — já OK
# mas test_evolution_audit usa "from tuipet.core import digicore"
replace_import("tests/test_evolution_audit.py",
               "from tuipet.core import digicore",
               "from tuipet.ui.screens import datacorescreen as digicore")

# data_meta → tuipet.data.loaders.data_meta
replace_import("tests/test_ko6_gate.py",
               "from tuipet.core import data_meta",
               "from tuipet.data.loaders import data_meta")

# app imported from tuipet.core  → just tuipet.app
replace_import("tests/test_poop_placement.py",
               "from tuipet.core import app as A",
               "import tuipet.app as A")

# adventure syntax errors: "from tuipet.ui.screens import adventurescreen" on its own line
# inside test_help.py (extra import leftover from scripted fixes)
for fn in ["tests/test_help.py"]:
    text = read(fn)
    # remove orphan import line that causes SyntaxError
    cleaned = re.sub(r"^\s*from tuipet\.ui\.screens import adventurescreen\s*\n", "",
                     text, flags=re.MULTILINE)
    if cleaned != text:
        write(fn, cleaned)
        print(f"  fixed: {os.path.basename(fn)}: removed orphan adventurescreen import")

# test_anim_timing, test_effects_integrity, test_egg_economy — check for syntax errors
for fn in ["tests/test_anim_timing.py",
           "tests/test_effects_integrity.py",
           "tests/test_egg_economy.py"]:
    text = read(fn)
    # remove any double 'as' clauses: "import x as y as z"
    cleaned = re.sub(r"(import \S+ as \S+) as \S+", r"\1", text)
    if cleaned != text:
        write(fn, cleaned)
        print(f"  fixed: {os.path.basename(fn)}: removed double 'as' clause")

# ===========================================================================
# 5. LOBBY / LOBBY_SCREENS — some tests need lobbychat attributes
#    that live inside the module but now path changed; also fix test_honors
#    which references lobbychat but might only need persistence
# ===========================================================================
print("\nAll fixes applied.")
