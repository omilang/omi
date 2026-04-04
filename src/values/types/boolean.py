from src.values.value import Value


class Boolean(Value):
    def __init__(self, value):
        super().__init__()
        self.value = bool(value)

    def added_to(self, other):
        from src.values.types.number import Number
        if isinstance(other, (Boolean, Number)):
            return Number(int(self.value) + other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='+')

    def subbed_by(self, other):
        from src.values.types.number import Number
        if isinstance(other, (Boolean, Number)):
            return Number(int(self.value) - other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='-')

    def multed_by(self, other):
        from src.values.types.number import Number
        if isinstance(other, (Boolean, Number)):
            return Number(int(self.value) * other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='*')

    def get_comparison_eq(self, other):
        if isinstance(other, Boolean):
            return Boolean(self.value == other.value).set_context(self.context), None
        from src.values.types.number import Number
        if isinstance(other, Number):
            return Boolean(int(self.value) == other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='==')

    def get_comparison_ne(self, other):
        if isinstance(other, Boolean):
            return Boolean(self.value != other.value).set_context(self.context), None
        from src.values.types.number import Number
        if isinstance(other, Number):
            return Boolean(int(self.value) != other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='!=')

    def anded_by(self, other):
        if isinstance(other, Boolean):
            return Boolean(self.value and other.value).set_context(self.context), None
        from src.values.types.number import Number
        if isinstance(other, (Boolean, Number)):
            return Boolean(bool(self.value and other.value)).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='and')

    def ored_by(self, other):
        if isinstance(other, Boolean):
            return Boolean(self.value or other.value).set_context(self.context), None
        from src.values.types.number import Number
        if isinstance(other, (Boolean, Number)):
            return Boolean(bool(self.value or other.value)).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='or')

    def notted(self):
        return Boolean(not self.value).set_context(self.context), None

    def is_true(self):
        return self.value

    def copy(self):
        copy = Boolean(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return "true" if self.value else "false"

    def __str__(self):
        return self.__repr__()


Boolean.true = None
Boolean.false = None

Boolean.true = Boolean(True)
Boolean.false = Boolean(False)
