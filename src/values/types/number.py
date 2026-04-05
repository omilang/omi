import math
from src.error.message.rt import RTError
from src.values.value import Value

def _num_result(value):
    if isinstance(value, float):
        if value == int(value) and not (value == float('inf') or value == float('-inf')):
            return Int(int(value))
        return Float(value)
    return Int(int(value)) if isinstance(value, int) else Float(float(value))


class Number(Value):
    def __new__(cls, value):
        if cls is Number:
            if isinstance(value, float):
                return object.__new__(Float)
            return object.__new__(Int)
        return object.__new__(cls)

    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        if isinstance(other, Number):
            return _num_result(self.value + other.value).set_context(self.context), None
        from src.values.types.boolean import Boolean
        if isinstance(other, Boolean):
            return _num_result(self.value + int(other.value)).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='+')

    def subbed_by(self, other):
        if isinstance(other, Number):
            return _num_result(self.value - other.value).set_context(self.context), None
        from src.values.types.boolean import Boolean
        if isinstance(other, Boolean):
            return _num_result(self.value - int(other.value)).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='-')

    def multed_by(self, other):
        if isinstance(other, Number):
            return _num_result(self.value * other.value).set_context(self.context), None
        from src.values.types.boolean import Boolean
        if isinstance(other, Boolean):
            return _num_result(self.value * int(other.value)).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='*')

    def dived_by(self, other):
        if isinstance(other, Number):
            if other.value == 0:
                return None, RTError(
                    other.pos_start, other.pos_end,
                    'Division by zero',
                    self.context
                )
            result = self.value / other.value
            return _num_result(result).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='/')

    def powed_by(self, other):
        if isinstance(other, Number):
            return _num_result(self.value ** other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='^')

    def get_comparison_eq(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(self.value == other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='==')

    def get_comparison_ne(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(self.value != other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='!=')

    def get_comparison_lt(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(self.value < other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='<')

    def get_comparison_gt(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(self.value > other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='>')

    def get_comparison_lte(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(self.value <= other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='<=')

    def get_comparison_gte(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(self.value >= other.value).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='>=')

    def anded_by(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(bool(self.value and other.value)).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='and')

    def ored_by(self, other):
        if isinstance(other, Number):
            from src.values.types.boolean import Boolean
            return Boolean(bool(self.value or other.value)).set_context(self.context), None
        return None, Value.illegal_operation(self, other, op='or')

    def notted(self):
        from src.values.types.boolean import Boolean
        return Boolean(self.value == 0).set_context(self.context), None

    def is_true(self):
        return self.value != 0

    def __repr__(self):
        return str(self.value)


class Int(Number):
    def __init__(self, value):
        Value.__init__(self)
        self.value = int(value)

    def copy(self):
        copy = Int(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return str(self.value)


class Float(Number):
    def __init__(self, value):
        Value.__init__(self)
        self.value = float(value)

    def copy(self):
        copy = Float(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def __repr__(self):
        return str(self.value)


from src.values.types.null import Null as _Null
Number.null = _Null()
Number.false = None
Number.true = None
Number.math_PI = Float(math.pi)
Number.math_E = Float(math.e)
