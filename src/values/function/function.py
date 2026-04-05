import src.main.interpret as Interpreter
from src.values.function.base import BaseFunction
from src.values.types.number import Number
from src.run.runtime import RTResult
from src.run.typecheck import check_type

class Function(BaseFunction):
	def __init__(self, name, body_node, arg_names, should_auto_return,
	             return_type=None, arg_types=None, arg_defaults=None):
		super().__init__(name)
		self.body_node = body_node
		self.arg_names = arg_names
		self.should_auto_return = should_auto_return
		self.return_type = return_type
		self.arg_types = arg_types or [] 
		self.arg_defaults = arg_defaults or [None] * len(arg_names)

	def execute(self, args, kwargs=None):
		from src.values.types.void import Void
		from src.error.message.rt import RTError
		res = RTResult()
		interpreter = Interpreter.Interpreter()
		exec_ctx = self.generate_new_context()
		kwargs = kwargs or {}

		res.register(self.resolve_args(
			self.arg_names, self.arg_defaults, args, kwargs, exec_ctx
		))
		if res.should_return(): return res

		for i, name in enumerate(self.arg_names):
			if i < len(self.arg_types) and self.arg_types[i] is not None:
				val = exec_ctx.symbol_table.symbols.get(name)
				if val is not None:
					err = check_type(val, self.arg_types[i], exec_ctx,
					                 self.pos_start, self.pos_end)
					if err:
						return res.failure(err)

		value = res.register(interpreter.visit(self.body_node, exec_ctx))
		if res.should_return() and res.func_return_value == None: return res

		ret_value = (value if self.should_auto_return else None) or res.func_return_value or Void.void

		if self.return_type is not None:
			import src.var.flags as runtime_flags
			if not runtime_flags.notypes:
				ret_is_void = isinstance(ret_value, Void)
				ann_wants_void = "void" in self.return_type.type_parts
				ann_wants_null = "null" in self.return_type.type_parts

				if ann_wants_void and not ret_is_void:
					return res.failure(RTError(
						self.pos_start, self.pos_end,
						f"Function '{self.name}' declared void but returned a value. "
						f"Use bare 'return' to return nothing.",
						exec_ctx
					))
				if ann_wants_null and ret_is_void:
					return res.failure(RTError(
						self.pos_start, self.pos_end,
						f"Function '{self.name}' declared <null> but got void return. "
						f"Use 'return null' instead of bare 'return'.",
						exec_ctx
					))

				if not ann_wants_void:
					err = check_type(ret_value, self.return_type, exec_ctx,
					                 self.pos_start, self.pos_end)
					if err:
						return res.failure(err)

		return res.success(ret_value)

	def copy(self):
		copy = Function(self.name, self.body_node, self.arg_names, self.should_auto_return,
		                self.return_type, self.arg_types, self.arg_defaults)
		copy.set_context(self.context)
		copy.set_pos(self.pos_start, self.pos_end)
		return copy

	def __repr__(self):
		return f"<function {self.name}>"