from dataclasses import dataclass
from enum import Enum
from typing import Callable, Optional

from src.position import Position


class LintLevel(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    STYLE = "style"
    SECURITY = "security"


@dataclass
class LintIssue:
    rule: str
    level: LintLevel
    message: str
    pos_start: Position
    pos_end: Position
    file: str
    line: str
    suggestion: Optional[str] = None
    auto_fix: Optional[Callable] = None
    fix_start: Optional[int] = None
    fix_end: Optional[int] = None
    replacement: Optional[str] = None

    @property
    def auto_fixable(self):
        return self.auto_fix is not None or (self.fix_start is not None and self.fix_end is not None and self.replacement is not None)


class LintRule:
    name = "base-rule"
    level = LintLevel.WARNING
    description = ""
    enabled_by_default = True

    def __init__(self, config=None):
        self.config = config or {}

    def check(self, ast, context):
        return []
