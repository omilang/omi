from src.values.value import Value
from src.error.message.rt import RTError
from src.run.runtime import RTResult
from src.run.context import Context
from src.main.symboltable import SymbolTable

class BaseFunction(Value):
  def __init__(self, name):
    super().__init__()
    self.name = name or "<anonymous>"

  def generate_new_context(self):
    new_context = Context(self.name, self.context, self.pos_start)
    new_context.symbol_table = SymbolTable(new_context.parent.symbol_table)
    return new_context

  def check_args(self, arg_names, args):
    res = RTResult()
    expected = len(arg_names)
    got = len(args)

    if got > expected:
      return res.failure(RTError(
        self.pos_start, self.pos_end,
        f"'{self.name}' takes {expected} argument{'s' if expected != 1 else ''}, but {got} were given",
        self.context
      ))
    
    if got < expected:
      missing = arg_names[got:]
      missing_str = ", ".join(f"'{n}'" for n in missing)
      return res.failure(RTError(
        self.pos_start, self.pos_end,
        f"'{self.name}' missing argument{'s' if len(missing) != 1 else ''}: {missing_str}",
        self.context
      ))

    return res.success(None)

  def populate_args(self, arg_names, args, exec_ctx):
    for i in range(len(args)):
      arg_name = arg_names[i]
      arg_value = args[i]
      arg_value.set_context(exec_ctx)
      exec_ctx.symbol_table.set(arg_name, arg_value)

  def check_and_populate_args(self, arg_names, args, exec_ctx):
    res = RTResult()
    res.register(self.check_args(arg_names, args))
    if res.should_return(): return res
    self.populate_args(arg_names, args, exec_ctx)
    return res.success(None)

  def resolve_args(self, arg_names, defaults, args, kwargs, exec_ctx):
    res = RTResult()
    n = len(arg_names)

    if len(args) > n:
      return res.failure(RTError(
        self.pos_start, self.pos_end,
        f"'{self.name}' takes {n} argument{'s' if n != 1 else ''}, but {len(args)} were given",
        self.context
      ))

    filled = {}

    for i, val in enumerate(args):
      filled[arg_names[i]] = val

    for kw_name, kw_val in kwargs.items():
      if kw_name not in arg_names:
        return res.failure(RTError(
          self.pos_start, self.pos_end,
          f"'{self.name}' got unexpected keyword argument '{kw_name}'",
          self.context
        ))
      if kw_name in filled:
        return res.failure(RTError(
          self.pos_start, self.pos_end,
          f"'{self.name}' got duplicate value for argument '{kw_name}'",
          self.context
        ))
      filled[kw_name] = kw_val

    for i, name in enumerate(arg_names):
      if name not in filled:
        if defaults[i] is not None:
          defaults[i].set_context(exec_ctx)
          filled[name] = defaults[i]
        else:
          return res.failure(RTError(
            self.pos_start, self.pos_end,
            f"'{self.name}' missing required argument '{name}'",
            self.context
          ))

    for name, val in filled.items():
      val.set_context(exec_ctx)
      exec_ctx.symbol_table.set(name, val)

    return res.success(None)