import ast
import importlib

from src.error.message.rt import RTError
from src.main.symboltable import SymbolTable
from src.nodes.types.typeannotation import TypeAnnotationNode
from src.run.runtime import RTResult
from src.values.convert import omi_to_python
from src.values.function.stdlib import StdlibFunction
from src.values.types.boolean import Boolean
from src.values.types.dict import Dict
from src.values.types.list import List
from src.values.types.module import Module
from src.values.types.null import Null
from src.values.types.number import Number
from src.values.types.pythonlib import PythonLibValue
from src.values.types.string import String


def _lib_type_annotation():
    return TypeAnnotationNode(["pylib"], None, None)


def _python_to_omi_bridge(value):
    if isinstance(value, bool):
        return Boolean.true if value else Boolean.false
    if isinstance(value, (int, float)):
        return Number(value)
    if isinstance(value, str):
        return String(value)
    if value is None:
        return Null()
    if isinstance(value, list):
        return List([_python_to_omi_bridge(item) for item in value])
    if isinstance(value, tuple):
        return List([_python_to_omi_bridge(item) for item in value])
    if isinstance(value, dict):
        return Dict({str(k): _python_to_omi_bridge(v) for k, v in value.items()})

    return PythonLibValue(value)


def _omi_to_python_bridge(value):
    if isinstance(value, PythonLibValue):
        return value.py_object

    converted = omi_to_python(value)
    if converted is not None:
        return converted

    if isinstance(value, Null):
        return None

    return str(value)


def _execute_python_code(code):
    namespace = {"__builtins__": __builtins__}

    try:
        compiled_eval = compile(code, "<omi:python>", "eval")
        return eval(compiled_eval, namespace, namespace)
    except SyntaxError:
        pass

    tree = ast.parse(code, mode="exec")
    if not tree.body:
        return None

    if isinstance(tree.body[-1], ast.Expr):
        prefix_body = tree.body[:-1]
        last_expr = tree.body[-1].value

        if prefix_body:
            prefix_module = ast.Module(body=prefix_body, type_ignores=[])
            exec(compile(prefix_module, "<omi:python>", "exec"), namespace, namespace)

        expr_module = ast.Expression(body=last_expr)
        return eval(compile(expr_module, "<omi:python>", "eval"), namespace, namespace)

    exec(compile(tree, "<omi:python>", "exec"), namespace, namespace)
    return None


def _module_to_omi_lib(module):
    entries = {}

    for name in dir(module):
        if name.startswith("__"):
            continue

        try:
            attr = getattr(module, name)
        except Exception:
            continue

        entries[name] = _python_to_omi_bridge(attr)

    return PythonLibValue(module, entries)


class PythonBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)

    def copy(self):
        copy = PythonBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function python.{self.name}>"

    def execute(self, args, kwargs=None):
        if self.name == "call":
            return self._execute_call_varargs(args, kwargs or {})
        return super().execute(args, kwargs)

    def _execute_call_varargs(self, args, kwargs):
        res = RTResult()

        if len(args) < 2:
            return res.failure(RTError(
                self.pos_start,
                self.pos_end,
                "py.call requires at least 2 arguments: (lib, name, ...args)",
                self.context,
            ))

        lib_value = args[0]
        attr_name = args[1]
        call_args = args[2:]

        if not isinstance(attr_name, String):
            return res.failure(RTError(
                self.pos_start,
                self.pos_end,
                "Second argument of py.call must be a string method/function name",
                self.context,
            ))

        py_name = attr_name.value

        try:
            member = None

            if isinstance(lib_value, PythonLibValue):
                value, err = lib_value.get_member(py_name)
                if err:
                    return res.failure(RTError(
                        self.pos_start,
                        self.pos_end,
                        err.details,
                        self.context,
                    ))
                member = value
            else:
                return res.failure(RTError(
                    self.pos_start,
                    self.pos_end,
                    "First argument of py.call must be py.lib",
                    self.context,
                ))

            py_callable = member.py_object if isinstance(member, PythonLibValue) else member

            if callable(py_callable):
                py_args = [_omi_to_python_bridge(arg) for arg in call_args]
                py_kwargs = {
                    key: _omi_to_python_bridge(val)
                    for key, val in kwargs.items()
                }
                result = py_callable(*py_args, **py_kwargs)
            else:
                if call_args or kwargs:
                    return res.failure(RTError(
                        self.pos_start,
                        self.pos_end,
                        f"Python attribute '{py_name}' is not callable",
                        self.context,
                    ))
                result = _omi_to_python_bridge(member) if not isinstance(member, PythonLibValue) else member.py_object

            return res.success(_python_to_omi_bridge(result))
        except Exception as exc:
            return res.failure(RTError(
                self.pos_start,
                self.pos_end,
                f"py.call failed: {exc}",
                self.context,
            ))

    def execute_import(self, exec_ctx):
        module_name = exec_ctx.symbol_table.get("module_name")
        if not isinstance(module_name, String):
            return RTResult().failure(RTError(
                self.pos_start,
                self.pos_end,
                "py.import expects a string module name",
                exec_ctx,
            ))

        try:
            module = importlib.import_module(module_name.value)
            return RTResult().success(_module_to_omi_lib(module))
        except Exception as exc:
            return RTResult().failure(RTError(
                self.pos_start,
                self.pos_end,
                f"py.import failed: {exc}",
                exec_ctx,
            ))

    execute_import.arg_names = ["module_name"]

    def execute_eval(self, exec_ctx):
        code = exec_ctx.symbol_table.get("code")
        if not isinstance(code, String):
            return RTResult().failure(RTError(
                self.pos_start,
                self.pos_end,
                "py.eval expects a string",
                exec_ctx,
            ))

        try:
            result = _execute_python_code(code.value)
            return RTResult().success(_python_to_omi_bridge(result))
        except Exception as exc:
            return RTResult().failure(RTError(
                self.pos_start,
                self.pos_end,
                f"py.eval failed: {exc}",
                exec_ctx,
            ))

    execute_eval.arg_names = ["code"]


def create_python_module():
    symbol_table = SymbolTable()
    symbol_table.set("__type_lib__", _lib_type_annotation())

    for name in ("import", "call", "eval"):
        symbol_table.set(name, PythonBuiltInFunction(name))

    return Module("python", symbol_table)
