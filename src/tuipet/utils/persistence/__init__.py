from typing import Any, Dict, List, Optional, Tuple, Callable, Union
from .settings_io import *
from .progress_io import *
from .progress_io import _ALBUM_SEEN  # explicit: conftest patches this
from .serializer import *
from .save_io import *
import tuipet.utils.persistio as _persistio

from tuipet.utils.persistio import _atomic_write_json, _pick_save_dir, acquire_instance_lock, SAVE_DIR, _LOCK_NAME, SAVE_PATH
from tuipet.core.eggmigrate import _migrate_egg_index, EGG_ORDER_V

def __getattr__(name: str) -> Any:
    if name == "save_failed":
        return _persistio.save_failed
    if hasattr(_persistio, name):
        return getattr(_persistio, name)
    raise AttributeError(name)
