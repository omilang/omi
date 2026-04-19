class TryNode:
    def __init__(self, try_body, catch_var_tok, catch_body, final_body, pos_start, pos_end):
        self.try_body = try_body
        self.catch_var_tok = catch_var_tok
        self.catch_body = catch_body
        self.final_body = final_body
        self.pos_start = pos_start
        self.pos_end = pos_end


class DeferNode:
    def __init__(self, expr_node, pos_start, pos_end):
        self.expr_node = expr_node
        self.pos_start = pos_start
        self.pos_end = pos_end


class PatternNode:
    def __init__(self, kind, name=None, capture_var_tok=None, value=None, pos_start=None, pos_end=None):
        self.kind = kind
        self.name = name
        self.capture_var_tok = capture_var_tok
        self.value = value
        self.pos_start = pos_start
        self.pos_end = pos_end


class CaseNode:
    def __init__(self, pattern, body, pos_start, pos_end):
        self.pattern = pattern
        self.body = body
        self.pos_start = pos_start
        self.pos_end = pos_end


class MatchNode:
    def __init__(self, expr, cases, pos_start, pos_end):
        self.expr = expr
        self.cases = cases
        self.pos_start = pos_start
        self.pos_end = pos_end