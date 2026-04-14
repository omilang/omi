from src.values.types.number import Number, Int
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.dict import Dict
from src.values.types.boolean import Boolean
from src.values.types.module import Module
from src.values.function.stdlib import StdlibFunction
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class StringBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)

    def copy(self):
        copy = StringBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function string.{self.name}>"

    def execute_len(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))
        return RTResult().success(Int(len(s.value)))
    execute_len.arg_names = ["str"]

    def execute_slice(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        start = exec_ctx.symbol_table.get("start")
        end = exec_ctx.symbol_table.get("end")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(start, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a number", exec_ctx
            ))
        if not isinstance(end, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Third argument must be a number", exec_ctx
            ))

        return RTResult().success(String(s.value[int(start.value):int(end.value)]))
    execute_slice.arg_names = ["str", "start", "end"]

    def execute_split(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        delimiter = exec_ctx.symbol_table.get("delimiter")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(delimiter, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        parts = s.value.split(delimiter.value)
        return RTResult().success(List([String(p) for p in parts]))
    execute_split.arg_names = ["str", "delimiter"]

    def execute_join(self, exec_ctx):
        lst = exec_ctx.symbol_table.get("list")
        delimiter = exec_ctx.symbol_table.get("delimiter")

        if not isinstance(lst, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be an array", exec_ctx
            ))
        if not isinstance(delimiter, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        result = delimiter.value.join(str(elem) for elem in lst.elements)
        return RTResult().success(String(result))
    execute_join.arg_names = ["list", "delimiter"]

    def execute_replace(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        old = exec_ctx.symbol_table.get("old")
        new = exec_ctx.symbol_table.get("new")
        count = exec_ctx.symbol_table.get("count")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(old, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))
        if not isinstance(new, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Third argument must be a string", exec_ctx
            ))

        cnt = int(count.value) if isinstance(count, Number) else -1
        if cnt < 0:
            result = s.value.replace(old.value, new.value)
        else:
            result = s.value.replace(old.value, new.value, cnt)
        return RTResult().success(String(result))
    execute_replace.arg_names = ["str", "old", "new"]
    execute_replace.opt_names = ["count"]
    execute_replace.opt_defaults_factory = lambda: [Int(-1)]

    def execute_trim(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))
        return RTResult().success(String(s.value.strip()))
    execute_trim.arg_names = ["str"]

    def execute_trim_left(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))
        return RTResult().success(String(s.value.lstrip()))
    execute_trim_left.arg_names = ["str"]

    def execute_trim_right(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))
        return RTResult().success(String(s.value.rstrip()))
    execute_trim_right.arg_names = ["str"]

    def execute_upper(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))
        return RTResult().success(String(s.value.upper()))
    execute_upper.arg_names = ["str"]

    def execute_lower(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))
        return RTResult().success(String(s.value.lower()))
    execute_lower.arg_names = ["str"]

    def execute_contains(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        sub = exec_ctx.symbol_table.get("substring")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(sub, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))
        return RTResult().success(Boolean(sub.value in s.value))
    execute_contains.arg_names = ["str", "substring"]

    def execute_starts_with(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        prefix = exec_ctx.symbol_table.get("prefix")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(prefix, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))
        return RTResult().success(Boolean(s.value.startswith(prefix.value)))
    execute_starts_with.arg_names = ["str", "prefix"]

    def execute_ends_with(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        suffix = exec_ctx.symbol_table.get("suffix")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(suffix, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))
        return RTResult().success(Boolean(s.value.endswith(suffix.value)))
    execute_ends_with.arg_names = ["str", "suffix"]

    def execute_index_of(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        sub = exec_ctx.symbol_table.get("substring")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(sub, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))
        return RTResult().success(Int(s.value.find(sub.value)))
    execute_index_of.arg_names = ["str", "substring"]

    def execute_format(self, exec_ctx):
        template = exec_ctx.symbol_table.get("template")
        values = exec_ctx.symbol_table.get("values")

        if not isinstance(template, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))

        result = template.value

        if isinstance(values, List):
            for elem in values.elements:
                result = result.replace("{}", str(elem), 1)
        elif isinstance(values, Dict):
            for key, val in values.entries.items():
                result = result.replace("{" + key + "}", str(val))
        else:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be an array or dict", exec_ctx
            ))

        return RTResult().success(String(result))
    execute_format.arg_names = ["template", "values"]

    def execute_repeat(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        count = exec_ctx.symbol_table.get("count")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(count, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a number", exec_ctx
            ))

        return RTResult().success(String(s.value * int(count.value)))
    execute_repeat.arg_names = ["str", "count"]

    def execute_pad_left(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        length = exec_ctx.symbol_table.get("length")
        char = exec_ctx.symbol_table.get("char")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(length, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a number", exec_ctx
            ))

        fill = char.value if isinstance(char, String) and len(char.value) == 1 else " "
        return RTResult().success(String(s.value.rjust(int(length.value), fill)))
    execute_pad_left.arg_names = ["str", "length"]
    execute_pad_left.opt_names = ["char"]
    execute_pad_left.opt_defaults_factory = lambda: [String(" ")]

    def execute_pad_right(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        length = exec_ctx.symbol_table.get("length")
        char = exec_ctx.symbol_table.get("char")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(length, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a number", exec_ctx
            ))

        fill = char.value if isinstance(char, String) and len(char.value) == 1 else " "
        return RTResult().success(String(s.value.ljust(int(length.value), fill)))
    execute_pad_right.arg_names = ["str", "length"]
    execute_pad_right.opt_names = ["char"]
    execute_pad_right.opt_defaults_factory = lambda: [String(" ")]

    def execute_reverse(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))
        return RTResult().success(String(s.value[::-1]))
    execute_reverse.arg_names = ["str"]


def create_string_module():
    symbol_table = SymbolTable()

    funcs = [
        "len", "slice", "split", "join", "replace",
        "trim", "trim_left", "trim_right",
        "upper", "lower",
        "contains", "starts_with", "ends_with", "index_of",
        "format", "repeat", "pad_left", "pad_right", "reverse",
    ]
    for name in funcs:
        symbol_table.set(name, StringBuiltInFunction(name))

    return Module("string", symbol_table)
