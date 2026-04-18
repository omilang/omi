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
    from src.values.types.pythonlib import PythonLibValue
    from src.values.function.base import BaseFunction
    from src.values.future import FutureValue
    from src.stdlib.http import HTTPResponse

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
        "pylib":  lambda v: isinstance(v, PythonLibValue),
        "future": lambda v: isinstance(v, FutureValue),
        "httpresponse": lambda v: isinstance(v, HTTPResponse),
        "null":   lambda v: isinstance(v, Null),
        "void":   lambda v: isinstance(v, Void),
        "every":  lambda v: True,
    }


def _extract_generic_args_from_type_str(type_str):
    if '<' not in type_str or '>' not in type_str:
        return (type_str, [])
    
    start = type_str.index('<')
    end = type_str.rindex('>')
    base_type = type_str[:start]
    args_str = type_str[start+1:end]
    args = []
    current = ""
    depth = 0
    for char in args_str:
        if char == '<':
            depth += 1
            current += char
        elif char == '>':
            depth -= 1
            current += char
        elif char == ',' and depth == 0:
            args.append(current.strip())
            current = ""
        else:
            current += char
    if current.strip():
        args.append(current.strip())
    return (base_type, args)


def resolve_generics(annotation, type_map):
    if annotation is None:
        return None
    
    from src.nodes.types.typeannotation import TypeAnnotationNode, DictTypeAnnotation
    
    if isinstance(annotation, DictTypeAnnotation):
        resolved_fields = {}
        for field_name, field_ann in annotation.fields.items():
            resolved_fields[field_name] = resolve_generics(field_ann, type_map)

        resolved_variants = []
        for variant_name, payload_ann in getattr(annotation, 'enum_variants', []):
            resolved_variants.append((variant_name, resolve_generics(payload_ann, type_map)))
        
        result = DictTypeAnnotation(
            resolved_fields,
            annotation.pos_start,
            annotation.pos_end,
            annotation.type_params,
            enum_name=getattr(annotation, 'enum_name', None),
            enum_variants=resolved_variants,
        )
        return result
    
    if isinstance(annotation, TypeAnnotationNode):
        resolved_parts = []
        
        for part in annotation.type_parts:
            if part.startswith('"') and part.endswith('"'):
                resolved_parts.append(part)
                continue

            base_type, type_args = _extract_generic_args_from_type_str(part)

            if base_type in type_map:
                resolved_parts.append(type_map[base_type])
            else:
                if type_args:
                    resolved_args = []
                    for arg in type_args:
                        arg_base, arg_args = _extract_generic_args_from_type_str(arg)
                        if arg_base in type_map:
                            resolved_arg = type_map[arg_base]
                        else:
                            resolved_arg = arg
                        resolved_args.append(resolved_arg)
                    resolved_parts.append(f"{base_type}<{', '.join(resolved_args)}>")
                else:
                    resolved_parts.append(part)
        
        result = TypeAnnotationNode(
            resolved_parts,
            annotation.pos_start,
            annotation.pos_end,
            annotation.array_elem_types,
            annotation.max_size,
            annotation.type_params
        )
        return result
    
    return annotation


def _build_generic_type_map_from_annotation(annotation, type_params):
    if not type_params or not annotation or not annotation.type_parts:
        return {}
    
    type_map = {}
    
    for part in annotation.type_parts:
        if part.startswith('"') and part.endswith('"'):
            continue

        base_type, args = _extract_generic_args_from_type_str(part)

        for i, param in enumerate(type_params):
            if i < len(args):
                type_map[param] = args[i]
    
    return type_map


def build_enum_annotation(enum_def):
    from src.nodes.types.typeannotation import TypeAnnotationNode, DictTypeAnnotation

    payload_types = []
    enum_variants = []

    for variant in enum_def.variants:
        payload_type = variant.payload_type
        enum_variants.append((variant.name, payload_type))
        if payload_type is not None:
            payload_types.append(str(payload_type))

    fields = {
        "__tag": TypeAnnotationNode(["string"], enum_def.pos_start, enum_def.pos_end),
    }

    if payload_types:
        if any(payload is None for _, payload in enum_variants):
            payload_types.append("null")
        fields["value"] = TypeAnnotationNode(payload_types, enum_def.pos_start, enum_def.pos_end)

    return DictTypeAnnotation(
        fields,
        enum_def.pos_start,
        enum_def.pos_end,
        enum_def.type_params,
        enum_name=enum_def.name,
        enum_variants=enum_variants,
    )


