import os
import sys
import platform
import subprocess
from src.values.value import Value
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.module import Module
from src.values.function.base import BaseFunction
from src.run.runtime import RTResult
from src.run.context import Context
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class SystemBuiltInFunction(BaseFunction):
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
        copy = SystemBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function system.{self.name}>"

    def execute_exec(self, exec_ctx):
        cmd = exec_ctx.symbol_table.get("command")
        if not isinstance(cmd, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))
        try:
            result = subprocess.run(
                cmd.value, shell=True, capture_output=True, text=True
            )
            output = result.stdout if result.returncode == 0 else result.stderr
            return RTResult().success(String(output.rstrip("\n")))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"Failed to execute command: {e}",
                exec_ctx
            ))
    execute_exec.arg_names = ["command"]

    def execute_env(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")
        if not isinstance(name, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a string",
                exec_ctx
            ))
        value = os.environ.get(name.value, "")
        return RTResult().success(String(value))
    execute_env.arg_names = ["name"]

    def execute_set_env(self, exec_ctx):
        name = exec_ctx.symbol_table.get("name")
        value = exec_ctx.symbol_table.get("value")
        if not isinstance(name, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a string",
                exec_ctx
            ))
        if not isinstance(value, String):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string",
                exec_ctx
            ))
        os.environ[name.value] = value.value
        return RTResult().success(Number.null)
    execute_set_env.arg_names = ["name", "value"]

    def execute_platform(self, exec_ctx):
        return RTResult().success(String(platform.system()))
    execute_platform.arg_names = []

    def execute_username(self, exec_ctx):
        try:
            name = os.getlogin()
        except OSError:
            name = os.environ.get("USERNAME", os.environ.get("USER", "unknown"))
        return RTResult().success(String(name))
    execute_username.arg_names = []

    def execute_exit(self, exec_ctx):
        code = exec_ctx.symbol_table.get("code")
        if isinstance(code, Number) and code.value != 0:
            sys.exit(int(code.value))
        else:
            sys.exit(0)
    execute_exit.arg_names = ["code"]

    def execute_cwd(self, exec_ctx):
        return RTResult().success(String(os.getcwd()))
    execute_cwd.arg_names = []


def create_system_module():
    symbol_table = SymbolTable()

    funcs = ["exec", "env", "set_env", "platform", "username", "exit", "cwd"]
    for name in funcs:
        symbol_table.set(name, SystemBuiltInFunction(name))

    return Module("system", symbol_table)
