from src.values.function.base import BaseFunction
from src.run.runtime import RTResult
from src.error.message.rt import RTError


class StdlibFunction(BaseFunction):
    def execute(self, args, kwargs=None):
        res = RTResult()
        exec_ctx = self.generate_new_context()
        kwargs = kwargs or {}

        method_name = f"execute_{self.name}"
        method = getattr(self, method_name, self.no_visit_method)

        required = getattr(method, 'arg_names', [])
        optional = getattr(method, 'opt_names', [])
        factory = getattr(method, 'opt_defaults_factory', None)
        defaults = factory() if factory else getattr(method, 'opt_defaults', [])

        arg_names = required + optional
        arg_defaults = [None] * len(required) + list(defaults)

        res.register(self.resolve_args(arg_names, arg_defaults, args, kwargs, exec_ctx))
        if res.should_return():
            return res

        return_value = res.register(method(exec_ctx))
        if res.should_return():
            return res
        return res.success(return_value)

    def no_visit_method(self, node, context):
        raise Exception(f"No execute_{self.name} method defined")
