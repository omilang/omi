import json
from dataclasses import dataclass
from typing import Dict, List

from src.arrow import arrow
from src.linter.rule import LintLevel
import src.var.ansi as ansi


class _Colors:
    GREEN = "green"
    RED = "red"
    YELLOW = "yellow"
    MAGENTA = "magenta"
    CYAN = "cyan"


def _color(text, ansi_color):
    return ansi.wrap(text, ansi_color)


@dataclass
class LintReport:
    issues: List[object]
    files: List[str]
    summary: Dict[str, int]
    source_by_file: Dict[str, str] = None

    @classmethod
    def from_issues(cls, issues, files=None, source_by_file=None):
        summary = {"errors": 0, "warnings": 0, "style": 0, "security": 0, "auto_fixable": 0}
        for issue in issues:
            if issue.level == LintLevel.ERROR:
                summary["errors"] += 1
            elif issue.level == LintLevel.WARNING:
                summary["warnings"] += 1
            elif issue.level == LintLevel.STYLE:
                summary["style"] += 1
            elif issue.level == LintLevel.SECURITY:
                summary["security"] += 1
            if getattr(issue, "auto_fixable", False):
                summary["auto_fixable"] += 1
        return cls(list(issues), list(files or []), summary, source_by_file or {})

    def __post_init__(self):
        if self.source_by_file is None:
            self.source_by_file = {}

    def to_text(self, source_by_file=None):
        if source_by_file is None:
            source_by_file = self.source_by_file or {}
        if not self.issues:
            return _color("✓ No lint issues found.", _Colors.GREEN)

        lines = []
        grouped = {}
        for issue in self.issues:
            grouped.setdefault(issue.file, []).append(issue)

        for file_name, file_issues in grouped.items():
            lines.append(_color(f"Linting {file_name}...", _Colors.CYAN))
            lines.append("")
            source = source_by_file.get(file_name, "")
            for issue in file_issues:
                level_marker = {
                    LintLevel.ERROR: "ERROR",
                    LintLevel.WARNING: "WARN",
                    LintLevel.STYLE: "STYLE",
                    LintLevel.SECURITY: "SECURITY",
                }[issue.level]
                
                level_color = {
                    LintLevel.ERROR: _Colors.RED,
                    LintLevel.WARNING: _Colors.YELLOW,
                    LintLevel.STYLE: _Colors.CYAN,
                    LintLevel.SECURITY: _Colors.MAGENTA,
                }[issue.level]
                
                level_text = _color(f"[{level_marker}]", level_color)
                lines.append(
                    f"{issue.file}:{issue.pos_start.ln + 1}:{issue.pos_start.col + 1} {level_text} [{issue.rule}] {issue.message}"
                )
                if issue.line:
                    lines.append(f"   {arrow(source or issue.line, issue.pos_start, issue.pos_end).replace(chr(10), chr(10) + '   ')}")
                if issue.suggestion:
                    lines.append(f"   hint: {issue.suggestion}")
                lines.append("")

        error_count = self.summary['errors']
        warning_count = self.summary['warnings']
        style_count = self.summary['style']
        security_count = self.summary['security']
        
        summary_parts = []
        if error_count > 0:
            summary_parts.append(_color(f"{error_count} error(s)", _Colors.RED))
        else:
            summary_parts.append(_color(f"{error_count} error(s)", _Colors.GREEN))
        
        if warning_count > 0:
            summary_parts.append(_color(f"{warning_count} warning(s)", _Colors.YELLOW))
        else:
            summary_parts.append(_color(f"{warning_count} warning(s)", _Colors.GREEN))
        
        if style_count > 0:
            summary_parts.append(_color(f"{style_count} style issue(s)", _Colors.CYAN))
        else:
            summary_parts.append(_color(f"{style_count} style issue(s)", _Colors.GREEN))
        
        if security_count > 0:
            summary_parts.append(_color(f"{security_count} security issue(s)", _Colors.MAGENTA))
        else:
            summary_parts.append(_color(f"{security_count} security issue(s)", _Colors.GREEN))
        
        summary_line = f"Summary: {', '.join(summary_parts)}"
        lines.append(summary_line)
        
        if self.summary["auto_fixable"]:
            lines.append(_color(f"Auto-fixable: {self.summary['auto_fixable']}", _Colors.GREEN))
        
        return "\n".join(lines).rstrip() + "\n"

    def to_json(self):
        return json.dumps(
            {
                "files": self.files,
                "issues": [
                    {
                        "rule": issue.rule,
                        "level": issue.level.value,
                        "message": issue.message,
                        "file": issue.file,
                        "line": issue.pos_start.ln + 1,
                        "column": issue.pos_start.col + 1,
                        "end_line": issue.pos_end.ln + 1,
                        "end_column": issue.pos_end.col + 1,
                        "suggestion": issue.suggestion,
                        "auto_fixable": issue.auto_fixable,
                    }
                    for issue in self.issues
                ],
                "summary": self.summary,
            },
            ensure_ascii=False,
            indent=2,
        )
