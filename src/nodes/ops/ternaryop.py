class TernaryOpNode:
    def __init__(self, true_node, cond_node, false_node):
        self.true_node = true_node
        self.cond_node = cond_node
        self.false_node = false_node
        self.pos_start = true_node.pos_start
        self.pos_end = false_node.pos_end

    def __repr__(self):
        return f'({self.true_node} ~ {self.cond_node} ~ {self.false_node})'
