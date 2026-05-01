import os
import src.run.run as run
import src.var.flags as flags
import src.var.ansi as ansi
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

    required = getattr(method, "arg_names", [])
    optional = getattr(method, "opt_names", [])
    defaults_factory = getattr(method, "opt_defaults_factory", None)
    defaults = defaults_factory() if defaults_factory else getattr(method, "opt_defaults", [])
    var_arg_name = getattr(method, "var_arg_name", None)

    min_args = len(required)
    max_args = None if var_arg_name else min_args + len(optional)

    if len(args) < min_args:
      missing = required[len(args):]
      missing_str = ", ".join(f"'{name}'" for name in missing)
      return res.failure(RTError(
        self.pos_start, self.pos_end,
        f"'{self.name}' missing argument{'s' if len(missing) != 1 else ''}: {missing_str}",
        self.context
      ))

    if max_args is not None and len(args) > max_args:
      return res.failure(RTError(
        self.pos_start, self.pos_end,
        f"'{self.name}' takes {max_args} argument{'s' if max_args != 1 else ''}, but {len(args)} were given",
        self.context
      ))

    for i, name in enumerate(required):
      arg_value = args[i]
      arg_value.set_context(exec_ctx)
      exec_ctx.symbol_table.set(name, arg_value)

    for i, name in enumerate(optional):
      arg_index = min_args + i
      arg_value = args[arg_index] if arg_index < len(args) else defaults[i]
      if arg_value is not None:
        arg_value.set_context(exec_ctx)
      exec_ctx.symbol_table.set(name, arg_value)

    if var_arg_name is not None:
      var_args = List(args[min_args + len(optional):]).set_context(exec_ctx)
      exec_ctx.symbol_table.set(var_arg_name, var_args)

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

  def _emit(self, values, sep="", end=""):
    if flags.noecho:
      return
    text = sep.join(str(value) for value in values)
    if flags.no_colors:
      text = ansi.strip_ansi(text)
    print(text, end=end)
    flags.repl_output_emitted = True
    flags.repl_output_ended_with_newline = str(end).endswith("\n")

  def execute_print(self, exec_ctx):
    value = exec_ctx.symbol_table.get("value")
    self._emit([value])
    return RTResult().success(Number.null)
  execute_print.arg_names = ["value"]

  def execute_println(self, exec_ctx):
    value = exec_ctx.symbol_table.get("value")
    end = exec_ctx.symbol_table.get("end")
    self._emit([value], end=str(end) if end is not None else "\n")
    return RTResult().success(Number.null)
  execute_println.arg_names = ["value"]
  execute_println.opt_names = ["end"]
  execute_println.opt_defaults_factory = lambda: [String("\n")]

  def execute_output(self, exec_ctx):
    values = exec_ctx.symbol_table.get("values")
    items = values.elements if isinstance(values, List) else []
    self._emit(items, sep=" ", end="\n")
    return RTResult().success(Number.null)
  execute_output.var_arg_name = "values"

  def execute_reprint(self, exec_ctx):
    return RTResult().success(String(str(exec_ctx.symbol_table.get("value"))))
  execute_reprint.arg_names = ["value"]

  def execute_input(self, exec_ctx):
    text = input(">>> ")
    return RTResult().success(String(text))
  execute_input.arg_names = []

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

    if hasattr(list_, 'is_const') and list_.is_const:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Cannot modify a constant array",
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

    if hasattr(list_, 'is_const') and list_.is_const:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Cannot modify a constant array",
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

    if hasattr(listA, 'is_const') and listA.is_const:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Cannot modify a constant array",
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
      value = exec_ctx.symbol_table.get("value")

      if isinstance(value, List):
        return RTResult().success(Number(len(value.elements)))

      if isinstance(value, String):
        return RTResult().success(Number(len(value.value)))

      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "Argument must be array or string",
        exec_ctx
      ))
  execute_len.arg_names = ["value"]

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

    result, error, _ = run.run("<eval>", code, preserve_flags=True)
    
    if error:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        f"Failed to execute eval\n" +
        error.as_string(),
        exec_ctx
      ))

    return RTResult().success(result.elements[0] if len(result.elements) == 1 else result)
  execute_eval.arg_names = ["code"]

  def execute_cancel(self, exec_ctx):
    target = exec_ctx.symbol_table.get("target")

    from src.values.future import FutureValue
    from src.values.async_group import AsyncGroupValue

    if isinstance(target, FutureValue):
      target.cancel()
      return RTResult().success(Number.null)

    if isinstance(target, AsyncGroupValue):
      target.cancel()
      return RTResult().success(Number.null)

    return RTResult().failure(RTError(
      self.pos_start, self.pos_end,
      "cancel() expects a future or async group",
      exec_ctx
    ))
  execute_cancel.arg_names = ["target"]

  def execute_range(self, exec_ctx):
    from src.values.types.number import Int, Float
    args = exec_ctx.symbol_table.get("args")
    items = args.elements if isinstance(args, List) else []

    if len(items) < 1 or len(items) > 3:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        f"range() takes 1 to 3 arguments, but {len(items)} were given",
        exec_ctx
      ))

    for item in items:
      if not isinstance(item, (Int, Float, Number)):
        return RTResult().failure(RTError(
          self.pos_start, self.pos_end,
          "range() arguments must be numbers",
          exec_ctx
        ))

    if len(items) == 1:
      start_v, stop_v, step_v = 0, int(items[0].value), 1
    elif len(items) == 2:
      start_v, stop_v, step_v = int(items[0].value), int(items[1].value), 1
    else:
      start_v, stop_v, step_v = int(items[0].value), int(items[1].value), int(items[2].value)

    if step_v == 0:
      return RTResult().failure(RTError(
        self.pos_start, self.pos_end,
        "range() step argument must not be zero",
        exec_ctx
      ))

    result = List([Int(i) for i in range(start_v, stop_v, step_v)])
    result.set_context(exec_ctx)
    return RTResult().success(result)
  execute_range.var_arg_name = "args"

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