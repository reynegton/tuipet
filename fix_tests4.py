import os
import re

def fix_imports(content):
    # Syntax error fixes
    content = content.replace("import tuipet.data.loaders.data as data as _data", "import tuipet.data.loaders.data as _data")
    
    # Net module
    content = re.sub(r'from tuipet\.net\b', r'from tuipet.network.net', content)
    content = re.sub(r'import tuipet\.net\b', r'import tuipet.network.net', content)
    
    # Screens missing
    content = re.sub(r'from tuipet\.raidscreen\b', r'from tuipet.ui.screens.raidscreen', content)
    content = re.sub(r'from tuipet\.digicorescreen\b', r'from tuipet.ui.screens.datacorescreen', content)
    
    # cloudsync was moved to utils or cloud? Actually cloudsync is in tuipet.cloudsync (or tuipet.network.cloudsync?)
    content = content.replace("from tuipet.ui.screens.cloudsync", "from tuipet.cloudsync")
    
    # Shop constants missing
    content = content.replace("tuipet.core.shop._town_maps", "tuipet.core.shop.store._town_maps")
    # if test_shops_audit uses shop._town_maps
    
    # Also fix 'from tuipet.ui.screens.adventurescreen import (..., HZ_TELE_T)'
    # HZ_TELE_T was probably moved to adventurescreen.constants or adventurescreen.helpers
    
    return content

if __name__ == "__main__":
    tests_dir = "tests"
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                
                content = fix_imports(content)
                
                with open(path, "w") as f:
                    f.write(content)
    print("Fixed more imports in tests/")
