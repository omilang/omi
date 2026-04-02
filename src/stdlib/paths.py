import os
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.module import Module
from src.values.function.base import BaseFunction
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class PathsBuiltInFunction(BaseFunction):
    def __init__(self, name):
        super().__init__(name)

    def execute(self, args):
        res = RTResult()
        exec_ctx = self.generate_new_context()

        method_name = f"execute_{self.name}"
        method = getattr(self, method_name, self.no_visit_method)

        res.register(self.check_and_populate_args(method.arg_names, args, exec_ctx))
        if res.should_return(): return res

        return_value = res.register(method(exec_ctx))
        if res.should_return(): return res
        return res.success(return_value)

    def no_visit_method(self, node, context):
        raise Exception(f"No execute_{self.name} method defined")

    def copy(self):
        copy = PathsBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function paths.{self.name}>"

    def execute_join(self, exec_ctx):
        parts = exec_ctx.symbol_table.get("parts")

        if not isinstance(parts, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a list of strings",
                exec_ctx
            ))

        str_parts = []
        for el in parts.elements:
            if not isinstance(el, String):
                return RTResult().failure(RTError(
                    self.pos_start, self.pos_end,
                    "All list elements must be strings",
                    exec_ctx
                ))
            str_parts.append(el.value)

        return RTResult().success(String(os.path.join(*str_parts)))
    execute_join.arg_names = ["parts"]

    def execute_abs(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))

        return RTResult().success(String(os.path.abspath(path.value)))
    execute_abs.arg_names = ["path"]

    def execute_exists(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))

        return RTResult().success(Number.true if os.path.exists(path.value) else Number.false)
    execute_exists.arg_names = ["path"]

    def execute_ext(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))

        _, extension = os.path.splitext(path.value)
        return RTResult().success(String(extension))
    execute_ext.arg_names = ["path"]

    def execute_name(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))

        return RTResult().success(String(os.path.basename(path.value)))
    execute_name.arg_names = ["path"]


def create_paths_module():
    symbol_table = SymbolTable()

    funcs = ["join", "abs", "exists", "ext", "name"]
    for name in funcs:
        symbol_table.set(name, PathsBuiltInFunction(name))

    return Module("paths", symbol_table)