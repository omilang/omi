from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.position import Position


@dataclass
class SymbolInfo:
    name: str
    kind: str
    pos_start: object
    pos_end: object
    node: object = None
    is_const: bool = False
    is_import: bool = False
    is_param: bool = False
    assigned_count: int = 0
    used: bool = False
    type_annotation: object = None
    module_path: Optional[str] = None


@dataclass
class ScopeState:
    name: str
    parent: Optional["ScopeState"] = None
    symbols: Dict[str, SymbolInfo] = field(default_factory=dict)

    def resolve(self, name):
        scope = self
        while scope is not None:
            symbol = scope.symbols.get(name)
            if symbol is not None:
                return symbol, scope
            scope = scope.parent
        return None, None

    def resolve_outer(self, name):
        if self.parent is None:
            return None, None
        return self.parent.resolve(name)


@dataclass
class LintOptions:
    config_path: Optional[str] = None
    level: str = "warning"
    rules: Optional[List[str]] = None
    fix: bool = False
    json_output: bool = False
    failfast: bool = False
    write_files: bool = False


@dataclass
class LintRunResult:
    report: object
    fixed_sources: Dict[str, str] = field(default_factory=dict)
    exit_code: int = 0


@dataclass
class LintContext:
    filename: str
    source: str
    processed_source: str
    config: object
    options: object = None
    root_dir: Optional[str] = None
    lines: List[str] = field(init=False)
    processed_lines: List[str] = field(init=False)
    line_offsets: List[int] = field(init=False)
    processed_line_offsets: List[int] = field(init=False)
    scope_stack: List[ScopeState] = field(default_factory=list)
    eval_enabled: bool = False
    module_enabled: bool = False
    imported_modules: List[str] = field(default_factory=list)

    def __post_init__(self):
        self.lines = self.source.splitlines()
        if self.source.endswith("\n"):
            self.lines.append("")
        self.processed_lines = self.processed_source.splitlines()
        if self.processed_source.endswith("\n"):
            self.processed_lines.append("")
        self.line_offsets = self._build_line_offsets(self.source)
        self.processed_line_offsets = self._build_line_offsets(self.processed_source)

    def _build_line_offsets(self, text):
        offsets = [0]
        for idx, char in enumerate(text):
            if char == "\n":
                offsets.append(idx + 1)
        return offsets

    def get_line(self, pos):
        if pos is None:
            return ""
        index = max(0, min(pos.ln, len(self.lines) - 1))
        if 0 <= index < len(self.lines):
            return self.lines[index]
        return ""

    def get_processed_line(self, pos):
        if pos is None:
            return ""
        index = max(0, min(pos.ln, len(self.processed_lines) - 1))
        if 0 <= index < len(self.processed_lines):
            return self.processed_lines[index]
        return ""

    def line_bounds(self, line_number, processed=False):
        lines = self.processed_lines if processed else self.lines
        offsets = self.processed_line_offsets if processed else self.line_offsets
        if line_number < 0 or line_number >= len(lines):
            return 0, 0
        start = offsets[line_number]
        if line_number + 1 < len(offsets):
            end = offsets[line_number + 1]
        else:
            end = len(self.processed_source if processed else self.source)
        return start, end

    def source_slice(self, start_pos, end_pos):
        if start_pos is None or end_pos is None:
            return ""
        return self.source[start_pos.idx:end_pos.idx]

    def processed_slice(self, start_pos, end_pos):
        if start_pos is None or end_pos is None:
            return ""
        return self.processed_source[start_pos.idx:end_pos.idx]

    def source_index_to_position(self, index):
        index = max(0, min(index, len(self.source)))
        line = 0
        column = 0
        for offset in self.line_offsets:
            if offset > index:
                break
            line += 1
        line = max(0, line - 1)
        if line < len(self.line_offsets):
            column = index - self.line_offsets[line]
        return Position(index, line, column, self.filename, self.source)


