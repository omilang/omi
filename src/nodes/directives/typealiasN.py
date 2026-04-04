class TypeAliasNode:
    def __init__(self, name_tok, type_annotation, pos_start, pos_end):
        self.name_tok = name_tok
        self.type_annotation = type_annotation
        self.pos_start = pos_start
        self.pos_end = pos_end
