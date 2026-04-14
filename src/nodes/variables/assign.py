class VarAssignNode:
	def __init__(self, var_name_tok, value_node, type_annotation=None, is_reassign=False, is_const=False):
		self.var_name_tok = var_name_tok
		self.value_node = value_node
		self.type_annotation = type_annotation
		self.is_reassign = is_reassign
		self.is_const = is_const

		self.pos_start = self.var_name_tok.pos_start
		self.pos_end = self.value_node.pos_end if self.value_node else self.var_name_tok.pos_end