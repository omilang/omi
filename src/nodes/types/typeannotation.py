class TypeAnnotationNode:
    def __init__(self, type_parts, pos_start, pos_end, array_elem_types=None, max_size=None, type_params=None):
        self.type_parts = type_parts
        self.array_elem_types = array_elem_types
        self.max_size = max_size
        self.type_params = type_params or []
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        if self.array_elem_types is not None:
            inner = " | ".join(self.array_elem_types)
            base = f"[{inner}]"
        else:
            base = " | ".join(self.type_parts)
        if self.type_params:
            base = f"{base}<{', '.join(self.type_params)}>"
        if self.max_size is not None:
            return f"{base}({self.max_size})"
        return base


class DictTypeAnnotation:
    def __init__(self, fields, pos_start, pos_end, type_params=None, enum_name=None, enum_variants=None):
        self.fields = fields
        self.type_params = type_params or []
        self.enum_name = enum_name
        self.enum_variants = enum_variants or []
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        if self.enum_name:
            type_params = ""
            if self.type_params:
                type_params = f"<{', '.join(self.type_params)}>"
            variants = []
            for variant_name, payload_ann in self.enum_variants:
                if payload_ann is None:
                    variants.append(variant_name)
                else:
                    variants.append(f"{variant_name}({payload_ann})")
            return f"enum {self.enum_name}{type_params} = {{ {', '.join(variants)} }}"

        parts = []
        for name, ann in self.fields.items():
            parts.append(f"{name}<{ann}>")
        base = "{" + ", ".join(parts) + "}"
        if self.type_params:
            base = f"{base}<{', '.join(self.type_params)}>"
        return base
