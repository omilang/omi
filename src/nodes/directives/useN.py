class UseDirectiveNode:
    def __init__(self, directive, pos_start, pos_end, value=None, has_as=False):
        self.directive = directive
        self.value = value
        self.has_as = has_as
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        if self.value is None:
            return f'UseDirectiveNode({self.directive})'
        if self.has_as:
            return f'UseDirectiveNode({self.directive} as {self.value})'
        return f'UseDirectiveNode({self.directive} {self.value})'
