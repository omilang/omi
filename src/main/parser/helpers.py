def sub_parse_expr(expr_src):
    from src.main.lexer import Lexer
    from src.main.parser.parser import Parser

    lexer = Lexer("<fstring>", expr_src)
    tokens, err = lexer.make_tokens()
    if err:
        return None
    sub_parser = Parser(tokens)
    result = sub_parser.expr()
    if result.error:
        return None
    return result.node
