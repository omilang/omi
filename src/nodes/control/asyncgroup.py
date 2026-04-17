class AsyncGroupNode:
    def __init__(self, name, params, body_node, pos_start, pos_end):
        self.name = name
        self.params = params or {}
        self.body_node = body_node
        self.pos_start = pos_start
        self.pos_end = pos_end
