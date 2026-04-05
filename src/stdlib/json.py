import json as _json
import os as _os

from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.boolean import Boolean
from src.values.types.module import Module
from src.values.function.stdlib import StdlibFunction
from src.values.convert import python_to_omi, omi_to_python
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class JsonBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)

    def copy(self):
        copy = JsonBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function json.{self.name}>"

    def execute_parse(self, exec_ctx):
        text = exec_ctx.symbol_table.get("text")
        if not isinstance(text, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "json.parse(): argument must be a string",
                exec_ctx,
            ))
        try:
            data = _json.loads(text.value)
            return RTResult().success(python_to_omi(data))
        except _json.JSONDecodeError as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"json.parse(): invalid JSON — {e}",
                exec_ctx,
            ))
    execute_parse.arg_names = ["text"]

    def execute_stringify(self, exec_ctx):
        value = exec_ctx.symbol_table.get("value")
        indent_val = exec_ctx.symbol_table.get("indent")
        indent = int(indent_val.value) if isinstance(indent_val, Number) and indent_val.value else None
        try:
            py = omi_to_python(value)
            return RTResult().success(String(_json.dumps(py, ensure_ascii=False, indent=indent)))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"json.stringify(): cannot serialize value — {e}",
                exec_ctx,
            ))
    execute_stringify.arg_names = ["value"]
    execute_stringify.opt_names = ["indent"]
    execute_stringify.opt_defaults = [Number(0)]

    def execute_read(self, exec_ctx):
        path_val = exec_ctx.symbol_table.get("path")
        if not isinstance(path_val, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "json.read(): path must be a string",
                exec_ctx,
            ))
        path = path_val.value
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = _json.load(f)
            return RTResult().success(python_to_omi(data))
        except FileNotFoundError:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"json.read(): file not found: '{path}'",
                exec_ctx,
            ))
        except _json.JSONDecodeError as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"json.read(): invalid JSON in '{path}' — {e}",
                exec_ctx,
            ))
        except OSError as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"json.read(): cannot read '{path}' — {e}",
                exec_ctx,
            ))
    execute_read.arg_names = ["path"]

    def execute_write(self, exec_ctx):
        path_val  = exec_ctx.symbol_table.get("path")
        value     = exec_ctx.symbol_table.get("value")
        indent_val = exec_ctx.symbol_table.get("indent")
        if not isinstance(path_val, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "json.write(): path must be a string",
                exec_ctx,
            ))
        indent = int(indent_val.value) if isinstance(indent_val, Number) and indent_val.value else None
        try:
            py = omi_to_python(value)
            with open(path_val.value, "w", encoding="utf-8") as f:
                _json.dump(py, f, ensure_ascii=False, indent=indent)
            return RTResult().success(Number.null)
        except OSError as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"json.write(): cannot write '{path_val.value}' — {e}",
                exec_ctx,
            ))
    execute_write.arg_names = ["path", "value"]
    execute_write.opt_names = ["indent"]
    execute_write.opt_defaults = [Number(0)]

    def execute_append(self, exec_ctx):
        path_val = exec_ctx.symbol_table.get("path")
        value    = exec_ctx.symbol_table.get("value")
        if not isinstance(path_val, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "json.append(): path must be a string",
                exec_ctx,
            ))
        path = path_val.value
        try:
            if _os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    existing = _json.load(f)
                if not isinstance(existing, list):
                    return RTResult().failure(RTError(
                        self.pos_start, self.pos_end,
                        f"json.append(): '{path}' does not contain a JSON array",
                        exec_ctx,
                    ))
            else:
                existing = []
            existing.append(omi_to_python(value))
            with open(path, "w", encoding="utf-8") as f:
                _json.dump(existing, f, ensure_ascii=False, indent=2)
            return RTResult().success(Number.null)
        except (_json.JSONDecodeError, OSError) as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"json.append(): {e}",
                exec_ctx,
            ))
    execute_append.arg_names = ["path", "value"]

    def execute_exists(self, exec_ctx):
        path_val = exec_ctx.symbol_table.get("path")
        if not isinstance(path_val, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "json.exists(): path must be a string",
                exec_ctx,
            ))
        return RTResult().success(
            Boolean.true if _os.path.isfile(path_val.value) else Boolean.false
        )
    execute_exists.arg_names = ["path"]


def create_json_module():
    symbol_table = SymbolTable()
    for name in ("parse", "stringify", "read", "write", "append", "exists"):
        symbol_table.set(name, JsonBuiltInFunction(name))
    return Module("json", symbol_table)
