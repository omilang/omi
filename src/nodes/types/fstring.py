class FStringNode:
    def __init__(self, parts, pos_start, pos_end):
        self.parts = parts
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f'FStringNode({self.parts})'
