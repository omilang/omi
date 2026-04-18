import configparser
import os
from dataclasses import dataclass, field
from fnmatch import fnmatch
from typing import Dict, List, Optional

from src.var.lint import DEFAULT_LINT_LEVEL, DEFAULT_LINT_MAX_LINE_LENGTH


@dataclass
class LintConfig:
    level: str = DEFAULT_LINT_LEVEL
    max_line_length: int = DEFAULT_LINT_MAX_LINE_LENGTH
    exclude: List[str] = field(default_factory=list)
    rules: Dict[str, object] = field(default_factory=dict)
    auto_fix_enabled: bool = True
    auto_fix_rules: List[str] = field(default_factory=list)

    @classmethod
    def load(cls, config_path: Optional[str], base_path: Optional[str] = None):
        if config_path:
            candidate = os.path.abspath(config_path)
            if os.path.isdir(candidate):
                candidate = os.path.join(candidate, ".omilint")
            else:
                if not candidate.endswith(".omilint"):
                    raise ValueError("Lint config file must have .omilint extension (e.g., .omilint, config.omilint)")

            if not os.path.isfile(candidate):
                raise ValueError(f"Lint config file not found: {candidate}")

            return cls._from_file(candidate)

        search_root = os.path.abspath(base_path or os.getcwd())
        candidates = []
        candidate = os.path.join(search_root, ".omilint")
        if os.path.isfile(candidate):
            candidates.append(candidate)

        for file in os.listdir(search_root):
            if file.endswith(".omilint"):
                candidate = os.path.join(search_root, file)
                if os.path.isfile(candidate):
                    candidates.append(candidate)

        if candidates:
            last_error = None
            for candidate in candidates:
                try:
                    return cls._from_file(candidate)
                except ValueError as err:
                    last_error = err
            if last_error is not None:
                raise last_error

        return cls()

    @classmethod
    def _from_file(cls, path):
        parser = configparser.ConfigParser(interpolation=None)
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                parser.read_file(handle)
        except configparser.Error as err:
            raise ValueError(f"Invalid lint config file '{path}': {err}")
        except OSError as err:
            raise ValueError(f"Failed to read lint config file '{path}': {err}")

        general = parser["general"] if parser.has_section("general") else {}
        rules = parser["rules"] if parser.has_section("rules") else {}
        auto_fix = parser["auto-fix"] if parser.has_section("auto-fix") else {}

        exclude = []
        raw_exclude = general.get("exclude", "") if hasattr(general, "get") else ""
        if raw_exclude:
            exclude = [item.strip() for item in raw_exclude.split(",") if item.strip()]

        auto_fix_rules = []
        raw_fix_rules = auto_fix.get("rules", "") if hasattr(auto_fix, "get") else ""
        if raw_fix_rules:
            auto_fix_rules = [item.strip() for item in raw_fix_rules.split(",") if item.strip()]

        parsed_rules = {}
        for key, value in getattr(rules, "items", lambda: [])():
            raw = value.strip().lower()
            if raw in {"true", "false"}:
                parsed_rules[key.strip()] = raw == "true"
            elif raw in {"error", "warning", "style", "security"}:
                parsed_rules[key.strip()] = raw
            else:
                parsed_rules[key.strip()] = value.strip()

        level = str(general.get("level", DEFAULT_LINT_LEVEL)).strip().lower() if hasattr(general, "get") else DEFAULT_LINT_LEVEL
        try:
            max_line_length = int(general.get("max_line_length", DEFAULT_LINT_MAX_LINE_LENGTH)) if hasattr(general, "get") else DEFAULT_LINT_MAX_LINE_LENGTH
        except (TypeError, ValueError):
            max_line_length = DEFAULT_LINT_MAX_LINE_LENGTH

        auto_fix_enabled = True
        if hasattr(auto_fix, "get"):
            auto_fix_enabled = str(auto_fix.get("enabled", "true")).strip().lower() != "false"

        return cls(
            level=level,
            max_line_length=max_line_length,
            exclude=exclude,
            rules=parsed_rules,
            auto_fix_enabled=auto_fix_enabled,
            auto_fix_rules=auto_fix_rules,
        )

    def should_exclude(self, path, root=None):
        if not self.exclude:
            return False

        target = os.path.basename(path).replace(os.sep, "/")
        rel = target
        if root:
            try:
                rel = os.path.relpath(path, root).replace(os.sep, "/")
            except ValueError:
                rel = target

        for pattern in self.exclude:
            if fnmatch(rel, pattern) or fnmatch(target, pattern):
                return True
        return False
