class UseDirectiveNode:
    def __init__(self, directive, pos_start, pos_end):
        self.directive = directive
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f'UseDirectiveNode({self.directive})'
