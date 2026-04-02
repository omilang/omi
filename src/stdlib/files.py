import os
import shutil
from src.values.value import Value
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.module import Module
from src.values.function.base import BaseFunction
from src.run.runtime import RTResult
from src.run.context import Context
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class FilesBuiltInFunction(BaseFunction):
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
        copy = FilesBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function files.{self.name}>"

    def execute_cwd(self, exec_ctx):
        return RTResult().success(String(os.getcwd()))
    execute_cwd.arg_names = []

    def execute_mkdir(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        parents = exec_ctx.symbol_table.get("parents")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string",
                exec_ctx
            ))

        create_parents = True
        if isinstance(parents, Number):
            create_parents = parents.value != 0

        try:
            if create_parents:
                os.makedirs(path.value, exist_ok=True)
            else:
                os.mkdir(path.value)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to create directory: {e}",
                exec_ctx
            ))

        return RTResult().success(Number.null)
    execute_mkdir.arg_names = ["path", "parents"]

    def execute_rm(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))

        try:
            os.remove(path.value)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to remove file: {e}",
                exec_ctx
            ))

        return RTResult().success(Number.null)
    execute_rm.arg_names = ["path"]

    def execute_rmdir(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))

        try:
            shutil.rmtree(path.value)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to remove directory: {e}",
                exec_ctx
            ))

        return RTResult().success(Number.null)
    execute_rmdir.arg_names = ["path"]

    def execute_list(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))

        try:
            entries = os.listdir(path.value)
            elements = [String(entry) for entry in entries]
            return RTResult().success(List(elements))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to list directory: {e}",
                exec_ctx
            ))
    execute_list.arg_names = ["path"]

    def execute_cp(self, exec_ctx):
        src = exec_ctx.symbol_table.get("src")
        dst = exec_ctx.symbol_table.get("dst")

        if not isinstance(src, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string",
                exec_ctx
            ))

        if not isinstance(dst, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string",
                exec_ctx
            ))

        try:
            if os.path.isdir(src.value):
                shutil.copytree(src.value, dst.value)
            else:
                shutil.copy2(src.value, dst.value)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to copy: {e}",
                exec_ctx
            ))

        return RTResult().success(Number.null)
    execute_cp.arg_names = ["src", "dst"]

    def execute_mv(self, exec_ctx):
        src = exec_ctx.symbol_table.get("src")
        dst = exec_ctx.symbol_table.get("dst")

        if not isinstance(src, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string",
                exec_ctx
            ))

        if not isinstance(dst, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string",
                exec_ctx
            ))

        try:
            shutil.move(src.value, dst.value)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to move: {e}",
                exec_ctx
            ))

        return RTResult().success(Number.null)
    execute_mv.arg_names = ["src", "dst"]


def create_files_module():
    symbol_table = SymbolTable()

    funcs = ["cwd", "mkdir", "rm", "rmdir", "list", "cp", "mv"]
    for name in funcs:
        symbol_table.set(name, FilesBuiltInFunction(name))

    return Module("files", symbol_table)
