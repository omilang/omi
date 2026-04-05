import src.var.flags as runtime_flags
from src.error.message.rt import RTError


def _build_type_map():
    from src.values.types.number import Number, Int, Float
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict
    from src.values.types.boolean import Boolean
    from src.values.types.null import Null
    from src.values.types.void import Void
    from src.values.function.base import BaseFunction

    return {
        "int":    lambda v: isinstance(v, Int),
        "float":  lambda v: isinstance(v, Float),
        "number": lambda v: isinstance(v, Number),
        "string": lambda v: isinstance(v, String),
        "array":  lambda v: isinstance(v, List),
        "dict":   lambda v: isinstance(v, Dict),
        "bool":   lambda v: isinstance(v, Boolean),
        "func":   lambda v: isinstance(v, BaseFunction),
        "call":   lambda v: isinstance(v, BaseFunction),
        "null":   lambda v: isinstance(v, Null),
        "void":   lambda v: isinstance(v, Void),
        "every":  lambda v: True,
    }


def check_type(value, type_annotation, context, pos_start, pos_end):
    if runtime_flags.notypes:
        return None

    if type_annotation is None:
        return None

    from src.values.types.list import List
    from src.nodes.types.typeannotation import TypeAnnotationNode

    if isinstance(value, List) and type_annotation.array_elem_types is not None:
        elem_ann = TypeAnnotationNode(
            type_annotation.array_elem_types,
            type_annotation.pos_start,
            type_annotation.pos_end,
        )
        for i, elem in enumerate(value.elements):
            err = check_type(elem, elem_ann, context, pos_start, pos_end)
            if err:
                return RTError(
                    pos_start, pos_end,
                    f"Array element at index {i}: {err.details}",
                    context,
                )

    if isinstance(value, List) and type_annotation.max_size is not None:
        if len(value.elements) > type_annotation.max_size:
            return RTError(
                pos_start, pos_end,
                f"Array exceeds maximum size of {type_annotation.max_size} "
                f"(got {len(value.elements)} elements)",
                context,
            )

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
    from src.values.types.void import Void
    from src.values.function.base import BaseFunction

    if isinstance(value, Boolean):
        return "bool"
    if isinstance(value, Void):
        return "void"
    if isinstance(value, Null):
        return "null"
    if isinstance(value, Int):
        return "int"
    if isinstance(value, Float):
        return "float"
    if isinstance(value, String):
        return f'string ("{value.value}")'
    if isinstance(value, List):
        return "array"
    if isinstance(value, Dict):
        return "dict"
    if isinstance(value, BaseFunction):
        return "call"
    return type(value).__name__.lower()
