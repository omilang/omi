class IncDecNode:
    def __init__(self, target_node, op_tok, is_postfix):
        self.target_node = target_node
        self.op_tok = op_tok
        self.is_postfix = is_postfix

        if is_postfix:
            self.pos_start = self.target_node.pos_start
            self.pos_end = self.op_tok.pos_end
        else:
            self.pos_start = self.op_tok.pos_start
            self.pos_end = self.target_node.pos_end

    def __repr__(self):
        if self.is_postfix:
            return f"({self.target_node}{self.op_tok})"
        return f"({self.op_tok}{self.target_node})"
