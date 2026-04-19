from src.error.message.invalidsyntax import InvalidSyntaxError
from src.main.parser.helpers import sub_parse_expr
from src.main.parser.result import ParseResult
from src.nodes.block import BlockNode
from src.nodes.control.flow import DeferNode
from src.nodes.directives.setN import SetDirectiveNode
from src.nodes.directives.typealiasN import TypeAliasNode
from src.nodes.directives.useN import UseDirectiveNode
from src.nodes.function.awaitN import AwaitNode
from src.nodes.function.call import CallNode
from src.nodes.function.funcdef import FuncDefNode
from src.nodes.imports.importN import ImportNode
from src.nodes.imports.moduleaccess import ModuleAccessNode
from src.nodes.jump.breakN import BreakNode
from src.nodes.jump.continueN import ContinueNode
from src.nodes.jump.returnN import ReturnNode
from src.nodes.ops.binop import BinOpNode
from src.nodes.ops.nullcoal import NullCoalNode
from src.nodes.ops.ternaryop import TernaryOpNode
from src.nodes.ops.unaryop import UnaryOpNode
from src.nodes.types.dict import DictNode
from src.nodes.types.fstring import FStringNode
from src.nodes.types.list import ListNode
from src.nodes.types.number import NumberNode
from src.nodes.types.string import StringNode
from src.nodes.types.subscript import DictSubscriptNode
from src.nodes.types.typeannotation import TypeAnnotationNode
from src.nodes.variables.access import VarAccessNode
from src.nodes.variables.assign import VarAssignNode
from src.var.parser import COMPARISON_BIN_OPS, LOGICAL_BIN_OPS
from src.var.token import (
    TT_INT,
    TT_FLOAT,
    TT_STRING,
    TT_FSTRING,
    TT_MUL,
    TT_DIV,
    TT_POW,
    TT_PLUS,
    TT_MINUS,
    TT_LPAREN,
    TT_RPAREN,
    TT_LSQUARE,
    TT_RSQUARE,
    TT_LBRACE,
    TT_RBRACE,
    TT_KEYWORD,
    TT_IDENTIFIER,
    TT_EQ,
    TT_COMMA,
    TT_ARROW,
    TT_NEWLINE,
    TT_COLON,
    TT_DOT,
    TT_LT,
    TT_AT,
    TT_TILDE,
    TT_NULLCOAL,
    TT_PIPE,
    TT_GT,
    TT_QUESTION,
    TT_E0F,
)


