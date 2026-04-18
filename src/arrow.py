def arrow(text, pos_start, pos_end, max_lines=3):
    if not text:
        return ""

    lines = text.splitlines()
    if text.endswith("\n"):
        lines.append("")

    start_line = max(0, pos_start.ln)
    end_line = max(start_line, pos_end.ln)
    end_col = pos_end.col

    if end_line > start_line and end_col == 0:
        end_line -= 1
        end_col = len(lines[end_line]) if end_line < len(lines) else 0

    shown_end_line = min(end_line, start_line + max_lines - 1)
    number_width = len(str(shown_end_line + 1))
    result_lines = []

    for line_no in range(start_line, shown_end_line + 1):
        line = lines[line_no] if line_no < len(lines) else ""
        
        def expand_tabs_to_col(s, col):
            expanded = ""
            pos = 0
            for i, c in enumerate(s):
                if i >= col:
                    break
                if c == "\t":
                    expanded += "    "
                    pos += 4
                else:
                    expanded += c
                    pos += 1
            return pos
        
        display_line = line.replace("\t", "    ")

        col_start = pos_start.col if line_no == start_line else 0
        col_end = end_col if line_no == end_line else len(line)
        col_start_expanded = expand_tabs_to_col(line, col_start)
        col_end_expanded = expand_tabs_to_col(line, col_end)
        col_end_expanded = max(col_start_expanded + 1, col_end_expanded)

        prefix = f"{line_no + 1:>{number_width}} | "
        result_lines.append(prefix + display_line)
        result_lines.append(" " * len(prefix) + " " * col_start_expanded + "^" * (col_end_expanded - col_start_expanded))

    if end_line > shown_end_line:
        result_lines.append(" " * (number_width + 3) + "...")

    return "\n".join(result_lines)