from src.error.message.invalidsyntax import InvalidSyntaxError
from src.var.keyword import is_test_file
from src.var.token import (
    TT_IDENTIFIER,
    TT_KEYWORD,
    TT_INT,
    TT_FLOAT,
    TT_STRING,
    TT_FSTRING,
    TT_E0F,
    TOKEN_DISPLAY_NAMES,
)


class ParserBaseMixin:
    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.function_async_depth = 0
        first_fn = None
        if tokens and getattr(tokens[0], "pos_start", None) is not None:
            first_fn = getattr(tokens[0].pos_start, "fn", None)
        self.is_test_mode = is_test_file(first_fn)
        self.suite_depth = 0
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

        if tok.type == TT_E0F:
            return "end of input"
        if tok.type in (TT_IDENTIFIER, TT_KEYWORD, TT_INT, TT_FLOAT):
            return repr(tok.value)
        if tok.type in (TT_STRING, TT_FSTRING):
            return "string"
        return TOKEN_DISPLAY_NAMES.get(tok.type, tok.type.lower())

    def parse(self):
        res = self.statements()
        if not res.error and self.current_tok.type != TT_E0F:
            if self.current_tok.type == TT_E0F:
                message = "Unexpected end of input. Expected end of statement."
            else:
                message = f"Unexpected {self.describe_token()}. Expected end of statement."
            return res.failure(InvalidSyntaxError(
                self.current_tok.pos_start,
                self.current_tok.pos_end,
                message,
            ))
        return res
