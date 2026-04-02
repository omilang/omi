class ImportNode:
	def __init__(self, module_path_tok, alias_tok, pos_start, pos_end):
		self.module_path_tok = module_path_tok
		self.alias_tok = alias_tok

		self.pos_start = pos_start
		self.pos_end = pos_end
