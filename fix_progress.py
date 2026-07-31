import sys

def insert_after_imports(file_path, content):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    insert_idx = 0
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            insert_idx = i + 1
    lines.insert(insert_idx, content + "\n")
    with open(file_path, 'w') as f:
        f.writelines(lines)

insert_after_imports('src/tuipet/utils/persistence/progress_io.py', 'from .settings_io import load_settings, save_settings')
