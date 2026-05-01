import datetime as _datetime
import json as _json
import logging as _logging
import os as _os
import sys as _sys
from logging.handlers import RotatingFileHandler as _RotatingFileHandler

from src.error.message.rt import RTError
from src.main.symboltable import SymbolTable
from src.run.runtime import RTResult
from src.values.convert import omi_to_python
from src.values.function.stdlib import StdlibFunction
from src.values.types.dict import Dict
from src.values.types.module import Module
from src.values.types.number import Number
from src.values.types.string import String
from src.var.constant import (
    LEVEL_NAMES,
    SIZE_UNITS,
    DEFAULT_MAX_SIZE,
    DEFAULT_BACKUP_COUNT,
)
import src.var.ansi as ansi


class _ColorLevelFormatter(_logging.Formatter):
    LEVEL_TO_STYLE = {
        "DEBUG": ("blue",),
        "INFO": ("green",),
        "WARNING": ("yellow",),
        "ERROR": ("red",),
        "CRITICAL": ("red", "bold"),
    }

    def format(self, record):
        colored_level = ansi.wrap(record.levelname, *self.LEVEL_TO_STYLE.get(record.levelname, ()))
        return f"{colored_level}: {record.getMessage()}"

class _LogState:
    def __init__(self):
        self.logger = _logging.getLogger("omi.stdlib.log")
        self.logger.propagate = False
        self.logger.setLevel(_logging.INFO)
        self.context_data = {}
        self.json_enabled = False
        self.file_path = None
        self.file_mode = "a"
        self.max_bytes = None
        self.backup_count = 0
        self.stream_handler = None
        self.file_handler = None
        self._ensure_stream_handler()

    def _ensure_stream_handler(self):
        if self.stream_handler is not None:
            return
        handler = _logging.StreamHandler(_sys.stdout)
        handler.setFormatter(_ColorLevelFormatter())
        self.logger.addHandler(handler)
        self.stream_handler = handler

    def _remove_file_handler(self):
        if self.file_handler is None:
            return
        self.logger.removeHandler(self.file_handler)
        self.file_handler.close()
        self.file_handler = None

    def _rebuild_file_handler(self):
        self._remove_file_handler()
        if not self.file_path:
            return

        folder = _os.path.dirname(_os.path.abspath(self.file_path))
        if folder and not _os.path.isdir(folder):
            _os.makedirs(folder, exist_ok=True)

        if self.max_bytes is not None:
            handler = _RotatingFileHandler(
                self.file_path,
                mode=self.file_mode,
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding="utf-8",
            )
        else:
            handler = _logging.FileHandler(self.file_path, mode=self.file_mode, encoding="utf-8")

        handler.setFormatter(_logging.Formatter("%(message)s"))
        self.logger.addHandler(handler)
        self.file_handler = handler

    def parse_size(self, raw_value):
        value = raw_value.strip().upper()
        for unit in ("GB", "MB", "KB", "B"):
            if value.endswith(unit):
                amount = value[: -len(unit)].strip()
                if not amount.isdigit():
                    raise ValueError("size must be a number followed by unit, e.g. 10MB")
                return int(amount) * SIZE_UNITS[unit]

        if value.isdigit():
            return int(value)

        raise ValueError("unsupported size format; use B, KB, MB, or GB")

    def _trace_location(self, pos):
        if pos is None:
            return "<unknown>:0"
        line = pos.ln + 1 if hasattr(pos, "ln") else 0
        column = pos.col + 1 if hasattr(pos, "col") else 0
        file_name = pos.fn if getattr(pos, "fn", None) else "<unknown>"
        return f"{file_name}:{line}:{column}"

    def log(self, level_name, message, pos, extra_context=None):
        if self.stream_handler is not None:
            self.stream_handler.stream = _sys.stdout

        if level_name not in LEVEL_NAMES:
            level_name = "INFO"
        level_value = LEVEL_NAMES[level_name]

        combined_context = dict(self.context_data)
        if extra_context:
            combined_context.update(extra_context)

        if self.json_enabled:
            payload = {
                "timestamp": _datetime.datetime.utcnow().isoformat() + "Z",
                "level": level_name,
                "message": message,
            }
            if combined_context:
                payload["context"] = combined_context
            text = _json.dumps(payload, ensure_ascii=False)
        else:
            text = message
            if combined_context:
                context_chunks = [f"{k}={v}" for k, v in sorted(combined_context.items())]
                text = f"{message} | {' '.join(context_chunks)}"

        self.logger.log(level_value, text)


_LOG_STATE = _LogState()


class LogBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)
        self.is_async = True

    def copy(self):
        copy = LogBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function log.{self.name}>"

    def _value_to_text(self, value):
        if isinstance(value, String):
            return value.value
        return str(value)

    def _emit(self, level_name, exec_ctx, include_trace=False):
        message_value = exec_ctx.symbol_table.get("message")
        message = self._value_to_text(message_value)

        extra_context = None
        if include_trace:
            pos = self.pos_start or exec_ctx.parent_entry_pos
            extra_context = {"trace": _LOG_STATE._trace_location(pos)}

        _LOG_STATE.log(level_name, message, self.pos_start, extra_context=extra_context)
        return RTResult().success(Number.null)

    def execute_debug(self, exec_ctx):
        return self._emit("DEBUG", exec_ctx)
    execute_debug.arg_names = []
    execute_debug.opt_names = ["message"]
    execute_debug.opt_defaults = [String("")]

    def execute_info(self, exec_ctx):
        return self._emit("INFO", exec_ctx)
    execute_info.arg_names = []
    execute_info.opt_names = ["message"]
    execute_info.opt_defaults = [String("")]

    def execute_warning(self, exec_ctx):
        return self._emit("WARNING", exec_ctx)
    execute_warning.arg_names = []
    execute_warning.opt_names = ["message"]
    execute_warning.opt_defaults = [String("")]

    def execute_error(self, exec_ctx):
        return self._emit("ERROR", exec_ctx)
    execute_error.arg_names = []
    execute_error.opt_names = ["message"]
    execute_error.opt_defaults = [String("")]

    def execute_critical(self, exec_ctx):
        return self._emit("CRITICAL", exec_ctx)
    execute_critical.arg_names = []
    execute_critical.opt_names = ["message"]
    execute_critical.opt_defaults = [String("")]

    def execute_set_level(self, exec_ctx):
        level_value = exec_ctx.symbol_table.get("level")
        if not isinstance(level_value, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.set_level(): level must be a string",
                exec_ctx,
            ))

        level_name = level_value.value.strip().upper()
        if level_name not in LEVEL_NAMES:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.set_level(): level must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL",
                exec_ctx,
            ))

        _LOG_STATE.logger.setLevel(LEVEL_NAMES[level_name])
        return RTResult().success(Number.null)
    execute_set_level.arg_names = ["level"]

    def execute_set_file(self, exec_ctx):
        path_value = exec_ctx.symbol_table.get("path")
        mode_value = exec_ctx.symbol_table.get("mode")

        if not isinstance(path_value, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.set_file(): path must be a string",
                exec_ctx,
            ))
        if not isinstance(mode_value, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.set_file(): mode must be a string",
                exec_ctx,
            ))

        mode_text = mode_value.value.strip().lower()
        if mode_text not in ("append", "write"):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.set_file(): mode must be 'append' or 'write'",
                exec_ctx,
            ))

        _LOG_STATE.file_path = path_value.value
        _LOG_STATE.file_mode = "a" if mode_text == "append" else "w"
        try:
            _LOG_STATE._rebuild_file_handler()
        except OSError as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"log.set_file(): cannot open file - {e}",
                exec_ctx,
            ))

        return RTResult().success(Number.null)
    execute_set_file.arg_names = ["path"]
    execute_set_file.opt_names = ["mode"]
    execute_set_file.opt_defaults = [String("append")]

    def execute_rotate(self, exec_ctx):
        max_size_value = exec_ctx.symbol_table.get("max_size")
        backup_count_value = exec_ctx.symbol_table.get("backup_count")

        if not isinstance(max_size_value, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.rotate(): max_size must be a string like '10MB'",
                exec_ctx,
            ))
        if not isinstance(backup_count_value, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.rotate(): backup_count must be a number",
                exec_ctx,
            ))

        try:
            parsed_size = _LOG_STATE.parse_size(max_size_value.value)
        except ValueError as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"log.rotate(): {e}",
                exec_ctx,
            ))

        backup_count = int(backup_count_value.value)
        if backup_count < 0:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.rotate(): backup_count must be >= 0",
                exec_ctx,
            ))

        _LOG_STATE.max_bytes = parsed_size
        _LOG_STATE.backup_count = backup_count

        if not _LOG_STATE.file_path:
            _LOG_STATE.file_path = "omi.log"

        try:
            _LOG_STATE._rebuild_file_handler()
        except OSError as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"log.rotate(): cannot configure rotating file - {e}",
                exec_ctx,
            ))

        return RTResult().success(Number.null)
    execute_rotate.arg_names = []
    execute_rotate.opt_names = ["max_size", "backup_count"]
    execute_rotate.opt_defaults = [String(DEFAULT_MAX_SIZE), Number(DEFAULT_BACKUP_COUNT)]

    def execute_with_context(self, exec_ctx):
        data_value = exec_ctx.symbol_table.get("data")
        if not isinstance(data_value, Dict):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.with_context(): data must be a dict",
                exec_ctx,
            ))

        py_data = omi_to_python(data_value)
        if not isinstance(py_data, dict):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "log.with_context(): data must be a dict",
                exec_ctx,
            ))

        for key, value in py_data.items():
            _LOG_STATE.context_data[str(key)] = value

        return RTResult().success(Number.null)
    execute_with_context.arg_names = ["data"]

    def execute_json_mode(self, exec_ctx):
        _LOG_STATE.json_enabled = True
        return RTResult().success(Number.null)
    execute_json_mode.arg_names = []

    def execute_trace(self, exec_ctx):
        pos = self.pos_start or exec_ctx.parent_entry_pos
        trace_text = _LOG_STATE._trace_location(pos)
        _LOG_STATE.log("INFO", f"TRACE {trace_text}", pos)
        return RTResult().success(String(trace_text))
    execute_trace.arg_names = []


def create_log_module():
    symbol_table = SymbolTable()
    for name in (
        "debug",
        "info",
        "warning",
        "error",
        "critical",
        "set_level",
        "set_file",
        "rotate",
        "with_context",
        "json_mode",
        "trace",
    ):
        symbol_table.set(name, LogBuiltInFunction(name))
    return Module("log", symbol_table)
