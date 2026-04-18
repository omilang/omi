class HookNode:
    def __init__(self, hook_type, body_node, pos_start, pos_end):
        self.hook_type = hook_type
        self.body_node = body_node
        self.pos_start = pos_start
        self.pos_end = pos_end
