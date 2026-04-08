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

    def powed_by(self, other):
        return None, self.illegal_operation(other, op='^')

    def get_comparison_eq(self, other):
        return None, self.illegal_operation(other, op='==')

    def get_comparison_ne(self, other):
        return None, self.illegal_operation(other, op='!=')

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