class ParserExpressionsStatementsMixin:
    def list_expr(self):
        res = ParseResult()
        element_nodes = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LSQUARE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '['",
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
                if res.error:
                    return res

            if self.current_tok.type != TT_RSQUARE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ',' or ']'",
                ))

            res.register_advancement()
            self.advance()

        return res.success(ListNode(
            element_nodes,
            pos_start,
            self.current_tok.pos_end.copy(),
        ))

    def dict_expr(self):
        res = ParseResult()
        pair_nodes = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LBRACE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '{'",
            ))

        res.register_advancement()
        self.advance()

        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        if self.current_tok.type != TT_RBRACE:
            key = res.register(self.expr())
            if res.error:
                return res

            if self.current_tok.type != TT_COLON:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ':' after dict key",
                ))
            res.register_advancement()
            self.advance()

            value = res.register(self.expr())
            if res.error:
                return res
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
                if res.error:
                    return res

                if self.current_tok.type != TT_COLON:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ':' after dict key",
                    ))
                res.register_advancement()
                self.advance()

                value = res.register(self.expr())
                if res.error:
                    return res
                pair_nodes.append((key, value))

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

            if self.current_tok.type != TT_RBRACE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ',' or '}'",
                ))

        res.register_advancement()
        self.advance()

        return res.success(DictNode(
            pair_nodes,
            pos_start,
            self.current_tok.pos_end.copy(),
        ))

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

        if tok.type == TT_IDENTIFIER:
            res.register_advancement()
            self.advance()
            return res.success(VarAccessNode(tok))

        if tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error:
                return res
            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
                return res.success(expr)
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ')'",
            ))

        if tok.type == TT_LSQUARE:
            list_expr = res.register(self.list_expr())
            if res.error:
                return res
            return res.success(list_expr)

        if tok.type == TT_LBRACE:
            dict_expr = res.register(self.dict_expr())
            if res.error:
                return res
            return res.success(dict_expr)

        if tok.matches(TT_KEYWORD, "if"):
            if_expr = res.register(self.if_expr())
            if res.error:
                return res
            return res.success(if_expr)

        if tok.matches(TT_KEYWORD, "for"):
            for_expr = res.register(self.for_expr())
            if res.error:
                return res
            return res.success(for_expr)

        if tok.matches(TT_KEYWORD, "while"):
            while_expr = res.register(self.while_expr())
            if res.error:
                return res
            return res.success(while_expr)

        if tok.matches(TT_KEYWORD, "func"):
            func_def = res.register(self.func_def())
            if res.error:
                return res
            return res.success(func_def)

        if tok.matches(TT_KEYWORD, "async"):
            pos_start = tok.pos_start.copy()
            res.register_advancement()
            self.advance()
            if not self.current_tok.matches(TT_KEYWORD, "func"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'func' after 'async'",
                ))
            func_def = res.register(self.func_def(is_async=True, pos_start_override=pos_start))
            if res.error:
                return res
            return res.success(func_def)

        return res.failure(InvalidSyntaxError(
            tok.pos_start,
            tok.pos_end,
            f"Unexpected {self.describe_token(tok)}. Expected a value, identifier, '(', '[', '{{', 'if', 'for', 'while', 'func' or 'async func'.",
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
                    node = sub_parse_expr(expr_buf)
                    if node:
                        parts.append(("expr", node))
                    else:
                        parts.append(("lit", "~(" + expr_buf + ")"))
                elif raw[i].isalpha() or raw[i] == "_":
                    id_buf = ""
                    while i < len(raw) and (raw[i].isalnum() or raw[i] == "_"):
                        id_buf += raw[i]
                        i += 1
                    node = sub_parse_expr(id_buf)
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
        return self.bin_op(self.call, (TT_POW,), self.factor)

    def _peek_is_kwarg(self):
        if self.current_tok.type != TT_IDENTIFIER:
            return False
        next_idx = self.tok_idx + 1
        if next_idx < len(self.tokens):
            return self.tokens[next_idx].type == TT_EQ
        return False

    def call(self):
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "async"):
            next_is_func = (
                self.tok_idx + 1 < len(self.tokens)
                and self.tokens[self.tok_idx + 1].matches(TT_KEYWORD, "func")
            )
            if next_is_func:
                atom = res.register(self.atom())
                if res.error:
                    return res
                return res.success(atom)

            if self._is_named_async_group():
                async_tok = self.current_tok
                res.register_advancement()
                self.advance()
                group_node = res.register(self.async_group(async_tok.pos_start.copy()))
                if res.error:
                    return res
                return res.success(group_node)

            async_tok = self.current_tok
            res.register_advancement()
            self.advance()

            async_target = res.register(self.call())
            if res.error:
                return res

            if isinstance(async_target, CallNode):
                async_target.is_async = True
                async_target.pos_start = async_tok.pos_start
                return res.success(async_target)

            if self.function_async_depth <= 0:
                return res.failure(InvalidSyntaxError(
                    async_tok.pos_start,
                    async_tok.pos_end,
                    "'async <expr>' is only allowed inside 'async func' when used for awaiting",
                ))

            return res.success(AwaitNode(async_target, async_tok.pos_start.copy(), async_target.pos_end))

        atom = res.register(self.atom())
        if res.error:
            return res

        while self.current_tok.type in (TT_DOT, TT_LSQUARE):
            if self.current_tok.type == TT_DOT:
                res.register_advancement()
                self.advance()

                if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier after '.'",
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
                if res.error:
                    return res

                if self.current_tok.type != TT_RSQUARE:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ']' after subscript index",
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
                    res.register_advancement()
                    self.advance()
                    res.register_advancement()
                    self.advance()
                    kw_val = res.register(self.expr())
                    if res.error:
                        return res
                    kwarg_nodes[kw_name] = kw_val
                else:
                    arg_nodes.append(res.register(self.expr()))
                    if res.error:
                        return res

                while self.current_tok.type == TT_COMMA:
                    res.register_advancement()
                    self.advance()

                    if self._peek_is_kwarg():
                        kw_name = self.current_tok.value
                        res.register_advancement()
                        self.advance()
                        res.register_advancement()
                        self.advance()
                        kw_val = res.register(self.expr())
                        if res.error:
                            return res
                        kwarg_nodes[kw_name] = kw_val
                    elif kwarg_nodes:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Positional argument cannot follow keyword argument",
                        ))
                    else:
                        arg_nodes.append(res.register(self.expr()))
                        if res.error:
                            return res

                if self.current_tok.type != TT_RPAREN:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ',' or ')'",
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
            if res.error:
                return res
            return res.success(UnaryOpNode(tok, factor))

        return self.power()

    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV))

    def arith_expr(self):
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))

    def comp_expr(self):
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "is") or self.current_tok.matches(TT_KEYWORD, "isnt"):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()

            node = res.register(self.comp_expr())
            if res.error:
                return res
            return res.success(UnaryOpNode(op_tok, node))

        node = res.register(self.bin_op(self.arith_expr, COMPARISON_BIN_OPS))

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
        if res.error:
            return res
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

            if not more_statements:
                break
            statement = res.try_register(self.statement())
            if not statement:
                self.reverse(res.to_reverse_count)
                more_statements = False
                continue
            statements.append(statement)

        return res.success(BlockNode(
            statements,
            pos_start,
            self.current_tok.pos_end.copy(),
        ))

    def statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.is_test_mode:
            if self.current_tok.matches(TT_KEYWORD, "suite"):
                suite_node = res.register(self._parse_suite_statement())
                if res.error:
                    return res
                return res.success(suite_node)

            if self.current_tok.matches(TT_KEYWORD, "test"):
                test_node = res.register(self._parse_test_case_statement())
                if res.error:
                    return res
                return res.success(test_node)

            if self.current_tok.matches(TT_KEYWORD, "async"):
                next_idx = self.tok_idx + 1
                if next_idx < len(self.tokens) and self.tokens[next_idx].matches(TT_KEYWORD, "test"):
                    async_tok = self.current_tok
                    res.register_advancement()
                    self.advance()
                    test_node = res.register(self._parse_test_case_statement(
                        is_async=True,
                        pos_start_override=async_tok.pos_start.copy(),
                    ))
                    if res.error:
                        return res
                    return res.success(test_node)

            if self.current_tok.matches(TT_KEYWORD, "skip"):
                skip_tok = self.current_tok
                res.register_advancement()
                self.advance()
                if not self.current_tok.matches(TT_KEYWORD, "test"):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'test' after 'skip'",
                    ))
                test_node = res.register(self._parse_test_case_statement(
                    is_skipped=True,
                    pos_start_override=skip_tok.pos_start.copy(),
                ))
                if res.error:
                    return res
                return res.success(test_node)

            if self.current_tok.matches(TT_KEYWORD, "expect"):
                expect_node = res.register(self._parse_expect_statement())
                if res.error:
                    return res
                return res.success(expect_node)

            if self.suite_depth > 0 and self.current_tok.type == TT_KEYWORD and self.current_tok.value in self.HOOK_KEYWORDS:
                hook_node = res.register(self._parse_hook_statement())
                if res.error:
                    return res
                return res.success(hook_node)

        if self.current_tok.type == TT_AT:
            res.register_advancement()
            self.advance()

            if self.current_tok.matches(TT_KEYWORD, "import"):
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_STRING:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected module name (string)",
                    ))

                module_path_tok = self.current_tok
                res.register_advancement()
                self.advance()

                if not self.current_tok.matches(TT_KEYWORD, "as"):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'as' after module name",
                    ))

                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier for module alias",
                    ))

                alias_tok = self.current_tok
                res.register_advancement()
                self.advance()

                return res.success(ImportNode(module_path_tok, alias_tok, pos_start, self.current_tok.pos_start.copy()))

            if self.current_tok.matches(TT_KEYWORD, "use"):
                res.register_advancement()
                self.advance()

                if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected directive name after '@use'",
                    ))

                directive_tok = self.current_tok
                res.register_advancement()
                self.advance()

                directive_name = str(directive_tok.value).lower()
                value = None
                has_as = False

                value_token_types = (TT_IDENTIFIER, TT_KEYWORD, TT_STRING, TT_INT, TT_FLOAT)

                if self.current_tok.matches(TT_KEYWORD, "as"):
                    has_as = True
                    res.register_advancement()
                    self.advance()
                    if self.current_tok.type not in value_token_types:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected value after 'as' in '@use'",
                        ))
                    value = str(self.current_tok.value)
                    res.register_advancement()
                    self.advance()
                elif directive_name in {"config", "save"} and self.current_tok.type in value_token_types:
                    value = str(self.current_tok.value)
                    res.register_advancement()
                    self.advance()

                if self.current_tok.type not in (TT_NEWLINE, TT_E0F):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Unexpected tokens after '@use' directive",
                    ))

                return res.success(UseDirectiveNode(directive_tok.value, pos_start, self.current_tok.pos_start.copy(), value=value, has_as=has_as))

            if self.current_tok.matches(TT_KEYWORD, "set"):
                res.register_advancement()
                self.advance()

                if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected name after '@set'",
                    ))

                lhs = self.current_tok.value
                res.register_advancement()
                self.advance()

                if self.current_tok.type == TT_DOT:
                    res.register_advancement()
                    self.advance()
                    if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected member name after '.'",
                        ))
                    lhs = lhs + "." + self.current_tok.value
                    res.register_advancement()
                    self.advance()

                if not self.current_tok.matches(TT_KEYWORD, "as"):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'as' in '@set'",
                    ))
                res.register_advancement()
                self.advance()

                if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD, TT_STRING, TT_INT, TT_FLOAT):
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected value or name after 'as' in '@set'",
                    ))

                rhs = str(self.current_tok.value)
                res.register_advancement()
                self.advance()

                return res.success(SetDirectiveNode(lhs, rhs, pos_start, self.current_tok.pos_start.copy()))

            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'import', 'use' or 'set' after '@'",
            ))

        if self.current_tok.matches(TT_KEYWORD, "return"):
            res.register_advancement()
            self.advance()

            expr = res.try_register(self.expr())
            if not expr:
                self.reverse(res.to_reverse_count)
            return res.success(ReturnNode(expr, pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TT_KEYWORD, "type"):
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected type name after 'type'",
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
                    "Expected '=' after type name",
                ))
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_LBRACE:
                dict_ann = res.register(self._parse_dict_type_def())
                if res.error:
                    return res
                dict_ann.type_params = type_params
                return res.success(TypeAliasNode(name_tok, dict_ann, pos_start, self.current_tok.pos_start.copy()))

            type_parts = []
            part = self._parse_single_type()
            if part is None:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected type name or string literal",
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

            type_ann = TypeAnnotationNode(type_parts, pos_start, self.current_tok.pos_start.copy(), type_params=type_params)
            return res.success(TypeAliasNode(name_tok, type_ann, pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TT_KEYWORD, "enum"):
            enum_node = res.register(self.enum_def())
            if res.error:
                return res
            return res.success(enum_node)

        if self.current_tok.matches(TT_KEYWORD, "trait"):
            trait_node = res.register(self.trait_def())
            if res.error:
                return res
            return res.success(trait_node)

        if self.current_tok.matches(TT_KEYWORD, "try"):
            try_node = res.register(self.try_expr())
            if res.error:
                return res
            return res.success(try_node)

        if self.current_tok.matches(TT_KEYWORD, "match"):
            match_node = res.register(self.match_expr())
            if res.error:
                return res
            return res.success(match_node)

        if self.current_tok.matches(TT_KEYWORD, "defer"):
            res.register_advancement()
            self.advance()

            deferred_expr = res.register(self.expr())
            if res.error:
                return res

            return res.success(DeferNode(
                deferred_expr,
                pos_start,
                deferred_expr.pos_end,
            ))

        if self.current_tok.matches(TT_KEYWORD, "continue"):
            res.register_advancement()
            self.advance()
            return res.success(ContinueNode(pos_start, self.current_tok.pos_start.copy()))

        if self.current_tok.matches(TT_KEYWORD, "break"):
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
                if res.error:
                    return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result
            elif self.current_tok.type == TT_LSQUARE:
                type_ann = res.register(self.parse_array_type_annotation())
                if res.error:
                    return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected variable name after 'var'",
                ))

            var_name = self.current_tok
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_EQ:
                if type_ann is None:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected '=' after variable name (or add a type annotation to declare without value)",
                    ))
                return res.success(VarAssignNode(var_name, None, type_ann))

            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error:
                return res
            return res.success(VarAssignNode(var_name, expr, type_ann))

        if self.current_tok.matches(TT_KEYWORD, "const"):
            res.register_advancement()
            self.advance()

            type_ann = None
            if self.current_tok.type == TT_LT:
                type_ann = res.register(self.parse_type_annotation())
                if res.error:
                    return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result
            elif self.current_tok.type == TT_LSQUARE:
                type_ann = res.register(self.parse_array_type_annotation())
                if res.error:
                    return res
                size_result = self._try_parse_size_constraint(type_ann, res)
                if isinstance(size_result, ParseResult):
                    return size_result
                type_ann = size_result

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected variable name after 'const'",
                ))

            var_name = self.current_tok
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_EQ:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Constants must be initialized. Expected '=' after constant name",
                ))

            res.register_advancement()
            self.advance()
            expr = res.register(self.expr())
            if res.error:
                return res
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
                if res.error:
                    return res
                return res.success(VarAssignNode(var_name, expr, None, is_reassign=True))

        node = res.register(self.bin_op(self.comp_expr, LOGICAL_BIN_OPS))

        if res.error:
            return res

        if self.current_tok.type == TT_NULLCOAL:
            res.register_advancement()
            self.advance()
            right = res.register(self.bin_op(self.comp_expr, LOGICAL_BIN_OPS))
            if res.error:
                return res
            return res.success(NullCoalNode(node, right))

        if self.current_tok.type == TT_TILDE:
            true_node = node
            res.register_advancement()
            self.advance()

            cond_node = res.register(self.bin_op(self.comp_expr, LOGICAL_BIN_OPS))
            if res.error:
                return res

            if self.current_tok.type != TT_TILDE:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '~' (ternary false branch)",
                ))
            res.register_advancement()
            self.advance()

            false_node = res.register(self.bin_op(self.comp_expr, LOGICAL_BIN_OPS))
            if res.error:
                return res

            return res.success(TernaryOpNode(true_node, cond_node, false_node))

        return res.success(node)

    def func_def(self, is_async=False, pos_start_override=None):
        res = ParseResult()
        func_pos_start = pos_start_override or self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "func"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'func'",
            ))

        res.register_advancement()
        self.advance()

        explicit_type_params = self._parse_explicit_type_params()

        func_type_params = explicit_type_params
        return_type = None

        if self.current_tok.type == TT_LT and not explicit_type_params:
            return_type = res.register(self.parse_type_annotation())
            if res.error:
                return res
            func_type_params = self._extract_type_params_from_annotation(return_type)

        if self.current_tok.type == TT_IDENTIFIER:
            var_name_tok = self.current_tok
            res.register_advancement()
            self.advance()
            if self.current_tok.type != TT_LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '('",
                ))
        else:
            var_name_tok = None
            if self.current_tok.type != TT_LPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected identifier or '('",
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
                if res.error:
                    return res
                arg_types.append(atype)
            else:
                arg_types.append(None)

            if self.current_tok.type == TT_EQ:
                res.register_advancement()
                self.advance()
                default_node = res.register(self.expr())
                if res.error:
                    return res
                arg_defaults.append(default_node)
            else:
                arg_defaults.append(None)

            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    hint = f" ('{self.current_tok.value}' is a reserved keyword)" if self.current_tok.type == TT_KEYWORD else ""
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected argument name{hint}",
                    ))

                arg_name_toks.append(self.current_tok)
                res.register_advancement()
                self.advance()

                if self.current_tok.type == TT_LT:
                    atype = res.register(self.parse_type_annotation())
                    if res.error:
                        return res
                    arg_types.append(atype)
                else:
                    arg_types.append(None)

                if self.current_tok.type == TT_EQ:
                    res.register_advancement()
                    self.advance()
                    default_node = res.register(self.expr())
                    if res.error:
                        return res
                    arg_defaults.append(default_node)
                else:
                    arg_defaults.append(None)

            if self.current_tok.type != TT_RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ',' or ')'",
                ))
        else:
            if self.current_tok.type != TT_RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected identifier or ')'",
                ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_ARROW:
            res.register_advancement()
            self.advance()

            body = res.register(self._parse_with_async_scope(self.expr, is_async))
            if res.error:
                return res

            node = FuncDefNode(
                var_name_tok,
                arg_name_toks,
                body,
                True,
                return_type,
                arg_types,
                arg_defaults,
                func_type_params,
                is_async=is_async,
            )
            node.pos_start = func_pos_start
            return res.success(node)

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '->' or ':' after function parameters",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self._parse_with_async_scope(self.statements, is_async))
            if res.error:
                return res

            if not self.current_tok.matches(TT_KEYWORD, "end"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'end'",
                ))

            res.register_advancement()
            self.advance()

            ordered_params = list(func_type_params)
            for arg_type in arg_types:
                if arg_type is not None:
                    params_in_arg = self._extract_type_params_from_annotation(arg_type)
                    for param in params_in_arg:
                        if param not in ordered_params:
                            ordered_params.append(param)
            if return_type is not None:
                params_in_return = self._extract_type_params_from_annotation(return_type)
                for param in params_in_return:
                    if param not in ordered_params:
                        ordered_params.append(param)
            func_type_params = ordered_params

            node = FuncDefNode(
                var_name_tok,
                arg_name_toks,
                body,
                False,
                return_type,
                arg_types,
                arg_defaults,
                func_type_params,
                is_async=is_async,
            )
            node.pos_start = func_pos_start
            return res.success(node)

        body = res.register(self._parse_with_async_scope(self.expr, is_async))
        if res.error:
            return res

        ordered_params = list(func_type_params)
        for arg_type in arg_types:
            if arg_type is not None:
                params_in_arg = self._extract_type_params_from_annotation(arg_type)
                for param in params_in_arg:
                    if param not in ordered_params:
                        ordered_params.append(param)
        if return_type is not None:
            params_in_return = self._extract_type_params_from_annotation(return_type)
            for param in params_in_return:
                if param not in ordered_params:
                    ordered_params.append(param)
        func_type_params = ordered_params

        node = FuncDefNode(
            var_name_tok,
            arg_name_toks,
            body,
            True,
            return_type,
            arg_types,
            arg_defaults,
            func_type_params,
            is_async=is_async,
        )
        node.pos_start = func_pos_start
        return res.success(node)

    def bin_op(self, func_a, ops, func_b=None):
        if func_b is None:
            func_b = func_a

        res = ParseResult()
        left = res.register(func_a())
        if res.error:
            return res

        while self.current_tok.type in ops or (self.current_tok.type, self.current_tok.value) in ops:
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()
            right = res.register(func_b())
            if res.error:
                return res
            left = BinOpNode(left, op_tok, right)

        return res.success(left)
