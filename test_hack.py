import sys
class DummyModule:
    pass
sys.modules["hack_module"] = DummyModule()
import hack_module
print(type(hack_module))
