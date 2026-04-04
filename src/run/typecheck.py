import src.var.flags as runtime_flags
from src.error.message.rt import RTError


def _build_type_map():
    from src.values.types.number import Number, Int, Float
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict
    from src.values.types.boolean import Boolean
    from src.values.types.null import Null
    from src.values.function.base import BaseFunction

    return {
        "int":    lambda v: isinstance(v, Int),
        "float":  lambda v: isinstance(v, Float),
        "number": lambda v: isinstance(v, Number),
        "string": lambda v: isinstance(v, String),
        "list":   lambda v: isinstance(v, List),
        "dict":   lambda v: isinstance(v, Dict),
        "bool":   lambda v: isinstance(v, Boolean),
        "func":   lambda v: isinstance(v, BaseFunction),
        "call":   lambda v: isinstance(v, BaseFunction),
        "null":   lambda v: isinstance(v, Null),
        "void":   lambda v: isinstance(v, Null),
        "every":  lambda v: True,
    }


def check_type(value, type_annotation, context, pos_start, pos_end):
    if runtime_flags.notypes:
        return None

    if type_annotation is None:
        return None

    type_map = _build_type_map()

    for part in type_annotation.type_parts:
        if part.startswith('"') and part.endswith('"'):
            from src.values.types.string import String
            literal_val = part[1:-1]
            if isinstance(value, String) and value.value == literal_val:
                return None
            continue

        resolved = context.symbol_table.get(f"__type_{part}__")
        if resolved is not None:
            err = check_type(value, resolved, context, pos_start, pos_end)
            if err is None:
                return None
            continue

        checker = type_map.get(part)
        if checker and checker(value):
            return None

    from src.values.types.string import String
    actual = _type_name(value)
    expected = str(type_annotation)
    return RTError(
        pos_start, pos_end,
        f"Type error: expected <{expected}>, got {actual}",
        context
    )


def _type_name(value):
    from src.values.types.number import Int, Float
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict
    from src.values.types.boolean import Boolean
    from src.values.types.null import Null
    from src.values.function.base import BaseFunction

    if isinstance(value, Boolean):
        return "bool"
    if isinstance(value, Null):
        return "null"
    if isinstance(value, Int):
        return "int"
    if isinstance(value, Float):
        return "float"
    if isinstance(value, String):
        return f'string ("{value.value}")'
    if isinstance(value, List):
        return "list"
    if isinstance(value, Dict):
        return "dict"
    if isinstance(value, BaseFunction):
        return "func (callable)"
    return type(value).__name__.lower()
