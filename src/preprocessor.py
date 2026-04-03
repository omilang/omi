from src.var.flags import VALID_DIRECTIVES

def process(source):
    flags = {d: False for d in VALID_DIRECTIVES}

    lines = source.split('\n')
    clean_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('@use '):
            directive = stripped[5:].strip().lower()
            if directive in VALID_DIRECTIVES:
                flags[directive] = True
            clean_lines.append('')
        else:
            clean_lines.append(line)

    return '\n'.join(clean_lines), flags
