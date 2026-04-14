import os
import shutil
from datetime import datetime
from src.values.types.number import Number, Int
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.boolean import Boolean
from src.values.types.module import Module
from src.values.function.stdlib import StdlibFunction
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class TxtBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)

    def copy(self):
        copy = TxtBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function txt.{self.name}>"

    def execute_read(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        encoding = exec_ctx.symbol_table.get("encoding")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))

        enc = encoding.value if isinstance(encoding, String) else "utf-8"

        try:
            with open(path.value, "r", encoding=enc) as f:
                content = f.read()
            return RTResult().success(String(content))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to read file: {e}", exec_ctx
            ))
    execute_read.arg_names = ["path"]
    execute_read.opt_names = ["encoding"]
    execute_read.opt_defaults_factory = lambda: [String("utf-8")]

    def execute_write(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        content = exec_ctx.symbol_table.get("content")
        encoding = exec_ctx.symbol_table.get("encoding")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(content, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        enc = encoding.value if isinstance(encoding, String) else "utf-8"

        try:
            with open(path.value, "w", encoding=enc) as f:
                f.write(content.value)
            return RTResult().success(Number.null)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to write file: {e}", exec_ctx
            ))
    execute_write.arg_names = ["path", "content"]
    execute_write.opt_names = ["encoding"]
    execute_write.opt_defaults_factory = lambda: [String("utf-8")]

    def execute_append(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        content = exec_ctx.symbol_table.get("content")
        encoding = exec_ctx.symbol_table.get("encoding")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(content, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            ))

        enc = encoding.value if isinstance(encoding, String) else "utf-8"

        try:
            with open(path.value, "a", encoding=enc) as f:
                f.write(content.value)
            return RTResult().success(Number.null)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to append to file: {e}", exec_ctx
            ))
    execute_append.arg_names = ["path", "content"]
    execute_append.opt_names = ["encoding"]
    execute_append.opt_defaults_factory = lambda: [String("utf-8")]

    def execute_lines(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        encoding = exec_ctx.symbol_table.get("encoding")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))

        enc = encoding.value if isinstance(encoding, String) else "utf-8"

        try:
            with open(path.value, "r", encoding=enc) as f:
                result = [String(line.rstrip("\n").rstrip("\r")) for line in f.readlines()]
            return RTResult().success(List(result))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to read lines: {e}", exec_ctx
            ))
    execute_lines.arg_names = ["path"]
    execute_lines.opt_names = ["encoding"]
    execute_lines.opt_defaults_factory = lambda: [String("utf-8")]

    def execute_write_lines(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")
        lines = exec_ctx.symbol_table.get("lines")
        encoding = exec_ctx.symbol_table.get("encoding")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string", exec_ctx
            ))
        if not isinstance(lines, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be an array", exec_ctx
            ))

        enc = encoding.value if isinstance(encoding, String) else "utf-8"

        try:
            with open(path.value, "w", encoding=enc) as f:
                for elem in lines.elements:
                    f.write(str(elem) + "\n")
            return RTResult().success(Number.null)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to write lines: {e}", exec_ctx
            ))
    execute_write_lines.arg_names = ["path", "lines"]
    execute_write_lines.opt_names = ["encoding"]
    execute_write_lines.opt_defaults_factory = lambda: [String("utf-8")]

    def execute_size(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))

        try:
            sz = os.path.getsize(path.value)
            return RTResult().success(Int(sz))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to get file size: {e}", exec_ctx
            ))
    execute_size.arg_names = ["path"]

    def execute_exists(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))

        return RTResult().success(Boolean(os.path.isfile(path.value)))
    execute_exists.arg_names = ["path"]

    def execute_backup(self, exec_ctx):
        path = exec_ctx.symbol_table.get("path")

        if not isinstance(path, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string", exec_ctx
            ))

        src_path = path.value
        if not os.path.isfile(src_path):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"File '{src_path}' does not exist", exec_ctx
            ))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base, ext = os.path.splitext(src_path)
        backup_path = f"{base}_{timestamp}{ext}.bak"

        try:
            shutil.copy2(src_path, backup_path)
            return RTResult().success(String(backup_path))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to backup file: {e}", exec_ctx
            ))
    execute_backup.arg_names = ["path"]


def create_txt_module():
    symbol_table = SymbolTable()

    funcs = ["read", "write", "append", "lines", "write_lines", "size", "exists", "backup"]
    for name in funcs:
        symbol_table.set(name, TxtBuiltInFunction(name))

    return Module("txt", symbol_table)
