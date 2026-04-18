from src.main.parser.base import ParserBaseMixin
from src.main.parser.control import ParserControlMixin
from src.main.parser.expressions_statements import ParserExpressionsStatementsMixin
from src.main.parser.types import ParserTypesMixin


class Parser(
    ParserBaseMixin,
    ParserTypesMixin,
    ParserControlMixin,
    ParserExpressionsStatementsMixin,
):
    pass
