import sys

def replace_in_file(file_path, old, new):
    with open(file_path, 'r') as f:
        text = f.read()
    with open(file_path, 'w') as f:
        f.write(text.replace(old, new))

replace_in_file('src/tuipet/utils/persistence/progress_io.py', 
                'from .settings_io import load_settings, save_settings\n', 
                '')

replace_in_file('src/tuipet/utils/persistence/progress_io.py', 
                'return load_settings().get("progress", {})',
                'from .settings_io import load_settings\n    return load_settings().get("progress", {})')

replace_in_file('src/tuipet/utils/persistence/progress_io.py', 
                'd = load_settings()',
                'from .settings_io import load_settings, save_settings\n    d = load_settings()')

