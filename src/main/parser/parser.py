import re

from src.var.token import (
    TT_INT, TT_FLOAT, TT_STRING, TT_FSTRING,
    TT_MUL, TT_DIV,
    TT_POW,
    TT_PLUS, TT_MINUS,
    TT_LPAREN, TT_RPAREN,
    TT_LSQUARE, TT_RSQUARE,
    TT_LBRACE, TT_RBRACE,
    TT_E0F,
    TT_KEYWORD, TT_IDENTIFIER, TT_EQ,
    TT_EE, TT_NE, TT_LT, TT_GT,
                  TT_LTE, TT_GTE,
    TT_COMMA, TT_ARROW, TT_PIPE,
    TT_NEWLINE,
    TT_COLON,
    TT_DOT, TT_AT, TT_TILDE,
    TT_QUESTION, TT_NULLCOAL,
    TOKEN_DISPLAY_NAMES,
)

from src.nodes.types.number import NumberNode
from src.nodes.ops.binop import BinOpNode
from src.nodes.ops.unaryop import UnaryOpNode
from src.nodes.variables.access import VarAccessNode
from src.nodes.variables.assign import VarAssignNode
from src.nodes.condition.ifN import IfNode
from src.nodes.loops.forN import ForNode
from src.nodes.loops.whileN import WhileNode
from src.nodes.function.funcdef import FuncDefNode
from src.nodes.function.call import CallNode
from src.nodes.types.string import StringNode
from src.nodes.types.fstring import FStringNode
from src.nodes.types.list import ListNode
from src.nodes.types.dict import DictNode
from src.nodes.jump.breakN import BreakNode
from src.nodes.jump.returnN import ReturnNode
from src.nodes.jump.continueN import ContinueNode
from src.nodes.imports.importN import ImportNode
from src.nodes.imports.moduleaccess import ModuleAccessNode
from src.nodes.ops.ternaryop import TernaryOpNode
from src.nodes.ops.nullcoal import NullCoalNode
from src.nodes.directives.useN import UseDirectiveNode
from src.nodes.directives.setN import SetDirectiveNode
from src.nodes.directives.typealiasN import TypeAliasNode
from src.nodes.types.typeannotation import TypeAnnotationNode, DictTypeAnnotation
from src.nodes.types.subscript import DictSubscriptNode
from src.nodes.types.enumdef import EnumDefNode, EnumVariantSignature
from src.nodes.types.traitdef import TraitDefNode, TraitMethodSignature
from src.error.message.invalidsyntax import InvalidSyntaxError
from src.main.parser.result import ParseResult

