from src.values.value import Value
from src.error.message.rt import RTError


def _python_to_omi_bridge(value):
    from src.values.types.boolean import Boolean
    from src.values.types.dict import Dict
    from src.values.types.list import List
    from src.values.types.null import Null
    from src.values.types.number import Number
    from src.values.types.string import String

    if isinstance(value, bool):
        return Boolean.true if value else Boolean.false
    if isinstance(value, (int, float)):
        return Number(value)
    if isinstance(value, str):
        return String(value)
    if value is None:
        return Null()
    if isinstance(value, list):
        return List([_python_to_omi_bridge(item) for item in value])
    if isinstance(value, tuple):
        return List([_python_to_omi_bridge(item) for item in value])
    if isinstance(value, dict):
        return Dict({str(k): _python_to_omi_bridge(v) for k, v in value.items()})

    return PythonLibValue(value)


class PythonLibValue(Value):
    def __init__(self, py_object, entries=None):
        super().__init__()
        self.py_object = py_object
        self.entries = dict(entries or {})

    def copy(self):
        copy = PythonLibValue(self.py_object, self.entries)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def get_member(self, name):
        if name in self.entries:
            return self.entries[name], None

        if not hasattr(self.py_object, name):
            return None, RTError(
                self.pos_start,
                self.pos_end,
                f"Python object has no attribute '{name}'",
                self.context,
            )

        try:
            value = getattr(self.py_object, name)
            converted = _python_to_omi_bridge(value)
            self.entries[name] = converted
            return converted, None
        except Exception as exc:
            return None, RTError(
                self.pos_start,
                self.pos_end,
                f"Failed to read Python attribute '{name}': {exc}",
                self.context,
            )

    def is_true(self):
        return len(self.entries) > 0

    def __repr__(self):
        obj = self.py_object
        obj_type = type(obj).__name__

        module_name = getattr(obj, "__name__", None)
        if module_name:
            return f"<py.lib module '{module_name}'>"

        return f"<py.lib {obj_type}>"
