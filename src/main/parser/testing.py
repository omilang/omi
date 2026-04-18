from src.error.message.invalidsyntax import InvalidSyntaxError
from src.main.parser.result import ParseResult
from src.nodes.testing.expect import ExpectNode
from src.nodes.testing.hook import HookNode
from src.nodes.testing.suite import SuiteNode
from src.nodes.testing.testcase import TestCaseNode
from src.nodes.types.string import StringNode
from src.var.parser import LOGICAL_BIN_OPS
from src.var.token import (
    TT_COLON,
    TT_E0F,
    TT_FSTRING,
    TT_KEYWORD,
    TT_NEWLINE,
    TT_STRING,
    TT_TILDE,
)


class ParserTestingMixin:
    HOOK_KEYWORDS = {"before", "after", "before_each", "after_each"}

    def _parse_expect_statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "expect"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'expect'",
            ))

        res.register_advancement()
        self.advance()

        expr_node = res.register(self.bin_op(self.comp_expr, LOGICAL_BIN_OPS))
        if res.error:
            return res

        message_node = None
        if self.current_tok.type == TT_TILDE:
            res.register_advancement()
            self.advance()

            if self.current_tok.type not in (TT_STRING, TT_FSTRING):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected string message after '~'",
                ))

            if self.current_tok.type == TT_FSTRING:
                message_node = self.parse_fstring(self.current_tok)
            else:
                message_node = StringNode(self.current_tok)

            res.register_advancement()
            self.advance()

        pos_end = (message_node.pos_end if message_node else expr_node.pos_end)
        return res.success(ExpectNode(expr_node, message_node, pos_start, pos_end))

    def _parse_hook_statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_KEYWORD or self.current_tok.value not in self.HOOK_KEYWORDS:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected hook keyword",
            ))

        hook_type = self.current_tok.value
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                f"Expected ':' after '{hook_type}'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()
            body_node = res.register(self.statements())
            if res.error:
                return res
        else:
            body_node = res.register(self.statement())
            if res.error:
                return res

        if not self.current_tok.matches(TT_KEYWORD, "end"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                f"Expected 'end' to close '{hook_type}' hook",
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(HookNode(hook_type, body_node, pos_start, pos_end))

    def _parse_test_case_statement(self, is_async=False, is_skipped=False, pos_start_override=None):
        res = ParseResult()
        pos_start = pos_start_override or self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "test"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'test'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_STRING:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected test description string",
            ))

        description_tok = self.current_tok
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':' after test description",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()
            body_node = res.register(self._parse_with_async_scope(self.statements, is_async))
            if res.error:
                return res
        else:
            body_node = res.register(self._parse_with_async_scope(self.statement, is_async))
            if res.error:
                return res

        if not self.current_tok.matches(TT_KEYWORD, "end"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'end' to close test case",
            ))

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(TestCaseNode(description_tok, body_node, is_async, is_skipped, pos_start, pos_end))

    def _parse_suite_statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "suite"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'suite'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_STRING:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected suite name string",
            ))

        name_tok = self.current_tok
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':' after suite name",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        hooks = {
            "before": [],
            "after": [],
            "before_each": [],
            "after_each": [],
        }
        body_nodes = []

        self.suite_depth += 1
        try:
            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

            while not self.current_tok.matches(TT_KEYWORD, "end"):
                if self.current_tok.type == TT_E0F:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'end' to close suite",
                    ))

                if self.current_tok.type == TT_KEYWORD and self.current_tok.value in self.HOOK_KEYWORDS:
                    hook_node = res.register(self._parse_hook_statement())
                    if res.error:
                        return res
                    hooks[hook_node.hook_type].append(hook_node)
                else:
                    child_node = res.register(self.statement())
                    if res.error:
                        return res
                    body_nodes.append(child_node)

                while self.current_tok.type == TT_NEWLINE:
                    res.register_advancement()
                    self.advance()
        finally:
            self.suite_depth -= 1

        pos_end = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(SuiteNode(name_tok, body_nodes, hooks, pos_start, pos_end))
