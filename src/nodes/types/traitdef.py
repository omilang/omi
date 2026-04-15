"""
TraitDefNode - represents a trait definition.
A trait is a structural contract that a type must satisfy.

Example:
    trait Serializable = {
        func<string> to_json()
    }
"""


class TraitMethodSignature:
    """Represents a single method signature in a trait."""
    
    def __init__(self, name, return_type, arg_types, arg_names=None):
        """
        name: method name (str)
        return_type: TypeAnnotationNode - the return type
        arg_types: list of TypeAnnotationNode - parameter types
        arg_names: list of str - parameter names (optional, for documentation)
        """
        self.name = name
        self.return_type = return_type
        self.arg_types = arg_types or []
        self.arg_names = arg_names or [f"arg{i}" for i in range(len(self.arg_types))]
    
    def __repr__(self):
        args_str = ", ".join(f"{name}<{ty}>" for name, ty in zip(self.arg_names, self.arg_types))
        return f"func<{self.return_type}> {self.name}({args_str})"


class TraitDefNode:
    """Represents a trait definition node."""
    
    def __init__(self, name_tok, methods, pos_start, pos_end, type_params=None):
        """
        name_tok: Token with the trait name
        methods: list of TraitMethodSignature - trait methods
        pos_start: Position
        pos_end: Position
        type_params: list of str - generic type parameters (e.g., ["T"])
        """
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
