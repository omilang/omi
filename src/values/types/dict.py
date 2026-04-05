from src.values.value import Value
from src.error.message.rt import RTError


class Dict(Value):
    def __init__(self, entries):
        super().__init__()
        self.entries = entries

    def get_member(self, name):
        value = self.entries.get(name)
        if value is None:
            return None, RTError(
                self.pos_start, self.pos_end,
                f"Key '{name}' not found in dict",
                self.context,
            )
        return value, None

    def is_true(self):
        return len(self.entries) > 0

    def copy(self):
        copy = Dict(dict(self.entries))
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        pairs = ", ".join(f'"{k}": {repr(v)}' for k, v in self.entries.items())
        return "{" + pairs + "}"

    def __str__(self):
        return self.__repr__()
