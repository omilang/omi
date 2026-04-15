class EnumVariantSignature:
    def __init__(self, name, payload_type=None, pos_start=None, pos_end=None):
        self.name = name
        self.payload_type = payload_type
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        if self.payload_type is None:
            return self.name
        return f"{self.name}({self.payload_type})"


class EnumDefNode:
    def __init__(self, name_tok, variants, pos_start, pos_end, type_params=None):
        self.name_tok = name_tok
        self.name = name_tok.value if name_tok else ""
        self.variants = variants or []
        self.type_params = type_params or []
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        type_params_str = ""
        if self.type_params:
            type_params_str = f"<{', '.join(self.type_params)}>"

        variants_str = ", ".join(repr(variant) for variant in self.variants)
        return f"enum {self.name}{type_params_str} = {{ {variants_str} }}"