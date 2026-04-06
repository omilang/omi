class TypeAnnotationNode:
    def __init__(self, type_parts, pos_start, pos_end, array_elem_types=None, max_size=None):
        self.type_parts = type_parts
        self.array_elem_types = array_elem_types
        self.max_size = max_size
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        if self.array_elem_types is not None:
            inner = " | ".join(self.array_elem_types)
            base = f"[{inner}]"
        else:
            base = " | ".join(self.type_parts)
        if self.max_size is not None:
            return f"{base}({self.max_size})"
        return base


class DictTypeAnnotation:
    def __init__(self, fields, pos_start, pos_end):
        self.fields = fields
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        parts = []
        for name, ann in self.fields.items():
            parts.append(f"{name}<{ann}>")
        return "{" + ", ".join(parts) + "}"
