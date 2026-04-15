import re as _re
from src.values.types.number import Number, Int
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.boolean import Boolean
from src.values.types.null import Null
from src.values.types.module import Module
from src.values.function.stdlib import StdlibFunction
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class RegexBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)

    def copy(self):
        copy = RegexBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function regex.{self.name}>"

    def _compile(self, pattern_str, exec_ctx):
        try:
            return _re.compile(pattern_str), None
        except _re.error as e:
            return None, RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Invalid regex pattern: {e}", exec_ctx
            ))

    def execute_test(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        pattern = exec_ctx.symbol_table.get("pattern")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(pattern, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        rx, err = self._compile(pattern.value, exec_ctx)
        if err: return err

        return RTResult().success(Boolean(bool(rx.search(s.value))))
    execute_test.arg_names = ["str", "pattern"]

    def execute_match(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        pattern = exec_ctx.symbol_table.get("pattern")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(pattern, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        rx, err = self._compile(pattern.value, exec_ctx)
        if err: return err

        m = rx.search(s.value)
        if m is None:
            return RTResult().success(Null())

        return RTResult().success(String(m.group(0)))
    execute_match.arg_names = ["str", "pattern"]

    def execute_find_all(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        pattern = exec_ctx.symbol_table.get("pattern")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(pattern, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        rx, err = self._compile(pattern.value, exec_ctx)
        if err: return err

        matches = rx.findall(s.value)
        return RTResult().success(List([String(m) for m in matches]))
    execute_find_all.arg_names = ["str", "pattern"]

    def execute_replace(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        pattern = exec_ctx.symbol_table.get("pattern")
        replacement = exec_ctx.symbol_table.get("replacement")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(pattern, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))
        if not isinstance(replacement, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Third argument must be a string", exec_ctx
            ))

        rx, err = self._compile(pattern.value, exec_ctx)
        if err: return err

        result = rx.sub(replacement.value, s.value)
        return RTResult().success(String(result))
    execute_replace.arg_names = ["str", "pattern", "replacement"]

    def execute_split(self, exec_ctx):
        s = exec_ctx.symbol_table.get("str")
        pattern = exec_ctx.symbol_table.get("pattern")

        if not isinstance(s, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(pattern, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        rx, err = self._compile(pattern.value, exec_ctx)
        if err: return err

        parts = rx.split(s.value)
        return RTResult().success(List([String(p) for p in parts]))
    execute_split.arg_names = ["str", "pattern"]


def create_regex_module():
    symbol_table = SymbolTable()

    funcs = ["test", "match", "find_all", "replace", "split"]
    for name in funcs:
        symbol_table.set(name, RegexBuiltInFunction(name))

    return Module("regex", symbol_table)
