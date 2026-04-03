import re

from src.main.lexer import Lexer
from src.var.token import (
    TT_AT,
    TT_DOT,
    TT_E0F,
    TT_FLOAT,
    TT_IDENTIFIER,
    TT_INT,
    TT_KEYWORD,
    TT_STRING,
)


def process(source):
    lines = source.split('\n')
    substitutions = []
    clean_lines = []

    for line in lines:
        stripped = line.strip()
        parsed_set = _parse_set_directive(stripped)

        if parsed_set is not None:
            lhs, rhs, rhs_is_literal = parsed_set

            if rhs_is_literal:
                pat = re.compile(r'\b' + re.escape(lhs) + r'\b')
                substitutions.append((pat, rhs))
            else:
                pat = re.compile(r'\b' + re.escape(rhs) + r'\b')
                substitutions.append((pat, lhs))

            clean_lines.append(line)

        elif stripped.startswith('@'):
            clean_lines.append(line)

        else:
            clean_lines.append(_apply_substitutions(line, substitutions))

    return '\n'.join(clean_lines)


def _parse_set_directive(stripped_line):
    if not stripped_line.startswith('@'):
        return None

    tokens, error = Lexer("<preprocessor>", stripped_line).make_tokens()
    if error:
        return None

    idx = 0
    if tokens[idx].type != TT_AT:
        return None
    idx += 1

    if idx >= len(tokens) or not tokens[idx].matches(TT_KEYWORD, 'set'):
        return None
    idx += 1

    lhs, idx = _parse_name(tokens, idx)
    if lhs is None:
        return None

    if idx >= len(tokens) or not tokens[idx].matches(TT_KEYWORD, 'as'):
        return None
    idx += 1

    rhs, rhs_is_literal, idx = _parse_rhs(tokens, idx, stripped_line)
    if rhs is None:
        return None

    if idx >= len(tokens) or tokens[idx].type != TT_E0F:
        return None

    return lhs, rhs, rhs_is_literal


def _parse_name(tokens, idx):
    if idx >= len(tokens) or tokens[idx].type not in (TT_IDENTIFIER, TT_KEYWORD):
        return None, idx

    parts = [str(tokens[idx].value)]
    idx += 1

    while idx < len(tokens) and tokens[idx].type == TT_DOT:
        idx += 1
        if idx >= len(tokens) or tokens[idx].type not in (TT_IDENTIFIER, TT_KEYWORD):
            return None, idx
        parts.append(str(tokens[idx].value))
        idx += 1

    return '.'.join(parts), idx


def _parse_rhs(tokens, idx, source_line):
    if idx >= len(tokens):
        return None, False, idx

    tok = tokens[idx]
    if tok.type in (TT_STRING, TT_INT, TT_FLOAT):
        raw_value = source_line[tok.pos_start.idx:tok.pos_end.idx]
        return raw_value, True, idx + 1

    name, next_idx = _parse_name(tokens, idx)
    if name is None:
        return None, False, idx

    return name, False, next_idx


def _apply_substitutions(line, substitutions):
    if not substitutions:
        return line

    parts = []
    code_start = 0
    string_start = None
    quote_char = None
    escape = False
    i = 0

    while i < len(line):
        ch = line[i]

        if quote_char is not None:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == quote_char:
                parts.append(line[string_start:i + 1])
                quote_char = None
                string_start = None
                code_start = i + 1
            i += 1
            continue

        if ch in ('"', "'"):
            parts.append(_apply_to_segment(line[code_start:i], substitutions))
            string_start = i
            quote_char = ch
            i += 1
            continue

        if ch == '/' and i + 1 < len(line) and line[i + 1] == '/':
            parts.append(_apply_to_segment(line[code_start:i], substitutions))
            parts.append(line[i:])
            return ''.join(parts)

        i += 1

    if quote_char is not None:
        parts.append(line[string_start:])
    else:
        parts.append(_apply_to_segment(line[code_start:], substitutions))

    return ''.join(parts)


def _apply_to_segment(segment, substitutions):
    processed = segment
    for pat, replacement in substitutions:
        processed = pat.sub(replacement, processed)
    return processed

