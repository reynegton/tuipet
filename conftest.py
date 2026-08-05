
import pytest
from tuipet.i18n import translator

@pytest.fixture(autouse=True)
def reset_language():
    translator.set_language("en")

