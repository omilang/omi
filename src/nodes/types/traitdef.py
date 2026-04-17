class TraitMethodSignature:
    def __init__(self, name, return_type, arg_types, arg_names=None):
        self.name = name
        self.return_type = return_type
        self.arg_types = arg_types or []
        self.arg_names = arg_names or [f"arg{i}" for i in range(len(self.arg_types))]
    
    def __repr__(self):
        args_str = ", ".join(f"{name}<{ty}>" for name, ty in zip(self.arg_names, self.arg_types))
        return f"func<{self.return_type}> {self.name}({args_str})"


class TraitDefNode:
    def __init__(self, name_tok, methods, pos_start, pos_end, type_params=None):
        self.name_tok = name_tok
        self.name = name_tok.value if name_tok else ""
        self.methods = methods or []
        self.type_params = type_params or []
        self.pos_start = pos_start
        self.pos_end = pos_end
    
    def __repr__(self):
        type_params_str = ""
        if self.type_params:
            type_params_str = f"<{', '.join(self.type_params)}>"
        
        methods_str = "\n    ".join(str(m) for m in self.methods)
        return f"trait {self.name}{type_params_str} = {{\n    {methods_str}\n}}"
