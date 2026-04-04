def python_to_omi(value):
    from src.values.types.number import Number, Int, Float
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict
    from src.values.types.boolean import Boolean
    from src.values.types.null import Null

    if isinstance(value, bool):
        return Boolean.true if value else Boolean.false
    if isinstance(value, int):
        return Int(value)
    if isinstance(value, float):
        return Float(value)
    if isinstance(value, str):
        return String(value)
    if isinstance(value, list):
        return List([python_to_omi(item) for item in value])
    if isinstance(value, dict):
        return Dict({str(k): python_to_omi(v) for k, v in value.items()})
    if value is None:
        return Null()
    return String(str(value))


def omi_to_python(value):
    from src.values.types.number import Number
    from src.values.types.string import String
    from src.values.types.list import List
    from src.values.types.dict import Dict
    from src.values.types.boolean import Boolean
    from src.values.types.null import Null

    if isinstance(value, Null):
        return None
    if isinstance(value, Boolean):
        return value.value
    if isinstance(value, Number):
        return value.value
    if isinstance(value, String):
        return value.value
    if isinstance(value, List):
        return [omi_to_python(item) for item in value.elements]
    if isinstance(value, Dict):
        return {k: omi_to_python(v) for k, v in value.entries.items()}
    return None
