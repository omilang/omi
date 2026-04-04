"""Utilities for converting between Python native types and Omi Value objects."""


def python_to_omi(value):
    from src.values.types.number import Number
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict

    if isinstance(value, bool):
        return Number(1) if value else Number(0)
    if isinstance(value, (int, float)):
        return Number(value)
    if isinstance(value, str):
        return String(value)
    if isinstance(value, list):
        return List([python_to_omi(item) for item in value])
    if isinstance(value, dict):
        return Dict({str(k): python_to_omi(v) for k, v in value.items()})
    if value is None:
        from src.values.types.number import Number
        return Number(0)
    return String(str(value))


def omi_to_python(value):
    from src.values.types.number import Number
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict

    if isinstance(value, Number):
        return value.value
    if isinstance(value, String):
        return value.value
    if isinstance(value, List):
        return [omi_to_python(item) for item in value.elements]
    if isinstance(value, Dict):
        return {k: omi_to_python(v) for k, v in value.entries.items()}
    return None