def _sub_parse(expr_src, pos_start):
    from src.main.lexer import Lexer
    lexer = Lexer("<fstring>", expr_src)
    tokens, err = lexer.make_tokens()
    if err:
        return None
    sub_parser = Parser(tokens)
    result = sub_parser.expr()
    if result.error:
        return None
    return result.node

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.advance()

    def advance(self):
        self.tok_idx += 1
        self.update_current_tok()
        return self.current_tok

    def reverse(self, amount=1):
        self.tok_idx -= amount
        self.update_current_tok()
        return self.current_tok

    def update_current_tok(self):
        if self.tok_idx >= 0 and self.tok_idx < len(self.tokens):
            self.current_tok = self.tokens[self.tok_idx]

    def describe_token(self, tok=None):
        tok = tok or self.current_tok

        if tok.type in (TT_IDENTIFIER, TT_KEYWORD, TT_INT, TT_FLOAT):
            return repr(tok.value)
        if tok.type in (TT_STRING, TT_FSTRING):
            return "string"
        return TOKEN_DISPLAY_NAMES.get(tok.type, tok.type.lower())

    def parse_type_annotation(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LT:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '<' for type annotation"
            ))

        res.register_advancement()
        self.advance()

        type_parts = []

        part = self._parse_single_type()
        if part is None:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected type name or string literal in type annotation"
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
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected type name or string literal after '|'"
                ))
            type_parts.append(part)
            if self.current_tok.type == TT_QUESTION:
                res.register_advancement()
                self.advance()
                if "null" not in type_parts:
                    type_parts.append("null")

        if self.current_tok.type != TT_GT:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '>' to close type annotation"
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
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected type name or string literal inside '[...]'"
            ))
        type_parts.append(part)

        while self.current_tok.type == TT_PIPE:
            res.register_advancement()
            self.advance()
            part = self._parse_single_type()
            if part is None:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected type name or string literal after '|'"
                ))
            type_parts.append(part)

        if self.current_tok.type != TT_RSQUARE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected ']' to close array type annotation"
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(TypeAnnotationNode(["array"], pos_start, pos_end, array_elem_types=type_parts))

    def _try_parse_size_constraint(self, type_ann, res):
        if self.current_tok.type != TT_LPAREN:
            return type_ann

        is_array_ann = (
            (type_ann.array_elem_types is not None) or
            ("array" in type_ann.type_parts)
        )
        if not is_array_ann:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Size constraint (...) is only allowed for array type annotations"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_INT:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected a positive integer for array size constraint"
            ))

        size_val = self.current_tok.value
        if not isinstance(size_val, int) or size_val <= 0:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Array size must be a positive integer"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_RPAREN:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected ')' after array size"
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
                    name = name + '.' + self.current_tok.value
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

    def _extract_type_params_from_annotation(self, ann):
        if ann is None or not ann.type_parts:
            return []
        
        type_str = ann.type_parts[0]

        if '<' in type_str and '>' in type_str:
            start = type_str.index('<') + 1
            end = type_str.index('>')
            params_str = type_str[start:end]
            params = [p.strip() for p in params_str.split(',')]
            params = [p for p in params if p]
            return params
        
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
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected field name in dict type definition"
                ))

            field_name = self.current_tok.value
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_LT:
                ann = res.register(self.parse_type_annotation())
                if res.error: return res
                fields[field_name] = ann
            elif self.current_tok.type == TT_COLON:
                res.register_advancement()
                self.advance()
                while self.current_tok.type == TT_NEWLINE:
                    res.register_advancement()
                    self.advance()
                if self.current_tok.type != TT_LBRACE:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected '{' for nested dict type"
                    ))
                nested = res.register(self._parse_dict_type_def())
                if res.error: return res
                fields[field_name] = nested
            else:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected '<type>' or ': {{...}}' after field name '{field_name}'"
                ))

            if self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

        if self.current_tok.type != TT_RBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '}' to close dict type definition"
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(DictTypeAnnotation(fields, pos_start, pos_end))

    def enum_def(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, 'enum'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected 'enum'"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected enum name after 'enum'"
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
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected type parameter name after '<'"
                ))

            type_params.append(self.current_tok.value)
            res.register_advancement()
            self.advance()

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected type parameter name after ','"
                    ))

                type_params.append(self.current_tok.value)
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_GT:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected '>' to close type parameters"
                ))
            res.register_advancement()
            self.advance()

        if self.current_tok.type != TT_EQ:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '=' after enum name"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_LBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '{' after '=' in enum definition"
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
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected variant name in enum definition"
                ))

            variant_name_tok = self.current_tok
            variant_name = variant_name_tok.value
            if not re.match(r'^[A-Z][a-zA-Z0-9_]*$', variant_name):
                return res.failure(InvalidSyntaxError(
                    variant_name_tok.pos_start, variant_name_tok.pos_end,
                    "Enum variant names must start with an uppercase letter and use only letters, numbers, and underscores"
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
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected payload type in enum variant"
                    ))

                payload_type = TypeAnnotationNode([payload_part], variant_name_tok.pos_start, self.current_tok.pos_start.copy())

                if self.current_tok.type != TT_RPAREN:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected ')' after enum variant payload type"
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
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '}' to close enum definition"
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(EnumDefNode(name_tok, variants, pos_start, pos_end, type_params))
    
    def parse(self):
        res = self.statements()
        if not res.error and self.current_tok.type != TT_E0F:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Unexpected {self.describe_token()}. Expected end of statement."
            ))
        return res

    def list_expr(self):
        res = ParseResult()
        element_nodes = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LSQUARE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected '['"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_RSQUARE:
            res.register_advancement()
            self.advance()
        else:
            element_nodes.append(res.register(self.expr()))
            if res.error:
                return res

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                element_nodes.append(res.register(self.expr()))
                if res.error: return res

            if self.current_tok.type != TT_RSQUARE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected ',' or ']'"
                ))

            res.register_advancement()
            self.advance()

        return res.success(ListNode(
            element_nodes,
            pos_start,
            self.current_tok.pos_end.copy()
        ))

    def dict_expr(self):
        res = ParseResult()
        pair_nodes = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '{'"
            ))

        res.register_advancement()
        self.advance()

        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        if self.current_tok.type != TT_RBRACE:
            key = res.register(self.expr())
            if res.error: return res

            if self.current_tok.type != TT_COLON:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ':' after dict key"
                ))
            res.register_advancement()
            self.advance()

            value = res.register(self.expr())
            if res.error: return res
            pair_nodes.append((key, value))

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                while self.current_tok.type == TT_NEWLINE:
                    res.register_advancement()
                    self.advance()

                if self.current_tok.type == TT_RBRACE:
                    break

                key = res.register(self.expr())
                if res.error: return res

                if self.current_tok.type != TT_COLON:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected ':' after dict key"
                    ))
                res.register_advancement()
                self.advance()

                value = res.register(self.expr())
                if res.error: return res
                pair_nodes.append((key, value))

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_RBRACE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ',' or '}'"
                ))

        res.register_advancement()
        self.advance()

        return res.success(DictNode(
            pair_nodes,
            pos_start,
            self.current_tok.pos_end.copy()
        ))

    def if_expr(self):
        res = ParseResult()
        all_cases = res.register(self.if_expr_cases("if"))
        if res.error: return res
        cases, else_case = all_cases
        return res.success(IfNode(cases, else_case))
    
    def if_expr_b(self):
        return self.if_expr_cases("elif")
    
    def if_expr_c(self):
        res = ParseResult()
        else_case = None

        if self.current_tok.matches(TT_KEYWORD, "else"):
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_COLON:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ':' after 'else'"
                ))
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

                statements = res.register(self.statements())
                if res.error: return res
                else_case = (statements, True)

                if self.current_tok.matches(TT_KEYWORD, "end"):
                    res.register_advancement()
                    self.advance()
                else:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected 'end'"
                    ))
            else:
                expr = res.register(self.statement())
                if res.error: return res
                else_case = (expr, False)

        return res.success(else_case)

    def if_expr_b_or_c(self):
        res = ParseResult()
        cases, else_case = [], None

        if self.current_tok.matches(TT_KEYWORD, "elif"):
            all_cases = res.register(self.if_expr_b())
            if res.error: return res
            cases, else_case = all_cases
        else:
            else_case = res.register(self.if_expr_c())
            if res.error: return res
        
        return res.success((cases, else_case))

    def if_expr_cases(self, case_keyword):
        res = ParseResult()
        cases = []
        else_case = None

        if not self.current_tok.matches(TT_KEYWORD, case_keyword):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected '{case_keyword}'"
            ))

        res.register_advancement()
        self.advance()

        condition = res.register(self.expr())
        if res.error: return res

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected ':'"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            statements = res.register(self.statements())
            if res.error: return res
            cases.append((condition, statements, True))

            if self.current_tok.matches(TT_KEYWORD, "end"):
                res.register_advancement()
                self.advance()
            else:
                all_cases = res.register(self.if_expr_b_or_c())
                if res.error: return res
                new_cases, else_case = all_cases
                cases.extend(new_cases)
        else:
            expr = res.register(self.statement())
            if res.error: return res
            cases.append((condition, expr, False))

            all_cases = res.register(self.if_expr_b_or_c())
            if res.error: return res
            new_cases, else_case = all_cases
            cases.extend(new_cases)

        return res.success((cases, else_case))

    def for_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "for"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected 'for'"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected identifier"
            ))

        var_name = self.current_tok
        res.register_advancement()
        self.advance()

        start_value = None
        step_value = None

        if self.current_tok.type == TT_EQ:
            res.register_advancement()
            self.advance()

            start_value = res.register(self.expr())
            if res.error: return res

            if not self.current_tok.matches(TT_KEYWORD, "to"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected 'to'"
                ))
            
            res.register_advancement()
            self.advance()

            end_value = res.register(self.expr())
            if res.error: return res

            if self.current_tok.matches(TT_KEYWORD, "step"):
                res.register_advancement()
                self.advance()

                step_value = res.register(self.expr())
                if res.error: return res
        elif self.current_tok.matches(TT_KEYWORD, "to"):
            res.register_advancement()
            self.advance()

            end_value = res.register(self.expr())
            if res.error: return res
        else:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected '=' for range form or 'to' for iterable form"
            ))

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected ':'"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self.statements())
            if res.error: return res

            if not self.current_tok.matches(TT_KEYWORD, "end"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected 'end'"
                ))

            res.register_advancement()
            self.advance()

            return res.success(ForNode(var_name, start_value, end_value, step_value, body, True))
            
        body = res.register(self.statement())
        if res.error: return res

        return res.success(ForNode(var_name, start_value, end_value, step_value, body, False))

    def while_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "while"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected 'while'"
            ))

        res.register_advancement()
        self.advance()

        condition = res.register(self.statement())
        if res.error: return res

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected ':'"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self.statements())
            if res.error: return res

            if not self.current_tok.matches(TT_KEYWORD, "end"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected 'end'"
                ))

            res.register_advancement()
            self.advance()

            return res.success(WhileNode(condition, body, True))
    
        body = res.register(self.expr())
        if res.error: return res

        return res.success(WhileNode(condition, body, False))

    def atom(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_INT, TT_FLOAT):
            res.register_advancement()
            self.advance()
            return res.success(NumberNode(tok))
        
        if tok.type in TT_STRING:
            res.register_advancement()
            self.advance()
            return res.success(StringNode(tok))
        
        if tok.type == TT_FSTRING:
            res.register_advancement()
            self.advance()
            return res.success(self.parse_fstring(tok))
        
        elif tok.type == TT_IDENTIFIER:
            res.register_advancement()
            self.advance()
            return res.success(VarAccessNode(tok))

        elif tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error: return res
            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
                return res.success(expr)
            else:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ')'"
                ))
        
        elif tok.type == TT_LSQUARE:
            list_expr = res.register(self.list_expr())
            if res.error: return res
            return res.success(list_expr)

        elif tok.type == TT_LBRACE:
            dict_expr = res.register(self.dict_expr())
            if res.error: return res
            return res.success(dict_expr)

        elif tok.matches(TT_KEYWORD, "if"):
            if_expr = res.register(self.if_expr())
            if res.error: return res
            return res.success(if_expr)

        elif tok.matches(TT_KEYWORD, "for"):
            for_expr = res.register(self.for_expr())
            if res.error: return res
            return res.success(for_expr)
        
        elif tok.matches(TT_KEYWORD, "while"):
            while_expr = res.register(self.while_expr())
            if res.error: return res
            return res.success(while_expr)
        
        elif tok.matches(TT_KEYWORD, "func"):
            func_def = res.register(self.func_def())
            if res.error: return res
            return res.success(func_def)

        return res.failure(InvalidSyntaxError(
            tok.pos_start, tok.pos_end,
            f"Unexpected {self.describe_token(tok)}. Expected a value, identifier, '(', '[', '{{', 'if', 'for', 'while' or 'func'."
        ))

    def parse_fstring(self, tok):
        raw = tok.value
        parts = []
        i = 0
        buf = ""
        while i < len(raw):
            if raw[i] == "~" and i + 1 < len(raw):
                if buf:
                    parts.append(("lit", buf))
                    buf = ""
                i += 1
                if raw[i] == "(":
                    depth = 1
                    i += 1
                    expr_buf = ""
                    while i < len(raw) and depth > 0:
                        if raw[i] == "(":
                            depth += 1
                        elif raw[i] == ")":
                            depth -= 1
                            if depth == 0:
                                i += 1
                                break
                        expr_buf += raw[i]
                        i += 1
                    node = _sub_parse(expr_buf, tok.pos_start)
                    if node:
                        parts.append(("expr", node))
                    else:
                        parts.append(("lit", "~(" + expr_buf + ")"))
                elif raw[i].isalpha() or raw[i] == "_":
                    id_buf = ""
                    while i < len(raw) and (raw[i].isalnum() or raw[i] == "_"):
                        id_buf += raw[i]
                        i += 1
                    node = _sub_parse(id_buf, tok.pos_start)
                    if node:
                        parts.append(("expr", node))
                    else:
                        parts.append(("lit", "~" + id_buf))
                else:
                    buf += "~"
            else:
                buf += raw[i]
                i += 1
        if buf:
            parts.append(("lit", buf))
        return FStringNode(parts, tok.pos_start, tok.pos_end)

    def power(self):
        return self.bin_op(self.call, (TT_POW, ), self.factor)
    
    def _peek_is_kwarg(self):
        if self.current_tok.type != TT_IDENTIFIER:
            return False
        next_idx = self.tok_idx + 1
        if next_idx < len(self.tokens):
            return self.tokens[next_idx].type == TT_EQ
        return False

    def call(self):
        res = ParseResult()
        atom = res.register(self.atom())
        if res.error: return res

        while self.current_tok.type in (TT_DOT, TT_LSQUARE):
            if self.current_tok.type == TT_DOT:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected identifier after '.'"
                    ))

                attr_tok = self.current_tok
                res.register_advancement()
                self.advance()

                atom = ModuleAccessNode(atom, attr_tok)

            elif self.current_tok.type == TT_LSQUARE:
                pos_start = self.current_tok.pos_start.copy()
                res.register_advancement()
                self.advance()

                index = res.register(self.expr())
                if res.error: return res

                if self.current_tok.type != TT_RSQUARE:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected ']' after subscript index"
                    ))

                pos_end = self.current_tok.pos_end.copy()
                res.register_advancement()
                self.advance()

                atom = DictSubscriptNode(atom, index, pos_start, pos_end)

        if self.current_tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()
            arg_nodes = []
            kwarg_nodes = {}

            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
            else:
                if self._peek_is_kwarg():
                    kw_name = self.current_tok.value
                    res.register_advancement(); self.advance()
                    res.register_advancement(); self.advance()
                    kw_val = res.register(self.expr())
                    if res.error: return res
                    kwarg_nodes[kw_name] = kw_val
                else:
                    arg_nodes.append(res.register(self.expr()))
                    if res.error: return res

                while self.current_tok.type == TT_COMMA:
                    res.register_advancement()
                    self.advance()

                    if self._peek_is_kwarg():
                        kw_name = self.current_tok.value
                        res.register_advancement(); self.advance()
                        res.register_advancement(); self.advance() 
                        kw_val = res.register(self.expr())
                        if res.error: return res
                        kwarg_nodes[kw_name] = kw_val
                    elif kwarg_nodes:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start, self.current_tok.pos_end,
                            "Positional argument cannot follow keyword argument"
                        ))
                    else:
                        arg_nodes.append(res.register(self.expr()))
                        if res.error: return res

                if self.current_tok.type != TT_RPAREN:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        f"Expected ',' or ')'"
                    ))

                res.register_advancement()
                self.advance()
            return res.success(CallNode(atom, arg_nodes, kwarg_nodes))
        return res.success(atom)

    def factor(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_PLUS, TT_MINUS):
            res.register_advancement()
            self.advance()
            factor = res.register(self.factor())
            if res.error: return res
            return res.success(UnaryOpNode(tok, factor))

        return self.power()

    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV))

    def arith_expr(self):
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))

    def comp_expr(self):
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "is") or \
           self.current_tok.matches(TT_KEYWORD, "isnt"):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()

            node = res.register(self.comp_expr())
            if res.error: return res
            return res.success(UnaryOpNode(op_tok, node))
        
        node = res.register(self.bin_op(self.arith_expr, (TT_EE, TT_NE, TT_LT, TT_GT, TT_LTE, TT_GTE)))

        if res.error:
            return res
        
        return res.success(node)

    def statements(self):
        res = ParseResult()
        statements = []
        pos_start = self.current_tok.pos_start.copy()

        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        statement = res.register(self.statement())
        if res.error: return res
        statements.append(statement)

        more_statements = True

        while True:
            newline_count = 0
            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
                newline_count += 1
            if newline_count == 0:
                more_statements = False
        
            if not more_statements: break
            statement = res.try_register(self.statement())
            if not statement:
                self.reverse(res.to_reverse_count)
                more_statements = False
                continue
            statements.append(statement)

        return res.success(ListNode(
            statements,
            pos_start,
            self.current_tok.pos_end.copy()
        ))

    def statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type == TT_AT:
            res.register_advancement()
            self.advance()

            if self.current_tok.matches(TT_KEYWORD, 'import'):
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_STRING:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected module name (string)"
                    ))

                module_path_tok = self.current_tok
                res.register_advancement()
                self.advance()

                if not self.current_tok.matches(TT_KEYWORD, 'as'):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected 'as' after module name"
                    ))

                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected identifier for module alias"
                    ))

                alias_tok = self.current_tok
                res.register_advancement()
                self.advance()

                return res.success(ImportNode(module_path_tok, alias_tok, pos_start, self.current_tok.pos_start.copy()))

            elif self.current_tok.matches(TT_KEYWORD, 'use'):
                res.register_advancement()
                self.advance()

                if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected directive name after '@use'"
                    ))

                directive_tok = self.current_tok
                res.register_advancement()
                self.advance()

                return res.success(UseDirectiveNode(directive_tok.value, pos_start, self.current_tok.pos_start.copy()))

            elif self.current_tok.matches(TT_KEYWORD, 'set'):
                res.register_advancement()
                self.advance()

                if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected name after '@set'"
                    ))

                lhs = self.current_tok.value
                res.register_advancement()
                self.advance()

                if self.current_tok.type == TT_DOT:
                    res.register_advancement()
                    self.advance()
                    if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start, self.current_tok.pos_end,
                            "Expected member name after '.'"
                        ))
                    lhs = lhs + '.' + self.current_tok.value
                    res.register_advancement()
                    self.advance()

                if not self.current_tok.matches(TT_KEYWORD, 'as'):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected 'as' in '@set'"
                    ))
                res.register_advancement()
                self.advance()

                if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD, TT_STRING, TT_INT, TT_FLOAT):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected value or name after 'as' in '@set'"
                    ))

                rhs = str(self.current_tok.value)
                res.register_advancement()
                self.advance()

                return res.success(SetDirectiveNode(lhs, rhs, pos_start, self.current_tok.pos_start.copy()))

            else:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected 'import', 'use' or 'set' after '@'"
                ))

        if self.current_tok.matches(TT_KEYWORD, 'return'):
            res.register_advancement()
            self.advance()

            expr = res.try_register(self.expr())
            if not expr:
                self.reverse(res.to_reverse_count)
            return res.success(ReturnNode(expr, pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TT_KEYWORD, 'type'):
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected type name after 'type'"
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
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected type parameter name after '<'"
                    ))

                type_params.append(self.current_tok.value)
                res.register_advancement()
                self.advance()

                while self.current_tok.type == TT_COMMA:
                    res.register_advancement()
                    self.advance()

                    if self.current_tok.type != TT_IDENTIFIER:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start, self.current_tok.pos_end,
                            "Expected type parameter name after ','"
                        ))

                    type_params.append(self.current_tok.value)
                    res.register_advancement()
                    self.advance()

                if self.current_tok.type != TT_GT:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected '>' to close type parameters"
                    ))
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_EQ:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected '=' after type name"
                ))
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_LBRACE:
                dict_ann = res.register(self._parse_dict_type_def())
                if res.error: return res
                dict_ann.type_params = type_params
                return res.success(TypeAliasNode(name_tok, dict_ann, pos_start, self.current_tok.pos_start.copy()))

            type_parts = []
            part = self._parse_single_type()
            if part is None:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected type name or string literal"
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
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected type name or string literal after '|'"
                    ))
                type_parts.append(part)
                if self.current_tok.type == TT_QUESTION:
                    res.register_advancement()
                    self.advance()
                    if "null" not in type_parts:
                        type_parts.append("null")

            type_ann = TypeAnnotationNode(type_parts, pos_start, self.current_tok.pos_start.copy(), type_params=type_params)
            return res.success(TypeAliasNode(name_tok, type_ann, pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TT_KEYWORD, 'enum'):
            enum_node = res.register(self.enum_def())
            if res.error: return res
            return res.success(enum_node)
        
        if self.current_tok.matches(TT_KEYWORD, 'trait'):
            trait_node = res.register(self.trait_def())
            if res.error: return res
            return res.success(trait_node)
        
        if self.current_tok.matches(TT_KEYWORD, 'continue'):
            res.register_advancement()
            self.advance()
            return res.success(ContinueNode(pos_start, self.current_tok.pos_start.copy()))
        
        if self.current_tok.matches(TT_KEYWORD, 'break'):
            res.register_advancement()
            self.advance()
            return res.success(BreakNode(pos_start, self.current_tok.pos_start.copy()))

        expr = res.register(self.expr())
        if res.error:
            return res
        
        return res.success(expr)

    def expr(self):
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "var"):
            res.register_advancement()
            self.advance()

            type_ann = None
            if self.current_tok.type == TT_LT:
                type_ann = res.register(self.parse_type_annotation())
                if res.error: return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result
            elif self.current_tok.type == TT_LSQUARE:
                type_ann = res.register(self.parse_array_type_annotation())
                if res.error: return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected variable name after 'var'"
                ))

            var_name = self.current_tok
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_EQ:
                if type_ann is None:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected '=' after variable name (or add a type annotation to declare without value)"
                    ))
                return res.success(VarAssignNode(var_name, None, type_ann))

            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error: return res
            return res.success(VarAssignNode(var_name, expr, type_ann))

        if self.current_tok.matches(TT_KEYWORD, "const"):
            res.register_advancement()
            self.advance()

            type_ann = None
            if self.current_tok.type == TT_LT:
                type_ann = res.register(self.parse_type_annotation())
                if res.error: return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result
            elif self.current_tok.type == TT_LSQUARE:
                type_ann = res.register(self.parse_array_type_annotation())
                if res.error: return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected variable name after 'const'"
                ))

            var_name = self.current_tok
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_EQ:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Constants must be initialized. Expected '=' after constant name"
                ))

            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error: return res
            return res.success(VarAssignNode(var_name, expr, type_ann, is_const=True))

        if self.current_tok.type == TT_IDENTIFIER:
            next_idx = self.tok_idx + 1
            if next_idx < len(self.tokens) and self.tokens[next_idx].type == TT_EQ:
                var_name = self.current_tok
                res.register_advancement()
                self.advance()
                res.register_advancement()
                self.advance()
                expr = res.register(self.expr())
                if res.error: return res
                return res.success(VarAssignNode(var_name, expr, None, is_reassign=True))

        node = res.register(self.bin_op(self.comp_expr, ((TT_KEYWORD, "and"), (TT_KEYWORD, "or"))))

        if res.error:
            return res

        if self.current_tok.type == TT_NULLCOAL:
            res.register_advancement()
            self.advance()
            right = res.register(self.bin_op(self.comp_expr, ((TT_KEYWORD, "and"), (TT_KEYWORD, "or"))))
            if res.error: return res
            return res.success(NullCoalNode(node, right))

        if self.current_tok.type == TT_TILDE:
            true_node = node
            res.register_advancement()
            self.advance()

            cond_node = res.register(self.bin_op(self.comp_expr, ((TT_KEYWORD, "and"), (TT_KEYWORD, "or"))))
            if res.error: return res

            if self.current_tok.type != TT_TILDE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected '~' (ternary false branch)"
                ))
            res.register_advancement()
            self.advance()

            false_node = res.register(self.bin_op(self.comp_expr, ((TT_KEYWORD, "and"), (TT_KEYWORD, "or"))))
            if res.error: return res

            return res.success(TernaryOpNode(true_node, cond_node, false_node))

        return res.success(node)

    def func_def(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, 'func'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected 'func'"
            ))
        
        res.register_advancement()
        self.advance()

        func_type_params = []
        return_type = None
        if self.current_tok.type == TT_LT:
            return_type = res.register(self.parse_type_annotation())
            if res.error: return res
            func_type_params = self._extract_type_params_from_annotation(return_type)

        if self.current_tok.type == TT_IDENTIFIER:
            var_name_tok = self.current_tok
            res.register_advancement()
            self.advance()
            if self.current_tok.type != TT_LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected '('"
                ))
        else:
            var_name_tok = None
            if self.current_tok.type != TT_LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected identifier or '('"
                ))

        res.register_advancement()
        self.advance()
        arg_name_toks = []
        arg_types = []
        arg_defaults = []

        if self.current_tok.type == TT_IDENTIFIER:
            arg_name_toks.append(self.current_tok)
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_LT:
                atype = res.register(self.parse_type_annotation())
                if res.error: return res
                arg_types.append(atype)
            else:
                arg_types.append(None)

            if self.current_tok.type == TT_EQ:
                res.register_advancement()
                self.advance()
                default_node = res.register(self.expr())
                if res.error: return res
                arg_defaults.append(default_node)
            else:
                arg_defaults.append(None)
            
            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    hint = f" ('{self.current_tok.value}' is a reserved keyword)" if self.current_tok.type == TT_KEYWORD else ""
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        f"Expected argument name{hint}"
                    ))

                arg_name_toks.append(self.current_tok)
                res.register_advancement()
                self.advance()

                if self.current_tok.type == TT_LT:
                    atype = res.register(self.parse_type_annotation())
                    if res.error: return res
                    arg_types.append(atype)
                else:
                    arg_types.append(None)

                if self.current_tok.type == TT_EQ:
                    res.register_advancement()
                    self.advance()
                    default_node = res.register(self.expr())
                    if res.error: return res
                    arg_defaults.append(default_node)
                else:
                    arg_defaults.append(None)
            
            if self.current_tok.type != TT_RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected ',' or ')'"
                ))
        else:
            if self.current_tok.type != TT_RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected identifier or ')'"
                ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_ARROW:
            res.register_advancement()
            self.advance()

            body = res.register(self.expr())
            if res.error: return res

            return res.success(FuncDefNode(
                var_name_tok,
                arg_name_toks,
                body,
                True,
                return_type,
                arg_types,
                arg_defaults,
                func_type_params,
            ))

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                f"Expected '->' or ':' after function parameters"
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self.statements())
            if res.error: return res

            if not self.current_tok.matches(TT_KEYWORD, "end"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    f"Expected 'end'"
                ))

            res.register_advancement()
            self.advance()
            
            return res.success(FuncDefNode(
                var_name_tok,
                arg_name_toks,
                body,
                False,
                return_type,
                arg_types,
                arg_defaults,
                func_type_params,
            ))

        body = res.register(self.expr())
        if res.error: return res

        return res.success(FuncDefNode(
            var_name_tok,
            arg_name_toks,
            body,
            True,
            return_type,
            arg_types,
            arg_defaults,
        ))

    def trait_def(self):
        """Parse trait definition: trait NAME<T> = { func<...> method(...) }"""
        res = ParseResult()
        
        if not self.current_tok.matches(TT_KEYWORD, 'trait'):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected 'trait'"
            ))
        
        res.register_advancement()
        self.advance()
        
        # Parse trait name
        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected trait name after 'trait'"
            ))
        
        name_tok = self.current_tok
        trait_name = name_tok.value
        pos_start = name_tok.pos_start.copy()
        res.register_advancement()
        self.advance()
        
        type_params = []
        if self.current_tok.type == TT_LT:
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected type parameter name after '<'"
                ))

            type_params.append(self.current_tok.value)
            res.register_advancement()
            self.advance()

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected type parameter name after ','"
                    ))

                type_params.append(self.current_tok.value)
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_GT:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected '>' to close type parameters"
                ))
            res.register_advancement()
            self.advance()
        
        # Expect '='
        if self.current_tok.type != TT_EQ:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '=' after trait name"
            ))
        res.register_advancement()
        self.advance()
        
        # Expect '{'
        if self.current_tok.type != TT_LBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '{' after '=' in trait definition"
            ))
        res.register_advancement()
        self.advance()
        
        # Skip newlines
        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()
        
        # Parse method signatures
        methods = []
        while self.current_tok.type != TT_RBRACE and self.current_tok.type != TT_E0F:
            # Each method must start with 'func'
            if not self.current_tok.matches(TT_KEYWORD, 'func'):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected 'func' in trait definition"
                ))
            
            res.register_advancement()
            self.advance()
            
            # Parse return type
            if self.current_tok.type != TT_LT:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected '<' for return type annotation in trait method"
                ))
            
            return_type = res.register(self.parse_type_annotation())
            if res.error: return res
            
            # Parse method name
            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected method name"
                ))
            
            method_name = self.current_tok.value
            res.register_advancement()
            self.advance()
            
            # Parse parameters
            if self.current_tok.type != TT_LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected '(' after method name"
                ))
            
            res.register_advancement()
            self.advance()
            
            arg_types = []
            arg_names = []
            
            # Parse parameter list
            if self.current_tok.type != TT_RPAREN:
                # First parameter
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected parameter name"
                    ))
                
                param_name = self.current_tok.value
                arg_names.append(param_name)
                res.register_advancement()
                self.advance()
                
                # Parse parameter type
                if self.current_tok.type != TT_LT:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start, self.current_tok.pos_end,
                        "Expected '<' for parameter type annotation"
                    ))
                
                param_type = res.register(self.parse_type_annotation())
                if res.error: return res
                arg_types.append(param_type)
                
                # Parse more parameters
                while self.current_tok.type == TT_COMMA:
                    res.register_advancement()
                    self.advance()
                    
                    if self.current_tok.type != TT_IDENTIFIER:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start, self.current_tok.pos_end,
                            "Expected parameter name"
                        ))
                    
                    param_name = self.current_tok.value
                    arg_names.append(param_name)
                    res.register_advancement()
                    self.advance()
                    
                    if self.current_tok.type != TT_LT:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start, self.current_tok.pos_end,
                            "Expected '<' for parameter type annotation"
                        ))
                    
                    param_type = res.register(self.parse_type_annotation())
                    if res.error: return res
                    arg_types.append(param_type)
            
            # Expect closing ')'
            if self.current_tok.type != TT_RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end,
                    "Expected ')' after method parameters"
                ))
            
            res.register_advancement()
            self.advance()
            
            # Create method signature
            method_sig = TraitMethodSignature(
                method_name,
                return_type,
                arg_types,
                arg_names
            )
            methods.append(method_sig)
            
            # Skip optional comma
            if self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()
            
            # Skip newlines
            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
        
        # Expect closing '}'
        if self.current_tok.type != TT_RBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start, self.current_tok.pos_end,
                "Expected '}' to close trait definition"
            ))
        
        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()
        
        # Create and return TraitDefNode
        trait_node = TraitDefNode(name_tok, methods, pos_start, pos_end, type_params)
        return res.success(trait_node)

    def bin_op(self, func_a, ops, func_b=None): 
        if func_b == None:
            func_b = func_a

        res = ParseResult()
        left = res.register(func_a())
        if res.error: return res

        while self.current_tok.type in ops or (self.current_tok.type, self.current_tok.value) in ops:
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()
            right = res.register(func_b())
            if res.error: return res
            left = BinOpNode(left, op_tok, right)

        return res.success(left)