def check_type(value, type_annotation, context, pos_start, pos_end):
    if runtime_flags.notypes:
        return None

    if type_annotation is None:
        return None

    from src.nodes.types.typeannotation import DictTypeAnnotation
    if isinstance(type_annotation, DictTypeAnnotation):
        if getattr(type_annotation, 'enum_name', None):
            return _check_enum_type(value, type_annotation, context, pos_start, pos_end)
        return _check_dict_type(value, type_annotation, context, pos_start, pos_end)

    from src.values.types.list import List
    from src.nodes.types.typeannotation import TypeAnnotationNode

    resolved_ann = _resolve_generic_annotation(type_annotation, context)
    if resolved_ann is not type_annotation:
        type_annotation = resolved_ann
        from src.nodes.types.typeannotation import DictTypeAnnotation
        if isinstance(type_annotation, DictTypeAnnotation):
            if getattr(type_annotation, 'enum_name', None):
                return _check_enum_type(value, type_annotation, context, pos_start, pos_end)
            return _check_dict_type(value, type_annotation, context, pos_start, pos_end)

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

    specific_err = None 

    for part in type_annotation.type_parts:
        if part.startswith('"') and part.endswith('"'):
            from src.values.types.string import String
            literal_val = part[1:-1]
            if isinstance(value, String) and value.value == literal_val:
                return None
            continue

        base_type, _ = _extract_generic_args_from_type_str(part)

        trait_def = context.symbol_table.get(f"__trait_{base_type}__")
        if trait_def is not None:
            err = check_structural_conformance(value, trait_def, context, pos_start, pos_end)
            if err is None:
                return None
            specific_err = err
            continue
        
        resolved = context.symbol_table.get(f"__type_{base_type}__")
        if resolved is not None:
            err = check_type(value, resolved, context, pos_start, pos_end)
            if err is None:
                return None
            specific_err = err
            continue

        checker = type_map.get(part) or type_map.get(base_type)
        if checker and checker(value):
            return None

    if specific_err is not None and len(type_annotation.type_parts) == 1:
        return specific_err

    from src.values.types.string import String
    actual = _type_name(value)
    expected = str(type_annotation)
    return RTError(
        pos_start, pos_end,
        f"Type error: expected <{expected}>, got {actual}",
        context
    )


def _resolve_generic_annotation(annotation, context):
    if annotation is None or not annotation.type_parts:
        return annotation
    
    from src.nodes.types.typeannotation import TypeAnnotationNode
    
    if not isinstance(annotation, TypeAnnotationNode):
        return annotation
    
    for part in annotation.type_parts:
        if '<' in part and '>' in part:
            base_type, type_args = _extract_generic_args_from_type_str(part)

            generic_def = context.symbol_table.get(f"__type_{base_type}__")
            if generic_def is not None:
                if hasattr(generic_def, 'type_params') and generic_def.type_params:
                    type_map = {}
                    for i, param in enumerate(generic_def.type_params):
                        if i < len(type_args):
                            type_map[param] = type_args[i]

                    if type_map:
                        resolved_def = resolve_generics(generic_def, type_map)
                        if resolved_def is not generic_def:
                            return resolved_def
    
    return annotation


def _type_name(value):
    from src.values.types.number import Int, Float
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict
    from src.values.types.boolean import Boolean
    from src.values.types.null import Null
    from src.values.types.void import Void
    from src.values.types.pythonlib import PythonLibValue
    from src.values.function.base import BaseFunction
    from src.values.future import FutureValue

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
    if isinstance(value, PythonLibValue):
        return "pylib"
    if isinstance(value, FutureValue):
        return "future"
    return type(value).__name__.lower()


def _check_dict_type(value, dict_ann, context, pos_start, pos_end):
    from src.values.types.dict import Dict
    from src.nodes.types.typeannotation import TypeAnnotationNode, DictTypeAnnotation

    if not isinstance(value, Dict):
        actual = _type_name(value)
        return RTError(
            pos_start, pos_end,
            f"Type error: expected dict type '{dict_ann}', got {actual}. Use the declared fields and types for that alias.",
            context
        )

    for field_name, field_ann in dict_ann.fields.items():
        is_nullable = (
            isinstance(field_ann, TypeAnnotationNode) and "null" in field_ann.type_parts
        )

        if field_name not in value.entries:
            if is_nullable:
                continue
            return RTError(
                pos_start, pos_end,
                f"Dict is missing required field '{field_name}' for type '{dict_ann}'",
                context
            )

        field_val = value.entries[field_name]
        err = check_type(field_val, field_ann, context, pos_start, pos_end)
        if err:
            return RTError(
                pos_start, pos_end,
                f"Field '{field_name}': {err.details}",
                context
            )

    return None


