class FuncDefNode:
	def __init__(self, var_name_tok, arg_name_toks, body_node, should_auto_return,
	             return_type=None, arg_types=None, arg_defaults=None, type_params=None, is_async=False):
		self.var_name_tok = var_name_tok
		self.arg_name_toks = arg_name_toks
		self.body_node = body_node
		self.should_auto_return = should_auto_return
		self.is_async = is_async
		self.return_type = return_type
		self.arg_types = arg_types or []
		self.arg_defaults = arg_defaults or [None] * len(arg_name_toks)
		self.type_params = type_params or []

		if self.var_name_tok:
			self.pos_start = self.var_name_tok.pos_start
		elif len(self.arg_name_toks) > 0:
			self.pos_start = self.arg_name_toks[0].pos_start
		else:
			self.pos_start = self.body_node.pos_start

		self.pos_end = self.body_node.pos_end