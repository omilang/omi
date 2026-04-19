import src.main.interpret as Interpreter
from src.values.function.base import BaseFunction
from src.values.types.number import Number
from src.run.runtime import RTResult
from src.run.typecheck import check_type
from src.run.typecheck import resolve_generics
from src.run.typecheck import _extract_generic_args_from_type_str

class Function(BaseFunction):
	def __init__(self, name, body_node, arg_names, should_auto_return,
	             return_type=None, arg_types=None, arg_defaults=None, type_params=None, is_async=False):
		super().__init__(name)
		self.body_node = body_node
		self.arg_names = arg_names
		self.should_auto_return = should_auto_return
		self.is_async = is_async
		self.return_type = return_type
		self.arg_types = arg_types or [] 
		self.arg_defaults = arg_defaults or [None] * len(arg_names)
		self.type_params = type_params or []

	def _type_name(self, value):
		from src.values.types.number import Int, Float
		from src.values.types.string import String
		from src.values.types.list import List
		from src.values.types.dict import Dict
		from src.values.types.boolean import Boolean
		from src.values.types.null import Null
		from src.values.types.void import Void
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
			return "string"
		if isinstance(value, List):
			return "array"
		if isinstance(value, Dict):
			return "dict"
		if isinstance(value, BaseFunction):
			return "call"
		if isinstance(value, FutureValue):
			return "future"
		return type(value).__name__.lower()

	def _infer_type_map_from_value(self, value, annotation, type_map):
		from src.nodes.types.typeannotation import TypeAnnotationNode, DictTypeAnnotation
		from src.values.types.list import List
		from src.values.types.dict import Dict

		if annotation is None:
			return True

		if isinstance(annotation, DictTypeAnnotation):
			if not isinstance(value, Dict):
				return False
			for field_name, field_ann in annotation.fields.items():
				if field_name not in value.entries:
					continue
				if not self._infer_type_map_from_value(value.entries[field_name], field_ann, type_map):
					return False
			return True

		if not isinstance(annotation, TypeAnnotationNode):
			return True

		if annotation.array_elem_types is not None:
			if not isinstance(value, List):
				return False
			if len(annotation.array_elem_types) == 1 and value.elements:
				elem_ann = TypeAnnotationNode(annotation.array_elem_types, annotation.pos_start, annotation.pos_end)
				for elem in value.elements:
					if not self._infer_type_map_from_value(elem, elem_ann, type_map):
						return False
			return True

		if not annotation.type_parts:
			return True

		part = annotation.type_parts[0]
		base_type, type_args = _extract_generic_args_from_type_str(part)

		if not type_args and base_type in self.type_params:
			inferred = self._type_name(value)
			existing = type_map.get(base_type)
			if existing is not None and existing != inferred:
				return False
			type_map[base_type] = inferred
			return True

		if type_args:
			if base_type in self.type_params:
				resolved_args = []
				for arg in type_args:
					if arg in self.type_params and arg in type_map:
						resolved_args.append(type_map[arg])
					else:
						resolved_args.append(arg)
				type_map[base_type] = f"{base_type}<{', '.join(resolved_args)}>"
			return True

		return True

	def resolve_call_type_map(self, args, kwargs=None):
		kwargs = kwargs or {}
		type_map = {}
		filled = {}
		for i, arg in enumerate(args):
			if i < len(self.arg_names):
				filled[self.arg_names[i]] = arg
		for name, value in kwargs.items():
			filled[name] = value
		for i, name in enumerate(self.arg_names):
			if i >= len(self.arg_types):
				continue
			annotation = self.arg_types[i]
			if annotation is None or name not in filled:
				continue
			if not self._infer_type_map_from_value(filled[name], annotation, type_map):
				return None
		return type_map

	def resolve_return_type(self, args, kwargs=None):
		type_map = self.resolve_call_type_map(args, kwargs)
		if type_map is None or self.return_type is None:
			return self.return_type
		return resolve_generics(self.return_type, type_map)

	def execute(self, args, kwargs=None):
		from src.values.types.void import Void
		from src.error.message.rt import RTError
		res = RTResult()
		interpreter = Interpreter.Interpreter()
		exec_ctx = self.generate_new_context()
		exec_ctx.in_async_function = self.is_async
		kwargs = kwargs or {}

		res.register(self.resolve_args(
			self.arg_names, self.arg_defaults, args, kwargs, exec_ctx
		))
		if res.should_return(): return res

		type_map = self.resolve_call_type_map(args, kwargs)
		if type_map is None:
			for i, arg_name in enumerate(self.arg_names):
				if i < len(self.arg_types) and self.arg_types[i] is not None:
					return res.failure(RTError(
						self.pos_start, self.pos_end,
						f"Function '{self.name}' could not infer generic type parameters from argument '{arg_name}'",
						exec_ctx
					))
			type_map = {}

		resolved_arg_types = []
		for ann in self.arg_types:
			if ann is None:
				resolved_arg_types.append(None)
			else:
				resolved_arg_types.append(resolve_generics(ann, type_map) if type_map else ann)

		resolved_return_type = resolve_generics(self.return_type, type_map) if (self.return_type is not None and type_map) else self.return_type

		for i, name in enumerate(self.arg_names):
			if i < len(resolved_arg_types) and resolved_arg_types[i] is not None:
				val = exec_ctx.symbol_table.symbols.get(name)
				if val is not None:
					err = check_type(val, resolved_arg_types[i], exec_ctx,
					                 self.pos_start, self.pos_end)
					if err:
						return res.failure(err)

		interpreter._push_defer_scope(exec_ctx)

		value = res.register(interpreter.visit(self.body_node, exec_ctx))
		if res.should_return() and res.func_return_value == None:
			return interpreter._finalize_scope_result(exec_ctx, res)

		ret_value = (value if self.should_auto_return else None) or res.func_return_value or Void.void

		if resolved_return_type is not None:
			import src.var.flags as runtime_flags
			if not runtime_flags.notypes:
				ret_is_void = isinstance(ret_value, Void)
				ann_wants_void = hasattr(resolved_return_type, 'type_parts') and "void" in resolved_return_type.type_parts
				ann_wants_null = hasattr(resolved_return_type, 'type_parts') and "null" in resolved_return_type.type_parts

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
					err = check_type(ret_value, resolved_return_type, exec_ctx,
					                 self.pos_start, self.pos_end)
					if err:
						return interpreter._finalize_scope_result(exec_ctx, res.failure(err))

		return interpreter._finalize_scope_result(exec_ctx, res.success(ret_value))

	async def execute_async(self, args, kwargs=None):
		res = self.execute(args, kwargs)
		if res.error:
			raise res.error
		return res.value

	def copy(self):
		copy = Function(self.name, self.body_node, self.arg_names, self.should_auto_return,
		                self.return_type, self.arg_types, self.arg_defaults, self.type_params, self.is_async)
		copy.set_context(self.context)
		copy.set_pos(self.pos_start, self.pos_end)
		return copy

	def __repr__(self):
		return f"<function {self.name}>"