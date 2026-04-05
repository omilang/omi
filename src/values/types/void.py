from src.values.value import Value
from src.values.types.boolean import Boolean


class Void(Value):

    def get_comparison_eq(self, other):
        return Boolean(isinstance(other, Void)).set_context(self.context), None

    def get_comparison_ne(self, other):
        return Boolean(not isinstance(other, Void)).set_context(self.context), None

    def anded_by(self, other):
        return Boolean.false.copy().set_context(self.context), None

    def ored_by(self, other):
        return Boolean(other.is_true()).set_context(self.context), None

    def notted(self):
        return Boolean.true.copy().set_context(self.context), None

    def is_true(self):
        return False

    def copy(self):
        copy = Void()
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return "void"


Void.void = Void()


class Uninitialized(Value):
    def __init__(self, name="", annotation=None):
        super().__init__()
        self.name = name
        self.annotation = annotation

    def copy(self):
        copy = Uninitialized(self.name, self.annotation)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return f"<uninitialized: {self.name}>"
