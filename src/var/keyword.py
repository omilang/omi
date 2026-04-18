KEYWORDS = [
    "var",
    "const",
    "and",
    "or",
    "is",
    "isnt",
    "if",
    "elif",
    "else",
    "try",
    "catch",
    "final",
    "match",
    "case",
    "for",
    "to",
    "step",
    "while",
    "async",
    "func",
    "end",
    "return",
    "continue",
    "break",
    "import",
    "as",
    "use",
    "set",
    "type",
    "enum",
    "trait"
]

TEST_KEYWORDS = [
    "suite",
    "test",
    "expect",
    "before",
    "after",
    "before_each",
    "after_each",
    "skip",
]

TEST_FILE_EXTENSION = ".test.omi"


def is_test_file(file_name):
    if not file_name:
        return False
    return str(file_name).lower().endswith(TEST_FILE_EXTENSION)


def get_keywords_for_file(file_name):
    if is_test_file(file_name):
        return KEYWORDS + TEST_KEYWORDS
    return KEYWORDS

FILE_FORMAT = [
    ".omi"
]

TYPE_LABELS = {
    'int': 'int',
    'float': 'float',
    'string': 'string',
    'dict': 'dict',
    'boolean': 'bool',
    'null': 'null',
    'void': 'void',
    'function': 'function',
    'builtinfunction': 'built-in function',
    'stdlibfunction': 'built-in function',
    'module': 'module',
    'futurevalue': 'future',
    'pythonlibvalue': 'py.lib',
}