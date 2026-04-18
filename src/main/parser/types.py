import re

from src.error.message.invalidsyntax import InvalidSyntaxError
from src.main.parser.result import ParseResult
from src.nodes.types.enumdef import EnumDefNode, EnumVariantSignature
from src.nodes.types.traitdef import TraitDefNode, TraitMethodSignature
from src.nodes.types.typeannotation import TypeAnnotationNode, DictTypeAnnotation
from src.var.token import (
    TT_IDENTIFIER,
    TT_KEYWORD,
    TT_STRING,
    TT_INT,
    TT_LPAREN,
    TT_RPAREN,
    TT_LSQUARE,
    TT_RSQUARE,
    TT_LBRACE,
    TT_RBRACE,
    TT_LT,
    TT_GT,
    TT_EQ,
    TT_COMMA,
    TT_PIPE,
    TT_COLON,
    TT_DOT,
    TT_QUESTION,
    TT_NEWLINE,
    TT_E0F,
)
from src.var.type_system import CONCRETE_TYPE_NAMES


class ParserTypesMixin:
    def parse_type_annotation(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LT:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '<' for type annotation",
            ))

        res.register_advancement()
        self.advance()

        type_parts = []

        part = self._parse_single_type()
        if part is None:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected type name or string literal in type annotation",
            ))
        type_parts.append(part)
        if self.current_tok.type == TT_QUESTION:
            res.register_advancement()
            self.advance()
            if "null" not in type_parts:
                type_parts.append("null")

        while self.current_tok.type == TT_PIPE:
            res.register_advancement()
            self.advance()
            part = self._parse_single_type()
            if part is None:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected type name or string literal after '|'",
                ))
            type_parts.append(part)
            if self.current_tok.type == TT_QUESTION:
                res.register_advancement()
                self.advance()
                if "null" not in type_parts:
                    type_parts.append("null")

        if self.current_tok.type != TT_GT:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '>' to close type annotation",
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(TypeAnnotationNode(type_parts, pos_start, pos_end))

    def parse_array_type_annotation(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        res.register_advancement()
        self.advance()

        type_parts = []
        part = self._parse_single_type()
        if part is None:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected type name or string literal inside '[...]'",
            ))
        type_parts.append(part)

        while self.current_tok.type == TT_PIPE:
            res.register_advancement()
            self.advance()
            part = self._parse_single_type()
            if part is None:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected type name or string literal after '|'",
                ))
            type_parts.append(part)

        if self.current_tok.type != TT_RSQUARE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ']' to close array type annotation",
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(TypeAnnotationNode(["array"], pos_start, pos_end, array_elem_types=type_parts))

    def _try_parse_size_constraint(self, type_ann, res):
        if self.current_tok.type != TT_LPAREN:
            return type_ann

        is_array_ann = (
            (type_ann.array_elem_types is not None)
            or ("array" in type_ann.type_parts)
        )
        if not is_array_ann:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Size constraint (...) is only allowed for array type annotations",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_INT:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected a positive integer for array size constraint",
            ))

        size_val = self.current_tok.value
        if not isinstance(size_val, int) or size_val <= 0:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Array size must be a positive integer",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_RPAREN:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ')' after array size",
            ))

        res.register_advancement()
        self.advance()

        type_ann.max_size = size_val
        return type_ann

    def _parse_single_type(self):
        tok = self.current_tok
        if tok.type in (TT_IDENTIFIER, TT_KEYWORD):
            name = tok.value
            self.advance()
            if self.current_tok.type == TT_DOT:
                self.advance()
                if self.current_tok.type in (TT_IDENTIFIER, TT_KEYWORD):
                    name = name + "." + self.current_tok.value
                    self.advance()

            if self.current_tok.type == TT_LT:
                type_args = []
                self.advance()

                arg = self._parse_single_type()
                if arg is None:
                    self.reverse()
                    return name
                type_args.append(arg)

                while self.current_tok.type == TT_COMMA:
                    self.advance()
                    arg = self._parse_single_type()
                    if arg is None:
                        self.reverse()
                        break
                    type_args.append(arg)

                while self.current_tok.type == TT_PIPE:
                    self.advance()
                    arg = self._parse_single_type()
                    if arg is None:
                        self.reverse()
                        break
                    type_args.append(arg)

                if self.current_tok.type == TT_GT:
                    self.advance()
                    name = f"{name}<{', '.join(type_args)}>"

            return name
        if tok.type == TT_STRING:
            val = f'"{tok.value}"'
            self.advance()
            return val
        return None

    def _is_type_parameter_string(self, s):
        if not s:
            return False
        if "<" in s or "|" in s or s.startswith('"'):
            return False
        if s.lower() in CONCRETE_TYPE_NAMES:
            return False
        return s and (s[0].isupper() or (len(s) <= 3 and s.isalpha()))

    def _extract_type_params_from_annotation(self, ann):
        if ann is None or not ann.type_parts:
            return []

        type_str = ann.type_parts[0]

        if "<" in type_str and ">" in type_str:
            start = type_str.index("<") + 1
            end = type_str.index(">")
            params_str = type_str[start:end]
            params = [p.strip() for p in params_str.split(",")]
            params = [p for p in params if p]
            return params

        return []

    def _parse_explicit_type_params(self):
        if self.current_tok.type != TT_LT:
            return []

        saved_idx = self.tok_idx

        try:
            self.advance()

            type_params = []

            if self.current_tok.type != TT_IDENTIFIER:
                self.tok_idx = saved_idx
                self.update_current_tok()
                return []

            first_param = self.current_tok.value
            if not self._is_type_parameter_string(first_param):
                self.tok_idx = saved_idx
                self.update_current_tok()
                return []

            type_params.append(first_param)
            self.advance()

            while self.current_tok.type == TT_COMMA:
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    self.tok_idx = saved_idx
                    self.update_current_tok()
                    return []

                param = self.current_tok.value
                if not self._is_type_parameter_string(param):
                    self.tok_idx = saved_idx
                    self.update_current_tok()
                    return []

                type_params.append(param)
                self.advance()

            if self.current_tok.type != TT_GT:
                self.tok_idx = saved_idx
                self.update_current_tok()
                return []

            self.advance()
            return type_params
        except Exception:
            self.tok_idx = saved_idx
            self.update_current_tok()
            return []

    def _parse_dict_type_def(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()
        fields = {}

        res.register_advancement()
        self.advance()

        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        while self.current_tok.type != TT_RBRACE and self.current_tok.type != TT_E0F:
            if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected field name in dict type definition",
                ))

            field_name = self.current_tok.value
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_LT:
                ann = res.register(self.parse_type_annotation())
                if res.error:
                    return res
                fields[field_name] = ann
            elif self.current_tok.type == TT_COLON:
                res.register_advancement()
                self.advance()
                while self.current_tok.type == TT_NEWLINE:
                    res.register_advancement()
                    self.advance()
                if self.current_tok.type != TT_LBRACE:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected '{' for nested dict type",
                    ))
                nested = res.register(self._parse_dict_type_def())
                if res.error:
                    return res
                fields[field_name] = nested
            else:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected '<type>' or ': {{...}}' after field name '{field_name}'",
                ))

            if self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

        if self.current_tok.type != TT_RBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '}' to close dict type definition",
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(DictTypeAnnotation(fields, pos_start, pos_end))

    def enum_def(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "enum"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'enum'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected enum name after 'enum'",
            ))

        name_tok = self.current_tok
        res.register_advancement()
        self.advance()

        type_params = []
        if self.current_tok.type == TT_LT:
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected type parameter name after '<'",
                ))

            type_params.append(self.current_tok.value)
            res.register_advancement()
            self.advance()

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected type parameter name after ','",
                    ))

                type_params.append(self.current_tok.value)
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_GT:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '>' to close type parameters",
                ))
            res.register_advancement()
            self.advance()

        if self.current_tok.type != TT_EQ:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '=' after enum name",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_LBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '{' after '=' in enum definition",
            ))

        res.register_advancement()
        self.advance()

        variants = []

        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        while self.current_tok.type != TT_RBRACE and self.current_tok.type != TT_E0F:
            if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected variant name in enum definition",
                ))

            variant_name_tok = self.current_tok
            variant_name = variant_name_tok.value
            if not re.match(r"^[A-Z][a-zA-Z0-9_]*$", variant_name):
                return res.failure(InvalidSyntaxError(
                    variant_name_tok.pos_start,
                    variant_name_tok.pos_end,
                    "Enum variant names must start with an uppercase letter and use only letters, numbers, and underscores",
                ))

            res.register_advancement()
            self.advance()

            payload_type = None
            if self.current_tok.type == TT_LPAREN:
                res.register_advancement()
                self.advance()

                payload_part = self._parse_single_type()
                if payload_part is None:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected payload type in enum variant",
                    ))

                payload_type = TypeAnnotationNode([payload_part], variant_name_tok.pos_start, self.current_tok.pos_start.copy())

                if self.current_tok.type != TT_RPAREN:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ')' after enum variant payload type",
                    ))
                res.register_advancement()
                self.advance()

            variants.append(EnumVariantSignature(variant_name, payload_type, variant_name_tok.pos_start, variant_name_tok.pos_end))

            if self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

        if self.current_tok.type != TT_RBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '}' to close enum definition",
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(EnumDefNode(name_tok, variants, pos_start, pos_end, type_params))

    def trait_def(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "trait"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'trait'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected trait name after 'trait'",
            ))

        name_tok = self.current_tok
        pos_start = name_tok.pos_start.copy()
        res.register_advancement()
        self.advance()

        type_params = []
        if self.current_tok.type == TT_LT:
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected type parameter name after '<'",
                ))

            type_params.append(self.current_tok.value)
            res.register_advancement()
            self.advance()

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected type parameter name after ','",
                    ))

                type_params.append(self.current_tok.value)
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_GT:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '>' to close type parameters",
                ))
            res.register_advancement()
            self.advance()

        if self.current_tok.type != TT_EQ:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '=' after trait name",
            ))
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_LBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '{' after '=' in trait definition",
            ))
        res.register_advancement()
        self.advance()

        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        methods = []
        while self.current_tok.type != TT_RBRACE and self.current_tok.type != TT_E0F:
            if not self.current_tok.matches(TT_KEYWORD, "func"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'func' in trait definition",
                ))

            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_LT:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '<' for return type annotation in trait method",
                ))

            return_type = res.register(self.parse_type_annotation())
            if res.error:
                return res

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected method name",
                ))

            method_name = self.current_tok.value
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '(' after method name",
                ))

            res.register_advancement()
            self.advance()

            arg_types = []
            arg_names = []

            if self.current_tok.type != TT_RPAREN:
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected parameter name",
                    ))

                param_name = self.current_tok.value
                arg_names.append(param_name)
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_LT:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected '<' for parameter type annotation",
                    ))

                param_type = res.register(self.parse_type_annotation())
                if res.error:
                    return res
                arg_types.append(param_type)

                while self.current_tok.type == TT_COMMA:
                    res.register_advancement()
                    self.advance()

                    if self.current_tok.type != TT_IDENTIFIER:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected parameter name",
                        ))

                    param_name = self.current_tok.value
                    arg_names.append(param_name)
                    res.register_advancement()
                    self.advance()

                    if self.current_tok.type != TT_LT:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected '<' for parameter type annotation",
                        ))

                    param_type = res.register(self.parse_type_annotation())
                    if res.error:
                        return res
                    arg_types.append(param_type)

            if self.current_tok.type != TT_RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ')' after method parameters",
                ))

            res.register_advancement()
            self.advance()

            method_sig = TraitMethodSignature(
                method_name,
                return_type,
                arg_types,
                arg_names,
            )
            methods.append(method_sig)

            if self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

        if self.current_tok.type != TT_RBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '}' to close trait definition",
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        trait_node = TraitDefNode(name_tok, methods, pos_start, pos_end, type_params)
        return res.success(trait_node)
