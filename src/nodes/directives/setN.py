class SetDirectiveNode:
    def __init__(self, lhs, rhs, pos_start, pos_end):
        self.lhs = lhs
        self.rhs = rhs
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f'SetDirectiveNode({self.lhs!r} as {self.rhs!r})'
