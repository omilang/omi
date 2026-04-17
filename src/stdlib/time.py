import time as _time
import datetime
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.module import Module
from src.values.function.stdlib import StdlibFunction
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


DEFAULT_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


class TimeBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)
        self.is_async = True

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
    execute_format.arg_names = ["timestamp"]
    execute_format.opt_names = ["fmt"]
    execute_format.opt_defaults_factory = lambda: [String(DEFAULT_TIME_FORMAT)]

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
    execute_parse.arg_names = ["string"]
    execute_parse.opt_names = ["fmt"]
    execute_parse.opt_defaults_factory = lambda: [String(DEFAULT_TIME_FORMAT)]

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
