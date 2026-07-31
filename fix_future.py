def fix(path):
    with open(path, 'r') as f:
        lines = f.readlines()
    
    # filter out the future import and put it back at the very top
    future_line = "from __future__ import annotations\n"
    new_lines = [l for l in lines if l.strip() != "from __future__ import annotations"]
    new_lines.insert(0, future_line)
    
    with open(path, 'w') as f:
        f.writelines(new_lines)

fix('src/tuipet/appactions/care_actions.py')
fix('src/tuipet/appactions/nav_actions.py')
fix('src/tuipet/appactions/system_actions.py')
