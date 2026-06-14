from src.values.types.string import String
from src.values.types.list import List
from src.values.types.dict import Dict
from src.values.types.boolean import Boolean
from src.values.types.null import Null
from src.values.types.module import Module
from src.values.function.stdlib import StdlibFunction
from src.run.runtime import RTResult
from src.run.typecheck import check_type
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError


class DictBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)

    def copy(self):
        copy = DictBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function dict.{self.name}>"

    def _dict_arg(self, exec_ctx):
        value = exec_ctx.symbol_table.get("dict")
        if not isinstance(value, Dict):
            return None, RTError(
                self.pos_start, self.pos_end,
                "First argument must be a dict", exec_ctx
            )
        return value, None

    def _key_arg(self, exec_ctx):
        key = exec_ctx.symbol_table.get("key")
        if not isinstance(key, String):
            return None, RTError(
                self.pos_start, self.pos_end,
                "Second argument must be a string", exec_ctx
            )
        return key.value, None

    def _ensure_mutable(self, value, exec_ctx):
        if hasattr(value, "is_const") and value.is_const:
            return RTError(
                self.pos_start, self.pos_end,
                "Cannot modify a constant dict", exec_ctx
            )
        return None

    def _check_dict_type(self, value, exec_ctx):
        annotation = getattr(value, "type_annotation", None)
        if annotation is None:
            return None
        return check_type(value, annotation, exec_ctx, self.pos_start, self.pos_end)

    def execute_has(self, exec_ctx):
        dict_value, error = self._dict_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        key, error = self._key_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        return RTResult().success(Boolean(key in dict_value.entries))
    execute_has.arg_names = ["dict", "key"]

    def execute_get(self, exec_ctx):
        dict_value, error = self._dict_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        key, error = self._key_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        default = exec_ctx.symbol_table.get("default")
        return RTResult().success(dict_value.entries.get(key, default))
    execute_get.arg_names = ["dict", "key"]
    execute_get.opt_names = ["default"]
    execute_get.opt_defaults_factory = lambda: [Null()]

    def execute_set(self, exec_ctx):
        dict_value, error = self._dict_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        key, error = self._key_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        error = self._ensure_mutable(dict_value, exec_ctx)
        if error:
            return RTResult().failure(error)

        value = exec_ctx.symbol_table.get("value")
        had_key = key in dict_value.entries
        old_value = dict_value.entries.get(key)
        dict_value.entries[key] = value

        error = self._check_dict_type(dict_value, exec_ctx)
        if error:
            if had_key:
                dict_value.entries[key] = old_value
            else:
                del dict_value.entries[key]
            return RTResult().failure(error)

        return RTResult().success(dict_value)
    execute_set.arg_names = ["dict", "key", "value"]

    def execute_delete(self, exec_ctx):
        dict_value, error = self._dict_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        key, error = self._key_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        error = self._ensure_mutable(dict_value, exec_ctx)
        if error:
            return RTResult().failure(error)

        if key not in dict_value.entries:
            return RTResult().success(Boolean.false)

        old_value = dict_value.entries.pop(key)
        error = self._check_dict_type(dict_value, exec_ctx)
        if error:
            dict_value.entries[key] = old_value
            return RTResult().failure(error)

        return RTResult().success(Boolean.true)
    execute_delete.arg_names = ["dict", "key"]

    def execute_keys(self, exec_ctx):
        dict_value, error = self._dict_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        return RTResult().success(List([String(key) for key in dict_value.entries.keys()]))
    execute_keys.arg_names = ["dict"]

    def execute_values(self, exec_ctx):
        dict_value, error = self._dict_arg(exec_ctx)
        if error:
            return RTResult().failure(error)
        return RTResult().success(List(list(dict_value.entries.values())))
    execute_values.arg_names = ["dict"]


def create_dict_module():
    symbol_table = SymbolTable()
    for name in ("has", "get", "set", "delete", "keys", "values"):
        symbol_table.set(name, DictBuiltInFunction(name))
    return Module("dict", symbol_table)
