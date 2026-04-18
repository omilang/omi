from dataclasses import dataclass


@dataclass
class FixApplicationResult:
    text: str
    changed: bool


def apply_fixes(text, issues):
    replacements = []
    text_len = len(text)

    for order, issue in enumerate(issues):
        if issue.fix_start is None or issue.fix_end is None or issue.replacement is None:
            continue
        if not isinstance(issue.fix_start, int) or not isinstance(issue.fix_end, int):
            continue
        start = max(0, min(issue.fix_start, text_len))
        end = max(0, min(issue.fix_end, text_len))
        if end < start:
            continue
        replacements.append((start, end, issue.replacement, order))

    if not replacements:
        return FixApplicationResult(text=text, changed=False)

    replacements.sort(key=lambda item: (item[0], item[1], item[3]))

    filtered = []
    last_end = -1
    for start, end, replacement, order in replacements:
        if filtered and start < last_end:
            prev_start, prev_end, prev_replacement, _ = filtered[-1]
            if start == prev_start and end == prev_end and replacement == prev_replacement:
                continue
            continue
        filtered.append((start, end, replacement, order))
        last_end = end

    filtered.sort(key=lambda item: item[0], reverse=True)

    updated = text
    for start, end, replacement, _ in filtered:
        updated = updated[:start] + replacement + updated[end:]

    return FixApplicationResult(text=updated, changed=(updated != text))