def _check_enum_type(value, enum_ann, context, pos_start, pos_end):
    from src.values.types.dict import Dict
    from src.values.types.string import String

    if not isinstance(value, Dict):
        actual = _type_name(value)
        return RTError(
            pos_start, pos_end,
            f"Type error: expected enum type '{enum_ann.enum_name}', got {actual}. Enums are stored as tagged dicts.",
            context,
        )

    tag_value = value.entries.get("__tag")
    if tag_value is None:
        return RTError(
            pos_start, pos_end,
            f"Enum '{enum_ann.enum_name}' is missing required field '__tag'. Use '__tag' to select a variant.",
            context,
        )

    if not isinstance(tag_value, String):
        return RTError(
            pos_start, pos_end,
            f"Enum '{enum_ann.enum_name}' field '__tag' must be a string",
            context,
        )

    tag_name = tag_value.value
    variant_map = {name: payload for name, payload in enum_ann.enum_variants}
    if tag_name not in variant_map:
        available_variants = ", ".join(sorted(variant_map.keys())) or "(none)"
        return RTError(
            pos_start, pos_end,
            f"Enum '{enum_ann.enum_name}' does not define variant '{tag_name}'. Available variants: {available_variants}",
            context,
        )

    payload_ann = variant_map[tag_name]
    allowed_keys = {"__tag"}
    if payload_ann is not None:
        allowed_keys.add("value")

    extra_keys = [key for key in value.entries.keys() if key not in allowed_keys]
    if extra_keys:
        return RTError(
            pos_start, pos_end,
            f"Enum '{enum_ann.enum_name}' variant '{tag_name}' has unexpected field(s): {', '.join(sorted(extra_keys))}",
            context,
        )

    if payload_ann is None:
        if "value" in value.entries:
            return RTError(
                pos_start, pos_end,
                f"Enum '{enum_ann.enum_name}' variant '{tag_name}' does not take a payload",
                context,
            )
        return None

    if "value" not in value.entries:
        return RTError(
            pos_start, pos_end,
            f"Enum '{enum_ann.enum_name}' variant '{tag_name}' is missing payload field 'value'",
            context,
        )

    payload_value = value.entries["value"]
    err = check_type(payload_value, payload_ann, context, pos_start, pos_end)
    if err:
        return RTError(
            pos_start, pos_end,
            f"Enum '{enum_ann.enum_name}' variant '{tag_name}': {err.details}",
            context,
        )

    return None


def _types_match(type_ann1, type_ann2):
    from src.nodes.types.typeannotation import TypeAnnotationNode
    
    if type_ann1 is None or type_ann2 is None:
        return type_ann1 is type_ann2
    
    str1 = str(type_ann1)
    str2 = str(type_ann2)
    
    return str1 == str2


def check_structural_conformance(value, trait_def, context, pos_start, pos_end):
    from src.values.types.dict import Dict
    from src.values.types.list import List
    from src.nodes.types.typeannotation import TypeAnnotationNode
    from src.values.function.base import BaseFunction
    
    trait_name = trait_def.name
    
    value_type_name = None

    if hasattr(value, 'type_name') and value.type_name:
        value_type_name = value.type_name

    if value_type_name is None and hasattr(value, 'type_annotation') and value.type_annotation:
        ann = value.type_annotation
        if hasattr(ann, 'type_parts') and ann.type_parts:
            type_name = ann.type_parts[0]
            if '<' in type_name:
                type_name = type_name[:type_name.index('<')]
            value_type_name = type_name

    if value_type_name is None:
        return RTError(
            pos_start, pos_end,
            f"Cannot check trait conformance for untyped value",
            context
        )

    for method in trait_def.methods:
        method_name = method.name
        method_return_type = method.return_type
        method_arg_types = method.arg_types

        method_key = f"__method_{value_type_name}_{method_name}__"
        func_value = context.symbol_table.get(method_key)

        if func_value is None:
            return RTError(
                pos_start, pos_end,
                f"Type '{value_type_name}' does not implement trait '{trait_name}' (missing method '{method_name}')",
                context
            )

        if hasattr(func_value, 'return_type') and hasattr(func_value, 'arg_types'):
            func_arg_types = func_value.arg_types[1:] if len(func_value.arg_types) > 1 else []
            expected_arg_types = method_arg_types[1:] if len(method_arg_types) > 1 else method_arg_types

            if len(func_arg_types) != len(expected_arg_types):
                return RTError(
                    pos_start, pos_end,
                    f"Type '{value_type_name}' method '{method_name}' has wrong number of parameters",
                    context
                )

            for i, (func_arg, trait_arg) in enumerate(zip(func_arg_types, expected_arg_types)):
                if not _types_match(func_arg, trait_arg):
                    return RTError(
                        pos_start, pos_end,
                        f"Type '{value_type_name}' method '{method_name}' parameter {i+1} type mismatch",
                        context
                    )
            
            if not _types_match(func_value.return_type, method_return_type):
                return RTError(
                    pos_start, pos_end,
                    f"Type '{value_type_name}' method '{method_name}' has wrong return type",
                    context
                )

    return None


def _get_value_type_name(value):
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
    elif isinstance(value, Void):
        return "void"
    elif isinstance(value, Null):
        return "null"
    elif isinstance(value, Int):
        return "int"
    elif isinstance(value, Float):
        return "float"
    elif isinstance(value, String):
        return "string"
    elif isinstance(value, List):
        return "array"
    elif isinstance(value, Dict):
        if hasattr(value, 'type_name') and value.type_name:
            return value.type_name
        return "dict"
    elif isinstance(value, BaseFunction):
        return "call"
    
    return None


