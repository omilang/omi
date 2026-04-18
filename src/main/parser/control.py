from src.error.message.invalidsyntax import InvalidSyntaxError
from src.main.parser.result import ParseResult
from src.nodes.condition.ifN import IfNode
from src.nodes.control.asyncgroup import AsyncGroupNode
from src.nodes.control.flow import TryNode, MatchNode, CaseNode, PatternNode
from src.nodes.loops.forN import ForNode
from src.nodes.loops.whileN import WhileNode
from src.var.token import (
    TT_IDENTIFIER,
    TT_KEYWORD,
    TT_INT,
    TT_FLOAT,
    TT_STRING,
    TT_LPAREN,
    TT_RPAREN,
    TT_EQ,
    TT_COMMA,
    TT_COLON,
    TT_NEWLINE,
    TT_E0F,
)


class ParserControlMixin:
    def if_expr(self):
        res = ParseResult()
        all_cases = res.register(self.if_expr_cases("if"))
        if res.error:
            return res
        cases, else_case = all_cases
        return res.success(IfNode(cases, else_case))

    def try_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "try"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'try'",
            ))

        def parse_clause_body():
            if self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
                body = res.register(self.statements())
                if res.error:
                    return None
            else:
                body = res.register(self.statement())
                if res.error:
                    return None

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

            return body

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':' after 'try'",
            ))

        res.register_advancement()
        self.advance()

        try_body = parse_clause_body()
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "catch"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'catch' after try block",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected identifier after 'catch'",
            ))

        catch_var_tok = self.current_tok
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':' after catch variable",
            ))

        res.register_advancement()
        self.advance()

        catch_body = parse_clause_body()
        if res.error:
            return res

        final_body = None
        if self.current_tok.matches(TT_KEYWORD, "final"):
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_COLON:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ':' after 'final'",
                ))

            res.register_advancement()
            self.advance()

            final_body = parse_clause_body()
            if res.error:
                return res

        if not self.current_tok.matches(TT_KEYWORD, "end"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'end' after try/catch/final block",
            ))

        end_pos = self.current_tok.pos_end.copy()
        res.register_advancement()
        self.advance()

        return res.success(TryNode(try_body, catch_var_tok, catch_body, final_body, pos_start, end_pos))

    def _parse_match_pattern(self):
        res = ParseResult()
        tok = self.current_tok
        pos_start = tok.pos_start.copy()

        if tok.type == TT_IDENTIFIER:
            if tok.value == "_":
                res.register_advancement()
                self.advance()
                return res.success(PatternNode("wildcard", name="_", pos_start=pos_start, pos_end=tok.pos_end.copy()))

            name = tok.value
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_LPAREN:
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected capture variable name inside pattern",
                    ))

                capture_var_tok = self.current_tok
                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_RPAREN:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ')' to close pattern",
                    ))

                pos_end = self.current_tok.pos_end.copy()
                res.register_advancement()
                self.advance()
                return res.success(PatternNode("variant", name=name, capture_var_tok=capture_var_tok, pos_start=pos_start, pos_end=pos_end))

            return res.success(PatternNode("identifier", name=name, pos_start=pos_start, pos_end=tok.pos_end.copy()))

        if tok.type in (TT_STRING, TT_INT, TT_FLOAT):
            res.register_advancement()
            self.advance()
            return res.success(PatternNode("literal", value=tok.value, pos_start=pos_start, pos_end=tok.pos_end.copy()))

        return res.failure(InvalidSyntaxError(
            tok.pos_start,
            tok.pos_end,
            "Expected pattern name, literal, or '_'",
        ))

    def match_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "match"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'match'",
            ))

        res.register_advancement()
        self.advance()

        expr = res.register(self.expr())
        if res.error:
            return res

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':' after match expression",
            ))

        res.register_advancement()
        self.advance()

        cases = []
        while self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

        while self.current_tok.matches(TT_KEYWORD, "case"):
            case_start = self.current_tok.pos_start.copy()
            res.register_advancement()
            self.advance()

            pattern = res.register(self._parse_match_pattern())
            if res.error:
                return res

            if self.current_tok.type != TT_COLON:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ':' after case pattern",
                ))

            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
                body = res.register(self.statements())
                if res.error:
                    return res
            else:
                body = res.register(self.statement())
                if res.error:
                    return res

            cases.append(CaseNode(pattern, body, case_start, self.current_tok.pos_end.copy()))

            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

            if self.current_tok.matches(TT_KEYWORD, "end"):
                res.register_advancement()
                self.advance()
                return res.success(MatchNode(expr, cases, pos_start, self.current_tok.pos_end.copy()))

        if len(cases) == 0:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected at least one 'case' in match expression",
            ))

        if not self.current_tok.matches(TT_KEYWORD, "end"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'case' or 'end' in match expression",
            ))

        res.register_advancement()
        self.advance()

        return res.success(MatchNode(expr, cases, pos_start, self.current_tok.pos_end.copy()))

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
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ':' after 'else'",
                ))
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()

                statements = res.register(self.statements())
                if res.error:
                    return res
                else_case = (statements, True)

                if self.current_tok.matches(TT_KEYWORD, "end"):
                    res.register_advancement()
                    self.advance()
                else:
                    return res.failure(InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'end'",
                    ))
            else:
                expr = res.register(self.statement())
                if res.error:
                    return res
                else_case = (expr, False)

        return res.success(else_case)

    def if_expr_b_or_c(self):
        res = ParseResult()
        cases, else_case = [], None

        if self.current_tok.matches(TT_KEYWORD, "elif"):
            all_cases = res.register(self.if_expr_b())
            if res.error:
                return res
            cases, else_case = all_cases
        else:
            else_case = res.register(self.if_expr_c())
            if res.error:
                return res

        return res.success((cases, else_case))

    def if_expr_cases(self, case_keyword):
        res = ParseResult()
        cases = []
        else_case = None

        if not self.current_tok.matches(TT_KEYWORD, case_keyword):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                f"Expected '{case_keyword}'",
            ))

        res.register_advancement()
        self.advance()

        condition = res.register(self.expr())
        if res.error:
            return res

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            statements = res.register(self.statements())
            if res.error:
                return res
            cases.append((condition, statements, True))

            if self.current_tok.matches(TT_KEYWORD, "end"):
                res.register_advancement()
                self.advance()
            else:
                all_cases = res.register(self.if_expr_b_or_c())
                if res.error:
                    return res
                new_cases, else_case = all_cases
                cases.extend(new_cases)
        else:
            expr = res.register(self.statement())
            if res.error:
                return res
            cases.append((condition, expr, False))

            all_cases = res.register(self.if_expr_b_or_c())
            if res.error:
                return res
            new_cases, else_case = all_cases
            cases.extend(new_cases)

        return res.success((cases, else_case))

    def for_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "for"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'for'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected identifier",
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
            if res.error:
                return res

            if not self.current_tok.matches(TT_KEYWORD, "to"):
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'to'",
                ))

            res.register_advancement()
            self.advance()

            end_value = res.register(self.expr())
            if res.error:
                return res

            if self.current_tok.matches(TT_KEYWORD, "step"):
                res.register_advancement()
                self.advance()

                step_value = res.register(self.expr())
                if res.error:
                    return res
        elif self.current_tok.matches(TT_KEYWORD, "to"):
            res.register_advancement()
            self.advance()

            end_value = res.register(self.expr())
            if res.error:
                return res
        else:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected '=' for range form or 'to' for iterable form",
            ))

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self.statements())
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

            return res.success(ForNode(var_name, start_value, end_value, step_value, body, True))

        body = res.register(self.statement())
        if res.error:
            return res

        return res.success(ForNode(var_name, start_value, end_value, step_value, body, False))

    def while_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "while"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'while'",
            ))

        res.register_advancement()
        self.advance()

        condition = res.register(self.statement())
        if res.error:
            return res

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()

            body = res.register(self.statements())
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

            return res.success(WhileNode(condition, body, True))

        body = res.register(self.expr())
        if res.error:
            return res

        return res.success(WhileNode(condition, body, False))

    def _parse_with_async_scope(self, parser_fn, is_async):
        if is_async:
            self.function_async_depth += 1
        try:
            return parser_fn()
        finally:
            if is_async:
                self.function_async_depth -= 1

    def _is_named_async_group(self):
        name_idx = self.tok_idx + 1
        if name_idx >= len(self.tokens):
            return False
        if self.tokens[name_idx].type != TT_IDENTIFIER:
            return False

        after_name_idx = name_idx + 1
        if after_name_idx >= len(self.tokens):
            return False

        after_name = self.tokens[after_name_idx]
        if after_name.type == TT_COLON:
            return True

        if after_name.type != TT_LPAREN:
            return False

        depth = 0
        idx = after_name_idx
        while idx < len(self.tokens):
            tok = self.tokens[idx]
            if tok.type == TT_LPAREN:
                depth += 1
            elif tok.type == TT_RPAREN:
                depth -= 1
                if depth == 0:
                    idx += 1
                    break
            idx += 1

        if idx >= len(self.tokens):
            return False
        return self.tokens[idx].type == TT_COLON

    def async_group(self, pos_start_override=None):
        res = ParseResult()
        pos_start = pos_start_override or self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected group name after 'async'",
            ))

        group_name = self.current_tok.value

        res.register_advancement()
        self.advance()

        params = {}
        if self.current_tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_RPAREN:
                while True:
                    if self.current_tok.type not in (TT_IDENTIFIER, TT_KEYWORD):
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected parameter name in 'async group'",
                        ))

                    param_name = self.current_tok.value
                    res.register_advancement()
                    self.advance()

                    if self.current_tok.type != TT_COLON:
                        return res.failure(InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected ':' after parameter name in 'async group'",
                        ))

                    res.register_advancement()
                    self.advance()

                    param_value = res.register(self.expr())
                    if res.error:
                        return res
                    params[param_name] = param_value

                    if self.current_tok.type == TT_COMMA:
                        res.register_advancement()
                        self.advance()
                        continue
                    break

            if self.current_tok.type != TT_RPAREN:
                return res.failure(InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ')' after 'async group' parameters",
                ))

            res.register_advancement()
            self.advance()

        if self.current_tok.type != TT_COLON:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected ':' after 'async group'",
            ))

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_NEWLINE:
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected newline after ':' in 'async group'",
            ))

        res.register_advancement()
        self.advance()

        body = res.register(self._parse_with_async_scope(self.statements, True))
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "end"):
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                "Expected 'end' to close 'async group'",
            ))

        res.register_advancement()
        self.advance()

        return res.success(AsyncGroupNode(group_name, params, body, pos_start, body.pos_end))
