import math as _math
import random as _random
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.module import Module
from src.values.function.base import BaseFunction
from src.run.runtime import RTResult
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class MathBuiltInFunction(BaseFunction):
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
        copy = MathBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function math.{self.name}>"

    def execute_abs(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if not isinstance(n, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a number",
                exec_ctx
            ))
        return RTResult().success(Number(abs(n.value)))
    execute_abs.arg_names = ["n"]

    def execute_round(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if not isinstance(n, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a number",
                exec_ctx
            ))
        return RTResult().success(Number(round(n.value)))
    execute_round.arg_names = ["n"]

    def execute_floor(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if not isinstance(n, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a number",
                exec_ctx
            ))
        return RTResult().success(Number(_math.floor(n.value)))
    execute_floor.arg_names = ["n"]

    def execute_ceil(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if not isinstance(n, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a number",
                exec_ctx
            ))
        return RTResult().success(Number(_math.ceil(n.value)))
    execute_ceil.arg_names = ["n"]

    def execute_min(self, exec_ctx):
        lst = exec_ctx.symbol_table.get("lst")
        if not isinstance(lst, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a list",
                exec_ctx
            ))
        if len(lst.elements) == 0:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "List must not be empty",
                exec_ctx
            ))
        for el in lst.elements:
            if not isinstance(el, Number):
                return RTResult().failure(RTError(
                    self.pos_start, self.pos_end,
                    "All list elements must be numbers",
                    exec_ctx
                ))
        return RTResult().success(Number(min(el.value for el in lst.elements)))
    execute_min.arg_names = ["lst"]

    def execute_max(self, exec_ctx):
        lst = exec_ctx.symbol_table.get("lst")
        if not isinstance(lst, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a list",
                exec_ctx
            ))
        if len(lst.elements) == 0:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "List must not be empty",
                exec_ctx
            ))
        for el in lst.elements:
            if not isinstance(el, Number):
                return RTResult().failure(RTError(
                    self.pos_start, self.pos_end,
                    "All list elements must be numbers",
                    exec_ctx
                ))
        return RTResult().success(Number(max(el.value for el in lst.elements)))
    execute_max.arg_names = ["lst"]

    def execute_sqrt(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if not isinstance(n, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a number",
                exec_ctx
            ))
        if n.value < 0:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Cannot take square root of a negative number",
                exec_ctx
            ))
        return RTResult().success(Number(_math.sqrt(n.value)))
    execute_sqrt.arg_names = ["n"]

    def execute_log(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        base = exec_ctx.symbol_table.get("base")

        if not isinstance(n, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First argument must be a number",
                exec_ctx
            ))
        if n.value <= 0:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be positive",
                exec_ctx
            ))

        try:
            if isinstance(base, Number) and base.value != 0:
                result = _math.log(n.value, base.value)
            else:
                result = _math.log(n.value)
            return RTResult().success(Number(result))
        except Exception as e:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                f"log failed: {e}",
                exec_ctx
            ))
    execute_log.arg_names = ["n", "base"]

    def execute_exp(self, exec_ctx):
        n = exec_ctx.symbol_table.get("n")
        if not isinstance(n, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a number",
                exec_ctx
            ))
        return RTResult().success(Number(_math.exp(n.value)))
    execute_exp.arg_names = ["n"]

    def execute_random(self, exec_ctx):
        return RTResult().success(Number(_random.random()))
    execute_random.arg_names = []

    def execute_randint(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        b = exec_ctx.symbol_table.get("b")

        if not isinstance(a, Number) or not isinstance(b, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Both arguments must be numbers",
                exec_ctx
            ))
        return RTResult().success(Number(_random.randint(int(a.value), int(b.value))))
    execute_randint.arg_names = ["a", "b"]

    def execute_randfloat(self, exec_ctx):
        a = exec_ctx.symbol_table.get("a")
        b = exec_ctx.symbol_table.get("b")
        digits = exec_ctx.symbol_table.get("digits")

        if not isinstance(a, Number) or not isinstance(b, Number):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "First two arguments must be numbers",
                exec_ctx
            ))

        value = _random.uniform(a.value, b.value)

        if isinstance(digits, Number):
            value = round(value, int(digits.value))

        return RTResult().success(Number(value))
    execute_randfloat.arg_names = ["a", "b", "digits"]

    def execute_choice(self, exec_ctx):
        lst = exec_ctx.symbol_table.get("lst")
        if not isinstance(lst, List):
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "Argument must be a list",
                exec_ctx
            ))
        if len(lst.elements) == 0:
            return RTResult().failure(RTError(
                self.pos_start, self.pos_end,
                "List must not be empty",
                exec_ctx
            ))
        return RTResult().success(_random.choice(lst.elements).copy())
    execute_choice.arg_names = ["lst"]


def create_math_module():
    symbol_table = SymbolTable()

    funcs = ["abs", "round", "floor", "ceil", "min", "max",
             "sqrt", "log", "exp", "random", "randint", "randfloat", "choice"]
    for name in funcs:
        symbol_table.set(name, MathBuiltInFunction(name))

    symbol_table.set("pi", Number(_math.pi))
    symbol_table.set("e", Number(_math.e))
    symbol_table.set("inf", Number(_math.inf))

    return Module("math", symbol_table)
