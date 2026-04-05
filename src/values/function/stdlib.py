from src.values.function.base import BaseFunction
from src.run.runtime import RTResult
from src.error.message.rt import RTError


class StdlibFunction(BaseFunction):
    def execute(self, args):
        res = RTResult()
        exec_ctx = self.generate_new_context()

        method_name = f"execute_{self.name}"
        method = getattr(self, method_name, self.no_visit_method)

        required = getattr(method, 'arg_names', [])
        optional = getattr(method, 'opt_names', [])
        factory  = getattr(method, 'opt_defaults_factory', None)
        defaults = factory() if factory else getattr(method, 'opt_defaults', [])

        min_args = len(required)
        max_args = len(required) + len(optional)

        if len(args) < min_args:
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                f"{min_args - len(args)} too few args passed into {self}",
                self.context,
            ))
        if len(args) > max_args:
            return res.failure(RTError(
                self.pos_start, self.pos_end,
                f"{len(args) - max_args} too many args passed into {self}",
                self.context,
            ))

        for i, name in enumerate(required):
            arg = args[i]
            arg.set_context(exec_ctx)
            exec_ctx.symbol_table.set(name, arg)

        for i, name in enumerate(optional):
            if min_args + i < len(args):
                arg = args[min_args + i]
                arg.set_context(exec_ctx)
                exec_ctx.symbol_table.set(name, arg)
            else:
                exec_ctx.symbol_table.set(name, defaults[i])

        return_value = res.register(method(exec_ctx))
        if res.should_return():
            return res
        return res.success(return_value)

    def no_visit_method(self, node, context):
        raise Exception(f"No execute_{self.name} method defined")
