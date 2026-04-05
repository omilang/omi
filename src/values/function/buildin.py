import os
import src.run.run as run
import src.var.flags as flags
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.dict import Dict
from src.values.types.boolean import Boolean
from src.run.runtime import RTResult
from src.error.message.rt import RTError
from src.values.function.base import BaseFunction
from src.var.keyword import FILE_FORMAT

class BuiltInFunction(BaseFunction):
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
    copy = BuiltInFunction(self.name)
    copy.set_context(self.context)
    copy.set_pos(self.pos_start, self.pos_end)
    return copy

  def __repr__(self):
    return f"<built-in function {self.name}>"

  def execute_print(self, exec_ctx):
    if not flags.noecho:
      print(str(exec_ctx.symbol_table.get("value")))
    return RTResult().success(Number.null)
  execute_print.arg_names = ["value"]
  
  def execute_print_ret(self, exec_ctx):
    return RTResult().success(String(str(exec_ctx.symbol_table.get("value"))))
  execute_print_ret.arg_names = ["value"]
  
  def execute_input(self, exec_ctx):
    text = input(">>> ")
    return RTResult().success(String(text))
  execute_input.arg_names = []

  def execute_input_int(self, exec_ctx):
    while True:
      text = input(">>> ")
      try:
        number = int(text)
        break
      except ValueError:
        print(f"'{text}' must be an integer. Try again!")
    return RTResult().success(Number(number))
  execute_input_int.arg_names = []

  def execute_clear(self, exec_ctx):
    os.system("cls" if os.name == "nt" else "cls") 
    return RTResult().success(Number.null)
  execute_clear.arg_names = []

  def execute_is_number(self, exec_ctx):
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), Number)))
  execute_is_number.arg_names = ["value"]

  def execute_is_int(self, exec_ctx):
    from src.values.types.number import Int
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), Int)))
  execute_is_int.arg_names = ["value"]

  def execute_is_float(self, exec_ctx):
    from src.values.types.number import Float
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), Float)))
  execute_is_float.arg_names = ["value"]

  def execute_is_bool(self, exec_ctx):
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), Boolean)))
  execute_is_bool.arg_names = ["value"]

  def execute_is_string(self, exec_ctx):
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), String)))
  execute_is_string.arg_names = ["value"]

  def execute_is_array(self, exec_ctx):
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), List)))
  execute_is_array.arg_names = ["value"]

  def execute_is_dict(self, exec_ctx):
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), Dict)))
  execute_is_dict.arg_names = ["value"]

  def execute_is_function(self, exec_ctx):
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), BaseFunction)))
  execute_is_function.arg_names = ["value"]

  def execute_append(self, exec_ctx):
    list_ = exec_ctx.symbol_table.get("list")
    value = exec_ctx.symbol_table.get("value")

    if not isinstance(list_, List):
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "First argument must be array",
        exec_ctx
      ))

    if list_.max_size is not None and len(list_.elements) >= list_.max_size:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        f"Array exceeds maximum size of {list_.max_size}",
        exec_ctx
      ))

    if list_.elem_annotation is not None:
      from src.run.typecheck import check_type
      err = check_type(value, list_.elem_annotation, exec_ctx, self.pos_start, self.pos_end)
      if err:
        return RTResult().failure(err)

    list_.elements.append(value)
    return RTResult().success(Number.null)
  execute_append.arg_names = ["list", "value"]

  def execute_pop(self, exec_ctx):
    list_ = exec_ctx.symbol_table.get("list")
    index = exec_ctx.symbol_table.get("index")

    if not isinstance(list_, List):
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "First argument must be array",
        exec_ctx
      ))

    if not isinstance(index, Number):
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Second argument must be number",
        exec_ctx
      ))

    try:
      element = list_.elements.pop(index.value)
    except:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Element at this index could not be removed from list because index is out of bounds",
        exec_ctx
      ))
    return RTResult().success(element)
  execute_pop.arg_names = ["list", "index"]

  def execute_extend(self, exec_ctx):
    listA = exec_ctx.symbol_table.get("listA")
    listB = exec_ctx.symbol_table.get("listB")

    if not isinstance(listA, List):
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "First argument must be array",
        exec_ctx
      ))

    if not isinstance(listB, List):
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Second argument must be array",
        exec_ctx
      ))

    if listA.max_size is not None:
      if len(listA.elements) + len(listB.elements) > listA.max_size:
        return RTResult().failure(RTError(
          self.pos_start, self.pos_end,
          f"Array exceeds maximum size of {listA.max_size}",
          exec_ctx
        ))

    if listA.elem_annotation is not None:
      from src.run.typecheck import check_type
      for i, elem in enumerate(listB.elements):
        err = check_type(elem, listA.elem_annotation, exec_ctx, self.pos_start, self.pos_end)
        if err:
          return RTResult().failure(RTError(
            self.pos_start, self.pos_end,
            f"Element at index {i} in second array: {err.details}",
            exec_ctx
          ))

    listA.elements.extend(listB.elements)
    return RTResult().success(Number.null)
  execute_extend.arg_names = ["listA", "listB"]
    
  def execute_len(self, exec_ctx):
      list_ = exec_ctx.symbol_table.get("list")

      if not isinstance(list_, List):
        return RTResult().failure(RTError(
          self.pos_start, self.pos_end,
          "Argument must be array",
          exec_ctx
        ))

      return RTResult().success(Number(len(list_.elements)))
  execute_len.arg_names = ["list"]

  def execute_eval(self, exec_ctx):
    if not flags.eval_enabled:
      print("Warning: eval() is disabled. Add '@use eval' to your file to enable it.")
      return RTResult().success(Number.null)

    code = exec_ctx.symbol_table.get("code")

    if not isinstance(code, String):
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Argument must be string",
        exec_ctx
      ))

    code = code.value

    result, error, _ = run.run("<eval>", code)
    
    if error:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        f"Failed to execute eval\n" +
        error.as_string(),
        exec_ctx
      ))

    return RTResult().success(result.elements[0] if len(result.elements) == 1 else result)
  execute_eval.arg_names = ["code"]

  def execute_is_null(self, exec_ctx):
    from src.values.types.null import Null
    return RTResult().success(Boolean(isinstance(exec_ctx.symbol_table.get("value"), Null)))
  execute_is_null.arg_names = ["value"]

  def execute_typeof(self, exec_ctx):
    from src.values.types.number import Int, Float
    from src.values.types.null import Null
    from src.values.types.void import Void
    value = exec_ctx.symbol_table.get("value")
    if isinstance(value, Boolean):
      type_str = "bool"
    elif isinstance(value, Void):
      type_str = "void"
    elif isinstance(value, Null):
      type_str = "null"
    elif isinstance(value, Int):
      type_str = "int"
    elif isinstance(value, Float):
      type_str = "float"
    elif isinstance(value, String):
      type_str = "string"
    elif isinstance(value, List):
      type_str = "array"
    elif isinstance(value, Dict):
      type_str = "dict"
    elif isinstance(value, BaseFunction):
      type_str = "call"
    else:
      type_str = type(value).__name__.lower()
    return RTResult().success(String(type_str))
  execute_typeof.arg_names = ["value"]

  def execute_to_string(self, exec_ctx):
    value = exec_ctx.symbol_table.get("value")
    return RTResult().success(String(str(value)))
  execute_to_string.arg_names = ["value"]

  def execute_to_int(self, exec_ctx):
    from src.values.types.number import Int, Float
    value = exec_ctx.symbol_table.get("value")
    if isinstance(value, Int):
      return RTResult().success(value)
    if isinstance(value, Float):
      return RTResult().success(Int(int(value.value)))
    if isinstance(value, Boolean):
      return RTResult().success(Int(1 if value.value else 0))
    if isinstance(value, String):
      try:
        return RTResult().success(Int(int(value.value)))
      except ValueError:
        return RTResult().failure(RTError(
          self.pos_start, self.pos_end,
          f'Cannot convert string "{value.value}" to int',
          exec_ctx
        ))
    return RTResult().failure(RTError(
      self.pos_start, self.pos_end,
      f"Cannot convert {type(value).__name__.lower()} to int",
      exec_ctx
    ))
  execute_to_int.arg_names = ["value"]

  def execute_to_float(self, exec_ctx):
    from src.values.types.number import Int, Float
    value = exec_ctx.symbol_table.get("value")
    if isinstance(value, Float):
      return RTResult().success(value)
    if isinstance(value, Int):
      return RTResult().success(Float(float(value.value)))
    if isinstance(value, Boolean):
      return RTResult().success(Float(1.0 if value.value else 0.0))
    if isinstance(value, String):
      try:
        return RTResult().success(Float(float(value.value)))
      except ValueError:
        return RTResult().failure(RTError(
          self.pos_start, self.pos_end,
          f'Cannot convert string "{value.value}" to float',
          exec_ctx
        ))
    return RTResult().failure(RTError(
      self.pos_start, self.pos_end,
      f"Cannot convert {type(value).__name__.lower()} to float",
      exec_ctx
    ))
  execute_to_float.arg_names = ["value"]

  def execute_to_bool(self, exec_ctx):
    from src.values.types.number import Int, Float
    value = exec_ctx.symbol_table.get("value")
    if isinstance(value, Boolean):
      return RTResult().success(value)
    if isinstance(value, (Int, Float)):
      if value.value == 1 or value.value == 1.0:
        return RTResult().success(Boolean.true)
      if value.value == 0 or value.value == 0.0:
        return RTResult().success(Boolean.false)
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        f"Cannot convert number {value.value} to bool: only 0 and 1 are allowed",
        exec_ctx
      ))
    if isinstance(value, String):
      if value.value == "true":
        return RTResult().success(Boolean.true)
      if value.value == "false":
        return RTResult().success(Boolean.false)
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        f'Cannot convert string "{value.value}" to bool: only "true" and "false" are allowed',
        exec_ctx
      ))
    return RTResult().failure(RTError(
      self.pos_start, self.pos_end,
      f"Cannot convert {type(value).__name__.lower()} to bool",
      exec_ctx
    ))
  execute_to_bool.arg_names = ["value"]