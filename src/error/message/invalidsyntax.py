from src.error.error import Error


class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details=""):
            if not details:
                details = "Unexpected or incomplete syntax"
            super().__init__(pos_start, pos_end, "Invalid Syntax", details)