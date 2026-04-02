import time as _time
import datetime
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.module import Module
from src.values.function.base import BaseFunction
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class TimeBuiltInFunction(BaseFunction):
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
        copy = TimeBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function time.{self.name}>"

    def execute_now(self, exec_ctx):
        return RTResult().success(Number(_time.time()))
    execute_now.arg_names = []

    def execute_format(self, exec_ctx):
        timestamp = exec_ctx.symbol_table.get("timestamp")
        fmt = exec_ctx.symbol_table.get("fmt")

        if not isinstance(timestamp, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a number (timestamp)",
                exec_ctx
            ))
        if not isinstance(fmt, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string (format)",
                exec_ctx
            ))

        try:
            dt = datetime.datetime.fromtimestamp(timestamp.value)
            result = dt.strftime(fmt.value)
            return RTResult().success(String(result))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to format timestamp: {e}",
                exec_ctx
            ))
    execute_format.arg_names = ["timestamp", "fmt"]

    def execute_sleep(self, exec_ctx):
        seconds = exec_ctx.symbol_table.get("seconds")

        if not isinstance(seconds, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a number",
                exec_ctx
            ))

        try:
            _time.sleep(seconds.value)
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Sleep failed: {e}",
                exec_ctx
            ))

        return RTResult().success(Number.null)
    execute_sleep.arg_names = ["seconds"]

    def execute_parse(self, exec_ctx):
        string = exec_ctx.symbol_table.get("string")
        fmt = exec_ctx.symbol_table.get("fmt")

        if not isinstance(string, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string",
                exec_ctx
            ))
        if not isinstance(fmt, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string (format)",
                exec_ctx
            ))

        try:
            dt = datetime.datetime.strptime(string.value, fmt.value)
            return RTResult().success(Number(dt.timestamp()))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to parse time string: {e}",
                exec_ctx
            ))
    execute_parse.arg_names = ["string", "fmt"]

    def execute_timezone(self, exec_ctx):
        offset_seconds = -_time.timezone
        if _time.daylight and _time.localtime().tm_isdst:
            offset_seconds = -_time.altzone
        offset_hours = offset_seconds / 3600
        return RTResult().success(Number(offset_hours))
    execute_timezone.arg_names = []


def create_time_module():
    symbol_table = SymbolTable()

    funcs = ["now", "format", "sleep", "parse", "timezone"]
    for name in funcs:
        symbol_table.set(name, TimeBuiltInFunction(name))

    return Module("time", symbol_table)
