import os
import re

UI_SCREENS = [
    "townscreen", "towneggscreen", "townshopscreen"
]

def replace_imports(content):
    # data module
    content = re.sub(r'from tuipet\.core import data\b', r'import tuipet.data.loaders.data as data', content)
    content = re.sub(r'from tuipet\.utils import data\b', r'import tuipet.data.loaders.data as data', content)
    content = re.sub(r'from tuipet import data\b', r'import tuipet.data.loaders.data as data', content)
    content = re.sub(r'import tuipet\.data\b', r'import tuipet.data.loaders.data as data', content)
    
    # townscreens
    for mod in UI_SCREENS:
        content = re.sub(r'from tuipet\.' + mod + r'\b', r'from tuipet.ui.screens.' + mod, content)
        content = re.sub(r'from tuipet import (\s*[^,]*\b' + mod + r'\b)', r'from tuipet.ui.screens import \1', content)
        
    return content

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
                if mod_name in UI_SCREENS:
                    new_lines.append(f"{indent}from tuipet.ui.screens import {imp}")
                elif mod_name == "data":
                    new_lines.append(f"{indent}import tuipet.data.loaders.data as data")
                else:
                    new_lines.append(f"{indent}from tuipet import {imp}")
            
            # Reconstruct only if we changed something in our manual split list before
            # Actually, since we're appending "from tuipet import imp" for the ones we don't know, 
            # this might undo previous fixes if we run it again!
            # Wait, fix_multi_imports was already run. The files don't have "from tuipet import" for the core modules anymore.
            # But let's skip fix_multi_imports for now because `data` and `townscreen` are usually not imported in a comma list like that anymore.
            pass
            
    return content

if __name__ == "__main__":
    tests_dir = "tests"
    for root, dirs, files in os.walk(tests_dir):
        for file in files:
            if file.endswith(".py"):
                path = os.path.join(root, file)
                with open(path, "r") as f:
                    content = f.read()
                
                content = replace_imports(content)
                
                with open(path, "w") as f:
                    f.write(content)
    print("Rewrote imports in tests/ again")
