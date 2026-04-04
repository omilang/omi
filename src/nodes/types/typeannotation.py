class TypeAnnotationNode:
    def __init__(self, type_parts, pos_start, pos_end):
        self.type_parts = type_parts
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return " | ".join(self.type_parts)
