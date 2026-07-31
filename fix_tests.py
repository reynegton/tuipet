import os
import re

CORE_MODULES = [
    "adventure", "arena", "battle", "datacore", "egg", "eggmigrate", "evolution",
    "jogress", "lines", "pet", "petbase", "petbattle", "petbody", "petcare",
    "petdna", "rival", "shop", "tournament", "training", "shop_constants"
]

UTILS_MODULES = [
    "anim", "arenafx", "backgrounds", "grid", "hostinfo", "itemfx",
    "persistence", "persistio", "placeholder", "render", "sound",
    "strikefx", "theme", "update"
]

UI_SCREENS = [
    "accountscreen", "adventurescreen", "albumscreen", "assistscreen",
    "backgroundscreen", "battlescreen", "bugscreen", "cloudsync",
    "datacorescreen", "deathscreen", "dnascreen", "eggguidescreen",
    "eggselectscreen", "feedscreen", "hallscreen", "helpscreen",
    "lobbyscreen", "optionsscreen", "shopscreen", "titlescreen",
    "tournamentscreen"
]

UI_COMPONENTS = [
    "statusbox", "menu"
]

def replace_imports(content):
    # from tuipet.pet import Pet -> from tuipet.core.pet import Pet
    for mod in CORE_MODULES:
        content = re.sub(r'from tuipet\.' + mod + r'\b', r'from tuipet.core.' + mod, content)
        # from tuipet import pet -> from tuipet.core import pet
        content = re.sub(r'from tuipet import (\s*[^,]*\b' + mod + r'\b)', r'from tuipet.core import \1', content)
        
    for mod in UTILS_MODULES:
        content = re.sub(r'from tuipet\.' + mod + r'\b', r'from tuipet.utils.' + mod, content)
        content = re.sub(r'from tuipet import (\s*[^,]*\b' + mod + r'\b)', r'from tuipet.utils import \1', content)
        
    for mod in UI_SCREENS:
        content = re.sub(r'from tuipet\.' + mod + r'\b', r'from tuipet.ui.screens.' + mod, content)
        content = re.sub(r'from tuipet import (\s*[^,]*\b' + mod + r'\b)', r'from tuipet.ui.screens import \1', content)
        
    for mod in UI_COMPONENTS:
        content = re.sub(r'from tuipet\.' + mod + r'\b', r'from tuipet.ui.components.' + mod, content)
        content = re.sub(r'from tuipet import (\s*[^,]*\b' + mod + r'\b)', r'from tuipet.ui.components import \1', content)
        
    # Also handle "import tuipet.pet" -> "import tuipet.core.pet"
    for mod in CORE_MODULES:
        content = re.sub(r'import tuipet\.' + mod + r'\b', r'import tuipet.core.' + mod, content)
    for mod in UTILS_MODULES:
        content = re.sub(r'import tuipet\.' + mod + r'\b', r'import tuipet.utils.' + mod, content)
    for mod in UI_SCREENS:
        content = re.sub(r'import tuipet\.' + mod + r'\b', r'import tuipet.ui.screens.' + mod, content)
    for mod in UI_COMPONENTS:
        content = re.sub(r'import tuipet\.' + mod + r'\b', r'import tuipet.ui.components.' + mod, content)

    # Some test files might do `from tuipet import adventure as adv, persistence, shop`
    # It's hard to catch all variants with regex without breaking. 
    # But let's fix the most common "from tuipet import X, Y" by splitting them up.
    
    # Actually, a simpler way is just to leave regex for `from tuipet import ...` 
    # It's better to manually fix or use a smarter AST rewriter if regex fails, but let's try regex first.
    
    return content

# Special regex for 'from tuipet import a, b' -> we'll just rewrite them one by one if they are on their own lines.
def fix_multi_imports(content):
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if line.startswith('from tuipet import ') or line.startswith('    from tuipet import '):
            indent = line[:len(line) - len(line.lstrip())]
            imports_str = line.split('import ')[1]
            imports = [imp.strip() for imp in imports_str.split(',')]
            
            new_lines = []
            for imp in imports:
                mod_name = imp.split(' as ')[0]
                if mod_name in CORE_MODULES:
                    new_lines.append(f"{indent}from tuipet.core import {imp}")
                elif mod_name in UTILS_MODULES:
                    new_lines.append(f"{indent}from tuipet.utils import {imp}")
                elif mod_name in UI_SCREENS:
                    new_lines.append(f"{indent}from tuipet.ui.screens import {imp}")
                elif mod_name in UI_COMPONENTS:
                    new_lines.append(f"{indent}from tuipet.ui.components import {imp}")
                elif mod_name == "app":
                    new_lines.append(f"{indent}from tuipet import {imp}")
                elif mod_name == "appactions":
                    new_lines.append(f"{indent}from tuipet import {imp}")
                elif mod_name == "appboot":
                    new_lines.append(f"{indent}from tuipet import {imp}")
                else:
                    new_lines.append(f"{indent}from tuipet import {imp}")
            
            lines[i] = '\n'.join(new_lines)
    return '\n'.join(lines)


if __name__ == "__main__":
    tests_dir = "tests"
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                
                content = fix_multi_imports(content)
                content = replace_imports(content)
                
                with open(path, "w") as f:
                    f.write(content)
    print("Rewrote imports in tests/")
