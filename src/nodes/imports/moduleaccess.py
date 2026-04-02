class ModuleAccessNode:
	def __init__(self, module_node, attribute_tok):
		self.module_node = module_node
		self.attribute_tok = attribute_tok

		self.pos_start = self.module_node.pos_start
		self.pos_end = self.attribute_tok.pos_end
