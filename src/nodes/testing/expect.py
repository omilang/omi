class ExpectNode:
    def __init__(self, expr_node, message_node, pos_start, pos_end):
        self.expr_node = expr_node
        self.message_node = message_node
        self.pos_start = pos_start
        self.pos_end = pos_end
