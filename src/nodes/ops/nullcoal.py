class NullCoalNode:
    def __init__(self, left, right):
        self.left = left
        self.right = right
        self.pos_start = left.pos_start
        self.pos_end = right.pos_end

    def __repr__(self):
        return f'({self.left} ?? {self.right})'
