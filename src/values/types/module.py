from src.values.value import Value
from src.error.message.rt import RTError

class Module(Value):
    def __init__(self, name, symbol_table):
        super().__init__()
        self.name = name
        self.symbol_table = symbol_table

    def get_member(self, name):
        value = self.symbol_table.get(name)
        if value is None:
            return None, RTError(
                self.pos_start, self.pos_end,
                f"Module '{self.name}' has no member '{name}'",
                self.context
            )
        return value, None

    def copy(self):
        copy = Module(self.name, self.symbol_table)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<module '{self.name}'>"
