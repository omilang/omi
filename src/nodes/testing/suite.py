class SuiteNode:
    def __init__(self, name_tok, body_nodes, hooks, pos_start, pos_end):
        self.name_tok = name_tok
        self.body_nodes = body_nodes or []
        self.hooks = hooks or {}
        self.pos_start = pos_start
        self.pos_end = pos_end
