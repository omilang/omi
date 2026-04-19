import os
import shutil
from src.values.value import Value
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.boolean import Boolean
from src.values.types.module import Module
from src.values.types.filehandle import FileHandleValue, _FileHandleState
from src.values.function.stdlib import StdlibFunction
from src.run.runtime import RTResult
from src.run.context import Context
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class FilesBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)
        self.is_async = True

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
        if isinstance(parents, Boolean):
            create_parents = parents.value
        elif isinstance(parents, Number):
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
    execute_mkdir.arg_names = ["path"]
    execute_mkdir.opt_names = ["parents"]
    execute_mkdir.opt_defaults_factory = lambda: [Boolean.true]

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
    execute_list.arg_names = []
    execute_list.opt_names = ["path"]
    execute_list.opt_defaults_factory = lambda: [String(".")]

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

    def execute_open(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        mode = exec_ctx.symbol_table.get("mode")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string",
                exec_ctx
            ))

        if not isinstance(mode, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string",
                exec_ctx
            ))

        try:
            py_file = open(path.value, mode.value, encoding=None if "b" in mode.value else "utf-8")
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to open file: {e}",
                exec_ctx
            ))

        handle = FileHandleValue(_FileHandleState(py_file, path.value, mode.value))
        handle.set_context(exec_ctx).set_pos(self.pos_start, self.pos_end)
        return RTResult().success(handle)
    execute_open.arg_names = ["path"]
    execute_open.opt_names = ["mode"]
    execute_open.opt_defaults_factory = lambda: [String("r")]

    def execute_close(self, exec_ctx):
        handle = exec_ctx.symbol_table.get("handle")

        if not isinstance(handle, FileHandleValue):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a file_handle",
                exec_ctx
            ))

        try:
            handle.close()
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to close file: {e}",
                exec_ctx
            ))

        return RTResult().success(Number.null)
    execute_close.arg_names = ["handle"]

    def execute_read(self, exec_ctx):
        handle = exec_ctx.symbol_table.get("handle")
        count = exec_ctx.symbol_table.get("count")

        if not isinstance(handle, FileHandleValue):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a file_handle",
                exec_ctx
            ))

        if handle.closed:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "File handle is closed",
                exec_ctx
            ))

        if not isinstance(count, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a number",
                exec_ctx
            ))

        try:
            data = handle.read(int(count.value))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to read from file: {e}",
                exec_ctx
            ))

        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="replace")

        return RTResult().success(String(data))
    execute_read.arg_names = ["handle"]
    execute_read.opt_names = ["count"]
    execute_read.opt_defaults_factory = lambda: [Number(-1)]

    def execute_write(self, exec_ctx):
        handle = exec_ctx.symbol_table.get("handle")
        data = exec_ctx.symbol_table.get("data")

        if not isinstance(handle, FileHandleValue):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a file_handle",
                exec_ctx
            ))

        if handle.closed:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "File handle is closed",
                exec_ctx
            ))

        if not isinstance(data, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string",
                exec_ctx
            ))

        try:
            written = handle.write(data.value)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to write file: {e}",
                exec_ctx
            ))

        return RTResult().success(Number(written))
    execute_write.arg_names = ["handle", "data"]


def create_files_module():
    symbol_table = SymbolTable()

    funcs = ["cwd", "mkdir", "rm", "rmdir", "list", "cp", "mv", "open", "close", "read", "write"]
    for name in funcs:
        symbol_table.set(name, FilesBuiltInFunction(name))

    return Module("files", symbol_table)
