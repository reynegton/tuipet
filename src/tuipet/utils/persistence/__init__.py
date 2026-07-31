from .settings_io import *
from .progress_io import *
from .progress_io import _ALBUM_SEEN  # explicit: conftest patches this
from .serializer import *
from .save_io import *
import tuipet.utils.persistio as _persistio

def __getattr__(name):
    if name == "save_failed":
        return _persistio.save_failed
    raise AttributeError(name)
