from src.error.message.rt import RTError
from src.run.runtime import RTResult
from src.var.keyword import TYPE_LABELS

def _type_label(value):
    return TYPE_LABELS.get(type(value).__name__.lower(), type(value).__name__.lower())

class Value:
    def __init__(self):
        self.set_pos()
        self.set_context()
        self.type_annotation = None
        self.is_const = False

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self
    
    def set_annotation(self, annotation):
        self.type_annotation = annotation
        return self

    def added_to(self, other):
        return None, self.illegal_operation(other, op='+')

    def subbed_by(self, other):
        return None, self.illegal_operation(other, op='-')

    def multed_by(self, other):
        return None, self.illegal_operation(other, op='*')

    def dived_by(self, other):
        return None, self.illegal_operation(other, op='/')

    def moded_by(self, other):
        return None, self.illegal_operation(other, op='%')

    def powed_by(self, other):
        return None, self.illegal_operation(other, op='^')

    def _equals_value(self, other):
        from src.values.types.boolean import Boolean
        from src.values.types.dict import Dict
        from src.values.types.list import List
        from src.values.types.null import Null
        from src.values.types.number import Number
        from src.values.types.string import String

        if isinstance(self, Null) or isinstance(other, Null):
            return isinstance(self, Null) and isinstance(other, Null)

        if isinstance(self, (Boolean, Number)) and isinstance(other, (Boolean, Number)):
            left = int(self.value) if isinstance(self, Boolean) else self.value
            right = int(other.value) if isinstance(other, Boolean) else other.value
            return left == right

        if isinstance(self, String) and isinstance(other, String):
            return self.value == other.value

        if isinstance(self, List) and isinstance(other, List):
            if len(self.elements) != len(other.elements):
                return False
            return all(left._equals_value(right) for left, right in zip(self.elements, other.elements))

        if isinstance(self, Dict) and isinstance(other, Dict):
            if set(self.entries.keys()) != set(other.entries.keys()):
                return False
            return all(self.entries[key]._equals_value(other.entries[key]) for key in self.entries)

        return False

    def get_comparison_eq(self, other):
        from src.values.types.boolean import Boolean
        return Boolean(self._equals_value(other)).set_context(self.context), None

    def get_comparison_ne(self, other):
        from src.values.types.boolean import Boolean
        return Boolean(not self._equals_value(other)).set_context(self.context), None

    def get_comparison_lt(self, other):
        return None, self.illegal_operation(other, op='<')

    def get_comparison_gt(self, other):
        return None, self.illegal_operation(other, op='>')

    def get_comparison_lte(self, other):
        return None, self.illegal_operation(other, op='<=')

    def get_comparison_gte(self, other):
        return None, self.illegal_operation(other, op='>=')

    def anded_by(self, other):
        return None, self.illegal_operation(other, op='and')

    def ored_by(self, other):
        return None, self.illegal_operation(other, op='or')

    def notted(self):
        return None, self.illegal_operation(op='isnt')

    def execute(self, args):
        return RTResult().failure(RTError(
            self.pos_start, self.pos_end,
            f"'{_type_label(self)}' is not callable",
            self.context
        ))

    def copy(self):
        raise Exception('No copy method defined')

    def is_true(self):
        return False

    def illegal_operation(self, other=None, op=None):
        pos_end = other.pos_end if (other and other is not self) else self.pos_end
        self_type = _type_label(self)
        if op:
            if other and other is not self:
                msg = f"Cannot apply '{op}' to {self_type} and {_type_label(other)}"
            else:
                msg = f"Cannot apply '{op}' to {self_type}"
        else:
            if other and other is not self:
                msg = f"Operation between {self_type} and {_type_label(other)} is not supported"
            else:
                msg = f"Operation is not supported for {self_type}"
        return RTError(self.pos_start, pos_end, msg, self.context)
