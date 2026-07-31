import ast
import os
import sys

with open("src/tuipet/utils/persistence.py", "r") as f:
    lines = f.readlines()

def get_node_text(node):
    if hasattr(node, 'lineno') and hasattr(node, 'end_lineno'):
        return "".join(lines[node.lineno - 1:node.end_lineno])
    return ""

with open("src/tuipet/utils/persistence.py", "r") as f:
    tree = ast.parse(f.read())

imports_text = ""
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        imports_text += get_node_text(node)
    
settings_funcs = ['__getattr__', 'load_settings', 'get_auto_update', 'get_cloud_sync', 'set_cloud_sync', 'sync_enabled', 'set_auto_update', 'save_settings', 'get_blocked', 'set_blocked', 'get_dms', 'save_dms', 'get_account', 'set_account', 'erase_all']
progress_funcs = ['get_album', 'get_wins', 'album_seen', 'album_add', 'ladder_award_claimed', 'note_ladder_award', 'album_has', '_note_add', 'wins_add', 'record_connection', 'mega_kills_add', 'armor_add', '_prog', 'get_eggs_owned', 'egg_own', 'get_titles_owned', 'title_own', 'get_title_worn', 'set_title_worn', '_note_max', 'note_generation', 'note_stage_index', 'note_xanti', '_note_set', 'map_complete_add', 'zone_best_set', 'zone_bests', 'raid_add', 'tourney_add', 'festival_add', '_note_put', '_note_take', 'shop_unlock_add', 'shop_unlocks', 'bank_memory', 'bank_bonus_seed', 'take_bonus_seed', 'peek_memory', 'take_memory', 'get_progress', 'add_pending_bug', 'peek_pending_bugs', 'write_pending_bugs']
serializer_funcs = ['snapshot_prev_gen', '_heal_bag', 'prev_gen_estate', 'to_save_dict', 'pet_from_save']
save_funcs = ['save', 'write_save_dict', 'local_saved_at', 'quarantine_save', 'load', 'delete', 'exists']

def extract_funcs(func_list):
    text = imports_text + "\n"
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in func_list:
            text += get_node_text(node) + "\n"
    return text

os.makedirs("src/tuipet/utils/persistence", exist_ok=True)

with open("src/tuipet/utils/persistence/settings_io.py", "w") as f:
    f.write(extract_funcs(settings_funcs))

with open("src/tuipet/utils/persistence/progress_io.py", "w") as f:
    f.write(extract_funcs(progress_funcs))

with open("src/tuipet/utils/persistence/serializer.py", "w") as f:
    f.write(extract_funcs(serializer_funcs))

with open("src/tuipet/utils/persistence/save_io.py", "w") as f:
    f.write(extract_funcs(save_funcs))

with open("src/tuipet/utils/persistence/__init__.py", "w") as f:
    f.write("from .settings_io import *\nfrom .progress_io import *\nfrom .serializer import *\nfrom .save_io import *\n")

