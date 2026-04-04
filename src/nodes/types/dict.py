class DictNode:
    def __init__(self, pair_nodes, pos_start, pos_end):
        # pair_nodes: list of (key_node, value_node) — key_node is always a StringNode
        self.pair_nodes = pair_nodes
        self.pos_start = pos_start
        self.pos_end = pos_end
