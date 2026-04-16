class CallNode:
	def __init__(self, node_to_call, arg_nodes, kwarg_nodes=None, is_async=False):
		self.node_to_call = node_to_call
		self.arg_nodes = arg_nodes
		self.kwarg_nodes = kwarg_nodes or {}
		self.is_async = is_async

		self.pos_start = self.node_to_call.pos_start

		if len(self.arg_nodes) > 0:
			self.pos_end = self.arg_nodes[len(self.arg_nodes) - 1].pos_end
		elif self.kwarg_nodes:
			self.pos_end = list(self.kwarg_nodes.values())[-1].pos_end
		else:
			self.pos_end = self.node_to_call.pos_end