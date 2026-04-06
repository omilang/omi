class DictSubscriptNode:
    def __init__(self, base_node, index_node, pos_start, pos_end):
        self.base_node = base_node
        self.index_node = index_node
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f'({self.base_node}[{self.index_node}])'
