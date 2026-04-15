from src.values.function.base import BaseFunction
from src.values.types.dict import Dict
from src.values.types.string import String
from src.run.runtime import RTResult
from src.error.message.rt import RTError


class EnumVariantConstructor(BaseFunction):
    def __init__(self, enum_name, variant_name, payload_type=None, enum_annotation=None):
        super().__init__(variant_name)
        self.enum_name = enum_name
        self.variant_name = variant_name
        self.payload_type = payload_type
        self.enum_annotation = enum_annotation

    def execute(self, args):
        res = RTResult()
        expected_args = 0 if self.payload_type is None else 1

        if len(args) != expected_args:
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                f"'{self.variant_name}' takes {expected_args} argument{'s' if expected_args != 1 else ''}, but {len(args)} were given",
                self.context,
            ))

        entries = {
            "__tag": String(self.variant_name),
        }
        if expected_args == 1:
            entries["value"] = args[0]

        value = Dict(entries).set_context(self.context).set_pos(self.pos_start, self.pos_end)
        if self.enum_annotation is not None:
            value.set_annotation(self.enum_annotation)
            value.type_name = self.enum_name

        return res.success(value)

    def copy(self):
        copy = EnumVariantConstructor(
            self.enum_name,
            self.variant_name,
            self.payload_type,
            self.enum_annotation,
        )
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<enum constructor {self.variant_name}>"