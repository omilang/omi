import os
import re
from dataclasses import dataclass

from src.linter.config import LintConfig
from src.linter.context import LintContext, LintRunResult
from src.linter.context import LintOptions, ScopeState, SymbolInfo
from src.linter.fixer import apply_fixes
from src.linter.report import LintReport
from src.linter.rule import LintIssue, LintLevel
from src.preprocessor import process
from src.main.lexer import Lexer
from src.main.parser.parser import Parser
from src.nodes.block import BlockNode
from src.nodes.condition.ifN import IfNode
from src.nodes.control.asyncgroup import AsyncGroupNode
from src.nodes.control.flow import CaseNode, MatchNode, PatternNode, TryNode
from src.nodes.directives.setN import SetDirectiveNode
from src.nodes.directives.typealiasN import TypeAliasNode
from src.nodes.directives.useN import UseDirectiveNode
from src.nodes.function.awaitN import AwaitNode
from src.nodes.function.call import CallNode
from src.nodes.function.funcdef import FuncDefNode
from src.nodes.imports.importN import ImportNode
from src.nodes.imports.moduleaccess import ModuleAccessNode
from src.nodes.jump.breakN import BreakNode
from src.nodes.jump.continueN import ContinueNode
from src.nodes.jump.returnN import ReturnNode
from src.nodes.loops.forN import ForNode
from src.nodes.loops.whileN import WhileNode
from src.nodes.ops.binop import BinOpNode
from src.nodes.ops.nullcoal import NullCoalNode
from src.nodes.ops.ternaryop import TernaryOpNode
from src.nodes.ops.unaryop import UnaryOpNode
from src.nodes.testing.expect import ExpectNode
from src.nodes.testing.hook import HookNode
from src.nodes.testing.suite import SuiteNode
from src.nodes.testing.testcase import TestCaseNode
from src.nodes.types.dict import DictNode
from src.nodes.types.enumdef import EnumDefNode
from src.nodes.types.fstring import FStringNode
from src.nodes.types.list import ListNode
from src.nodes.types.number import NumberNode
from src.nodes.types.string import StringNode
from src.nodes.types.subscript import DictSubscriptNode
from src.nodes.types.traitdef import TraitDefNode
from src.nodes.types.typeannotation import DictTypeAnnotation, TypeAnnotationNode
from src.nodes.variables.access import VarAccessNode
from src.nodes.variables.assign import VarAssignNode
from src.run.source import read_source_file
from src.var.builtin import BUILTIN_MODULES
from src.var.keyword import FILE_FORMAT, TEST_FILE_EXTENSION
from src.var.lint import BUILTIN_SYMBOLS, DEFAULT_LINT_MAX_LINE_LENGTH, DEFAULT_RULES, LEVELS


@dataclass
class _FileLintResult:
    file: str
    source: str
    processed_source: str
    issues: list
    fixed_source: str


def _is_node(value):
    return hasattr(value, "__dict__") and value.__class__.__name__.endswith("Node")


def _node_children(node):
    for key, value in getattr(node, "__dict__", {}).items():
        if key.startswith("pos_"):
            continue
        if key in {"tok", "op_tok", "var_name_tok", "alias_tok", "attribute_tok", "module_path_tok", "description_tok", "name_tok", "catch_var_tok"}:
            if _is_node(value):
                yield value
            continue
        if _is_node(value):
            yield value
        elif isinstance(value, dict):
            for item in value.values():
                if _is_node(item):
                    yield item
                elif isinstance(item, (list, tuple)):
                    for inner in item:
                        if _is_node(inner):
                            yield inner
        elif isinstance(value, (list, tuple)):
            for item in value:
                if _is_node(item):
                    yield item
                elif isinstance(item, tuple):
                    for inner in item:
                        if _is_node(inner):
                            yield inner


def _token_name(node):
    tok = getattr(node, "var_name_tok", None) or getattr(node, "name_tok", None) or getattr(node, "description_tok", None)
    if tok is not None and hasattr(tok, "value"):
        return tok.value
    if hasattr(node, "name"):
        return node.name
    return None


def _annotation_text(context, annotation):
    if annotation is None:
        return ""
    if isinstance(annotation, DictTypeAnnotation):
        return str(annotation)
    if isinstance(annotation, TypeAnnotationNode):
        return context.source_slice(annotation.pos_start, annotation.pos_end)
    return str(annotation)


def _looks_like_secret(text):
    lowered = text.lower()
    if "sk-" in text or "api_key" in lowered or "secret" in lowered or "token" in lowered:
        return True
    return len(text) >= 24 and any(char.isdigit() for char in text) and any(char.isalpha() for char in text)


def _infer_literal_type(node):
    if isinstance(node, NumberNode):
        return "float" if isinstance(node.tok.value, float) else "int"
    if isinstance(node, StringNode):
        return "string"
    if isinstance(node, ListNode):
        return "array"
    if isinstance(node, DictNode):
        return "dict"
    return None


def _annotation_matches(annotation, inferred_type):
    if annotation is None or inferred_type is None:
        return True
    if isinstance(annotation, DictTypeAnnotation):
        if inferred_type == "dict":
            return True
        return False
    if isinstance(annotation, TypeAnnotationNode):
        normalized = []
        for part in annotation.type_parts:
            normalized.append(part.split("<", 1)[0].strip().lower())
        if inferred_type in normalized or "every" in normalized:
            return True
        if inferred_type == "int" and "number" in normalized:
            return True
        return False
    return True


class LintAnalyzer:
    def __init__(self, context):
        self.context = context
        self.issues = []
        self.scope_stack = []
        self.source = context.source
        self.processed_source = context.processed_source
        self._module_cache = {}

        root = ScopeState("module")
        for name in BUILTIN_SYMBOLS:
            root.symbols[name] = SymbolInfo(name, "builtin", None, None, is_const=True, assigned_count=1, used=False)
        self.scope_stack.append(root)

    @property
    def scope(self):
        return self.scope_stack[-1]

    def push_scope(self, name):
        scope = ScopeState(name, self.scope)
        self.scope_stack.append(scope)
        return scope

    def pop_scope(self):
        scope = self.scope_stack.pop()
        self._finalize_scope(scope)
        return scope

    def analyze(self, ast):
        self._visit(ast)
        if len(self.scope_stack) == 1:
            self._finalize_scope(self.scope)
        return self.issues

    def _finalize_scope(self, scope):
        for symbol in scope.symbols.values():
            if symbol.kind in {"var", "param"} and not symbol.used:
                self._issue(
                    "unused-var",
                    LintLevel.WARNING,
                    symbol.pos_start,
                    symbol.pos_end,
                    f"Variable '{symbol.name}' is declared but never used",
                    suggestion=f"Remove unused variable '{symbol.name}' or use it",
                )
            if symbol.kind == "import" and not symbol.used:
                line_start, line_end = self.context.line_bounds(symbol.pos_start.ln)
                self._issue(
                    "unused-import",
                    LintLevel.WARNING,
                    symbol.pos_start,
                    symbol.pos_end,
                    f"Imported module '{symbol.name}' is never used",
                    suggestion=f"Remove unused import '{symbol.name}'",
                    fix_start=line_start,
                    fix_end=line_end,
                    replacement="",
                )
            if symbol.kind == "var" and not symbol.is_const and symbol.assigned_count == 1 and symbol.used:
                line_start, _ = self.context.line_bounds(symbol.pos_start.ln)
                line = self.context.get_line(symbol.pos_start)
                leading_ws = len(line) - len(line.lstrip(" \t"))
                self._issue(
                    "prefer-const",
                    LintLevel.WARNING,
                    symbol.pos_start,
                    symbol.pos_start,
                    f"Variable '{symbol.name}' is never reassigned; use const",
                    suggestion=f"Consider changing '{symbol.name}' to const",
                    fix_start=line_start + leading_ws,
                    fix_end=line_start + leading_ws + 3,
                    replacement="const",
                )

    def _issue(self, rule, level, pos_start, pos_end, message, suggestion=None, fix_start=None, fix_end=None, replacement=None):
        if pos_start is None:
            return
        line = self.context.get_line(pos_start)
        self.issues.append(
            LintIssue(
                rule=rule,
                level=level,
                message=message,
                pos_start=pos_start,
                pos_end=pos_end or pos_start,
                file=self.context.filename,
                line=line,
                suggestion=suggestion,
                fix_start=fix_start,
                fix_end=fix_end,
                replacement=replacement,
            )
        )

    def _declare(self, name, kind, pos_start, pos_end, node=None, is_const=False, is_import=False, is_param=False, type_annotation=None, module_path=None):
        existing_outer, _ = self.scope.resolve_outer(name)
        if existing_outer is not None and kind in {"var", "param", "import", "function", "type", "enum", "trait"}:
            self._issue(
                "no-shadow",
                LintLevel.WARNING,
                pos_start,
                pos_end,
                f"Name '{name}' shadows a symbol from an outer scope",
                suggestion=f"Rename '{name}' to avoid shadowing",
            )

        symbol = self.scope.symbols.get(name)
        if symbol is None:
            symbol = SymbolInfo(name, kind, pos_start, pos_end, node=node, is_const=is_const, is_import=is_import, is_param=is_param, type_annotation=type_annotation, module_path=module_path)
            self.scope.symbols[name] = symbol
        else:
            symbol.kind = kind
            if symbol.pos_start is None:
                symbol.pos_start = pos_start
            if symbol.pos_end is None:
                symbol.pos_end = pos_end
            symbol.node = node or symbol.node
            symbol.is_const = symbol.is_const or is_const
            symbol.is_import = symbol.is_import or is_import
            symbol.is_param = symbol.is_param or is_param
            symbol.type_annotation = type_annotation or symbol.type_annotation
            symbol.module_path = module_path or symbol.module_path
        symbol.assigned_count += 1 if kind in {"var", "param", "import", "function", "type", "enum", "trait"} else 0
        return symbol

    def _resolve(self, name):
        symbol, _ = self.scope.resolve(name)
        return symbol

    def _visit(self, node):
        if node is None:
            return False

        method = getattr(self, f"visit_{node.__class__.__name__}", None)
        if method is not None:
            return bool(method(node))

        for child in _node_children(node):
            self._visit(child)
        return False

    def visit_BlockNode(self, node):
        terminated = False
        for stmt in node.element_nodes:
            if terminated:
                self._issue(
                    "unreachable-code",
                    LintLevel.ERROR,
                    stmt.pos_start,
                    stmt.pos_end,
                    "Code is unreachable after a terminating statement",
                )
                break
            terminated = bool(self._visit(stmt)) or terminated
        return False

    def visit_ReturnNode(self, node):
        if node.node_to_return is not None:
            self._visit(node.node_to_return)
        return True

    def visit_BreakNode(self, node):
        return True

    def visit_ContinueNode(self, node):
        return True

    def visit_VarAccessNode(self, node):
        name = node.var_name_tok.value
        symbol = self._resolve(name)
        if symbol is None:
            self._issue(
                "undefined-var",
                LintLevel.ERROR,
                node.pos_start,
                node.pos_end,
                f"Variable '{name}' is used before it is declared",
            )
        else:
            symbol.used = True
        return False

    def visit_VarAssignNode(self, node):
        name = node.var_name_tok.value
        annotation = node.type_annotation
        if node.value_node is not None:
            self._visit(node.value_node)

        inferred_type = _infer_literal_type(node.value_node) if node.value_node is not None else None
        if annotation is not None and node.value_node is not None and not _annotation_matches(annotation, inferred_type):
            self._issue(
                "type-mismatch",
                LintLevel.ERROR,
                node.pos_start,
                node.pos_end,
                f"Type mismatch for '{name}'",
                suggestion=f"Expected {_annotation_text(self.context, annotation)}",
            )

        if node.is_reassign:
            symbol = self._resolve(name)
            if symbol is None:
                self._issue(
                    "undefined-var",
                    LintLevel.ERROR,
                    node.pos_start,
                    node.pos_end,
                    f"Variable '{name}' is used before it is declared",
                )
                symbol = self._declare(name, "var", node.pos_start, node.pos_end, node=node, type_annotation=annotation)
            else:
                if symbol.is_const:
                    self._issue(
                        "const-reassign",
                        LintLevel.ERROR,
                        node.pos_start,
                        node.pos_end,
                        f"Cannot reassign constant '{name}'",
                    )
                symbol.assigned_count += 1
                symbol.used = True
                if annotation is not None:
                    symbol.type_annotation = annotation
        else:
            symbol = self.scope.symbols.get(name)
            if symbol is None:
                symbol = self._declare(name, "var", node.pos_start, node.pos_end, node=node, is_const=node.is_const, type_annotation=annotation)
            else:
                symbol.assigned_count += 1
                symbol.is_const = symbol.is_const or node.is_const
                symbol.type_annotation = annotation or symbol.type_annotation
            if node.is_const:
                symbol.is_const = True
        return False

    def visit_FuncDefNode(self, node):
        fn_name = node.var_name_tok.value if node.var_name_tok else None
        if fn_name:
            self._declare(fn_name, "function", node.pos_start, node.pos_end, node=node)

        self.push_scope(fn_name or "<lambda>")
        seen_params = set()
        for arg_tok, arg_type, default_node in zip(node.arg_name_toks, node.arg_types, node.arg_defaults):
            arg_name = arg_tok.value
            if arg_name in seen_params:
                self._issue(
                    "duplicate-param",
                    LintLevel.ERROR,
                    arg_tok.pos_start,
                    arg_tok.pos_end,
                    f"Duplicate parameter '{arg_name}'",
                )
            seen_params.add(arg_name)
            self._declare(arg_name, "param", arg_tok.pos_start, arg_tok.pos_end, is_param=True, type_annotation=arg_type)
            if default_node is not None:
                self._visit(default_node)

        self._visit(node.body_node)

        return_type_text = str(node.return_type).strip().lower() if node.return_type is not None else None
        if (
            node.return_type is not None
            and return_type_text != "void"
            and not node.should_auto_return
            and not self._contains_return(node.body_node)
        ):
            self._issue(
                "missing-return",
                LintLevel.ERROR,
                node.pos_start,
                node.pos_end,
                f"Function '{fn_name or '<lambda>'}' declares a return type but never returns a value",
            )

        self.pop_scope()
        return False

    def _contains_return(self, node):
        if node is None:
            return False
        if isinstance(node, ReturnNode):
            return True
        if isinstance(node, BlockNode):
            return any(self._contains_return(stmt) for stmt in node.element_nodes)
        if isinstance(node, IfNode):
            for condition, expr, _ in node.cases:
                if self._contains_return(expr):
                    return True
            if node.else_case and self._contains_return(node.else_case[0]):
                return True
            return False
        return any(self._contains_return(child) for child in _node_children(node))

    def visit_ImportNode(self, node):
        module_path = node.module_path_tok.value
        alias = node.alias_tok.value
        self._declare(alias, "import", node.pos_start, node.pos_end, node=node, is_import=True, module_path=module_path)

        if module_path == "omi:system":
            self._issue(
                "unsafe-import",
                LintLevel.SECURITY,
                node.pos_start,
                node.pos_end,
                "Importing 'omi:system' can expose process and filesystem side effects",
            )

        if module_path.startswith("omi:"):
            if module_path not in BUILTIN_MODULES:
                self._issue(
                    "invalid-import",
                    LintLevel.ERROR,
                    node.pos_start,
                    node.pos_end,
                    f"Unknown standard library module '{module_path}'",
                )
            return False

        current_fn = node.pos_start.fn
        base_dir = os.path.dirname(os.path.abspath(current_fn)) if current_fn and current_fn != "<stdin>" else os.getcwd()
        module_file = None
        for ext in FILE_FORMAT:
            candidate = os.path.join(base_dir, module_path + ext)
            if os.path.isfile(candidate):
                module_file = candidate
                break
        if module_file is None:
            self._issue(
                "invalid-import",
                LintLevel.ERROR,
                node.pos_start,
                node.pos_end,
                f"Module '{module_path}' not found",
            )
            return False

        if module_file in self._module_cache:
            if not self._module_cache[module_file]:
                self._issue(
                    "invalid-import",
                    LintLevel.ERROR,
                    node.pos_start,
                    node.pos_end,
                    f"Module '{module_path}' does not declare '@use module'",
                )
            return False

        try:
            script = read_source_file(module_file)
            clean_script = process(script)
            lexer = Lexer(module_file, clean_script)
            tokens, error = lexer.make_tokens()
            if error:
                self._module_cache[module_file] = False
                self._issue(
                    "invalid-import",
                    LintLevel.ERROR,
                    node.pos_start,
                    node.pos_end,
                    f"Error in module '{module_path}': {error.as_string()}",
                )
                return False
            parser = Parser(tokens)
            ast = parser.parse()
            if ast.error:
                self._module_cache[module_file] = False
                self._issue(
                    "invalid-import",
                    LintLevel.ERROR,
                    node.pos_start,
                    node.pos_end,
                    f"Error in module '{module_path}': {ast.error.as_string()}",
                )
                return False
            stmts = ast.node.element_nodes if isinstance(ast.node, BlockNode) else []
            has_module_decl = any(isinstance(stmt, UseDirectiveNode) and stmt.directive.lower() == "module" for stmt in stmts)
            self._module_cache[module_file] = has_module_decl
            if not has_module_decl:
                self._issue(
                    "invalid-import",
                    LintLevel.ERROR,
                    node.pos_start,
                    node.pos_end,
                    f"Cannot import '{module_path}': file does not declare '@use module'",
                )
        except Exception:
            self._module_cache[module_file] = False
            self._issue(
                "invalid-import",
                LintLevel.ERROR,
                node.pos_start,
                node.pos_end,
                f"Failed to load module '{module_path}'",
            )
        return False

    def visit_UseDirectiveNode(self, node):
        directive = node.directive.lower()
        if directive == "eval":
            self.context.eval_enabled = True
        if directive == "module":
            self.context.module_enabled = True
        return False

    def visit_TypeAliasNode(self, node):
        self._declare(node.name_tok.value, "type", node.pos_start, node.pos_end, node=node)
        if isinstance(node.type_annotation, TypeAnnotationNode):
            text = self.context.source_slice(node.type_annotation.pos_start, node.type_annotation.pos_end)
            if "| null" in text and "?" not in text:
                self._issue(
                    "prefer-nullable",
                    LintLevel.WARNING,
                    node.type_annotation.pos_start,
                    node.type_annotation.pos_end,
                    "Prefer nullable shorthand 'T?' instead of 'T | null'",
                    suggestion="Use the 'T?' shorthand",
                    fix_start=node.type_annotation.pos_start.idx,
                    fix_end=node.type_annotation.pos_end.idx,
                    replacement=text.replace(" | null", "?"),
                )
        return False

    def visit_EnumDefNode(self, node):
        self._declare(node.name, "enum", node.pos_start, node.pos_end, node=node)
        return False

    def visit_TraitDefNode(self, node):
        self._declare(node.name, "trait", node.pos_start, node.pos_end, node=node)
        return False

    def visit_SetDirectiveNode(self, node):
        return False

    def visit_BinOpNode(self, node):
        self._visit(node.left_node)
        self._visit(node.right_node)
        if getattr(node.op_tok, "type", None) == "DIV":
            if isinstance(node.right_node, NumberNode) and node.right_node.tok.value == 0:
                self._issue(
                    "division-by-zero-risk",
                    LintLevel.SECURITY,
                    node.right_node.pos_start,
                    node.right_node.pos_end,
                    "Division by zero is possible here",
                )
        return False

    def visit_UnaryOpNode(self, node):
        self._visit(node.node)
        return False

    def visit_CallNode(self, node):
        if isinstance(node.node_to_call, VarAccessNode) and node.node_to_call.var_name_tok.value == "eval" and not self.context.eval_enabled:
            self._issue(
                "eval-usage",
                LintLevel.SECURITY,
                node.pos_start,
                node.pos_end,
                "eval() used without '@use eval'",
            )
        self._visit(node.node_to_call)
        for arg in node.arg_nodes:
            self._visit(arg)
        for value in node.kwarg_nodes.values():
            self._visit(value)
        return False

    def visit_ModuleAccessNode(self, node):
        self._visit(node.module_node)
        return False

    def visit_DictSubscriptNode(self, node):
        self._visit(node.base_node)
        self._visit(node.index_node)
        return False

    def visit_ListNode(self, node):
        for element in node.element_nodes:
            self._visit(element)
        return False

    def visit_DictNode(self, node):
        for key_node, value_node in node.pair_nodes:
            self._visit(key_node)
            self._visit(value_node)
        return False

    def visit_FStringNode(self, node):
        for kind, value in node.parts:
            if kind == "expr":
                self._visit(value)
            elif kind == "lit" and _looks_like_secret(value):
                self._issue(
                    "hardcoded-secret",
                    LintLevel.SECURITY,
                    node.pos_start,
                    node.pos_end,
                    "String literal looks like it contains a hardcoded secret",
                )
        return False

    def visit_IfNode(self, node):
        for condition, expr, _ in node.cases:
            self._visit(condition)
            self._visit(expr)
        if node.else_case:
            self._visit(node.else_case[0])
        return False

    def visit_ForNode(self, node):
        if node.start_value_node is not None:
            self._visit(node.start_value_node)
            self._visit(node.end_value_node)
            if node.step_value_node is not None:
                self._visit(node.step_value_node)
        else:
            self._visit(node.end_value_node)

        self._declare(node.var_name_tok.value, "var", node.var_name_tok.pos_start, node.var_name_tok.pos_end, node=node)
        self._visit(node.body_node)
        return False

    def visit_WhileNode(self, node):
        self._visit(node.condition_node)
        self._visit(node.body_node)
        return False

    def visit_TryNode(self, node):
        self.push_scope("try")
        self._visit(node.try_body)
        self.pop_scope()

        self.push_scope("catch")
        self._declare(node.catch_var_tok.value, "param", node.catch_var_tok.pos_start, node.catch_var_tok.pos_end, is_param=True)
        self._visit(node.catch_body)
        self.pop_scope()

        if node.final_body is not None:
            self.push_scope("final")
            self._visit(node.final_body)
            self.pop_scope()
        return False

    def visit_MatchNode(self, node):
        self._visit(node.expr)
        for case in node.cases:
            self.push_scope("case")
            self._visit(case)
            self.pop_scope()
        return False

    def visit_CaseNode(self, node):
        self._visit(node.pattern)
        self._visit(node.body)
        return False

    def visit_PatternNode(self, node):
        if node.capture_var_tok is not None:
            self._declare(node.capture_var_tok.value, "param", node.capture_var_tok.pos_start, node.capture_var_tok.pos_end, is_param=True)
        return False

    def visit_SuiteNode(self, node):
        for body_node in node.body_nodes:
            self._visit(body_node)
        for hook_nodes in node.hooks.values():
            for hook_node in hook_nodes:
                self._visit(hook_node)
        return False

    def visit_TestCaseNode(self, node):
        self.push_scope("test")
        self._visit(node.body_node)
        self.pop_scope()
        return False

    def visit_HookNode(self, node):
        self._visit(node.body_node)
        return False

    def visit_ExpectNode(self, node):
        self._visit(node.expr_node)
        if node.message_node is not None:
            self._visit(node.message_node)
        return False

    def visit_AsyncGroupNode(self, node):
        for value in node.params.values():
            self._visit(value)
        self._visit(node.body_node)
        return False

    def visit_AwaitNode(self, node):
        self._visit(node.expr_node)
        return False

    def visit_TernaryOpNode(self, node):
        self._visit(node.true_node)
        self._visit(node.cond_node)
        self._visit(node.false_node)
        return False

    def visit_NullCoalNode(self, node):
        self._visit(node.left)
        self._visit(node.right)
        return False


def _is_spacing_violation(line):
    code = line.split("//", 1)[0]
    code = re.sub(r'"(?:\\.|[^"\\])*"', '""', code)
    code = re.sub(r"'(?:\\.|[^'\\])*'", "''", code)
    return bool(re.search(r"\w(?:[+\-*/=]|==|!=|<=|>=)\w", code))


class LintRunner:
    def __init__(self, config_path=None, level=None, rules=None, fix=False, json_output=False, failfast=False):
        self.config_path = config_path
        self.level = level
        self.rules = rules
        self.fix = fix
        self.json_output = json_output
        self.failfast = failfast

    def _load_config(self, base_path):
        config = LintConfig.load(self.config_path, base_path)
        if self.level:
            config.level = self.level
        return config

    def lint_source(self, filename, source, processed_source=None, root_dir=None):
        processed_source = processed_source if processed_source is not None else process(source)
        config_base = os.path.dirname(os.path.abspath(filename)) if filename != "<stdin>" else (root_dir or os.getcwd())
        config = self._load_config(config_base)
        context = LintContext(filename=filename, source=source, processed_source=processed_source, config=config, options=None, root_dir=root_dir)
        lint_result = self._lint_with_context(context)
        return lint_result

    def lint_file(self, filename, source=None):
        if source is None:
            source = read_source_file(filename)
        return self.lint_source(filename, source)

    def lint_path(self, path):
        files = []
        if os.path.isdir(path):
            for root, _, filenames in os.walk(path):
                for name in filenames:
                    if not (name.endswith(".omi") or name.endswith(TEST_FILE_EXTENSION)):
                        continue
                    files.append(os.path.join(root, name))
        else:
            files.append(path)

        all_issues = []
        source_by_file = {}
        fixed_sources = {}
        for filename in files:
            source = read_source_file(filename)
            result = self.lint_source(filename, source)
            all_issues.extend(result.report.issues)
            source_by_file[filename] = source
            if result.fixed_sources.get(filename) is not None:
                fixed_sources[filename] = result.fixed_sources[filename]
                if self.fix:
                    with open(filename, "w", encoding="utf-8", newline="") as handle:
                        handle.write(result.fixed_sources[filename])

        report = LintReport.from_issues(all_issues, files=files, source_by_file=source_by_file)
        exit_code = 0
        if report.summary["errors"]:
            exit_code = 1
        elif any(issue.level != LintLevel.ERROR for issue in report.issues):
            exit_code = 2
        return LintRunResult(report=report, fixed_sources=fixed_sources, exit_code=exit_code)

    def _lint_with_context(self, context):
        text_issues = self._collect_text_issues(context)
        processed_source = context.processed_source
        lexer = Lexer(context.filename, processed_source)
        tokens, lexer_error = lexer.make_tokens()
        if lexer_error:
            issue = self._error_to_issue(context, lexer_error, "syntax-error")
            report = LintReport.from_issues(
                text_issues + [issue],
                files=[context.filename],
                source_by_file={context.filename: context.source},
            )
            return LintRunResult(report=report, fixed_sources={}, exit_code=1)

        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            issue = self._error_to_issue(context, ast.error, "syntax-error")
            report = LintReport.from_issues(
                text_issues + [issue],
                files=[context.filename],
                source_by_file={context.filename: context.source},
            )
            return LintRunResult(report=report, fixed_sources={}, exit_code=1)

        analyzer = LintAnalyzer(context)
        issues = text_issues + analyzer.analyze(ast.node)
        filtered_issues = self._filter_issues(issues, context.config)
        report = LintReport.from_issues(
            filtered_issues,
            files=[context.filename],
            source_by_file={context.filename: context.source},
        )

        fixed_source = None
        if self.fix and context.config.auto_fix_enabled:
            fixable_issues = [issue for issue in filtered_issues if issue.auto_fixable and (not context.config.auto_fix_rules or issue.rule in context.config.auto_fix_rules)]
            fixed_result = apply_fixes(context.source, fixable_issues)
            if fixed_result.changed:
                fixed_source = fixed_result.text

        exit_code = 0
        if report.summary["errors"]:
            exit_code = 1
        elif filtered_issues:
            exit_code = 2

        fixed_sources = {context.filename: fixed_source} if fixed_source is not None else {}
        return LintRunResult(report=report, fixed_sources=fixed_sources, exit_code=exit_code)

    def _collect_text_issues(self, context):
        issues = []
        previous_blank_lines = 0

        for line_index, line in enumerate(context.lines):
            if line.rstrip(" \t") != line:
                start, _ = context.line_bounds(line_index)
                trailing_start = start + len(line.rstrip(" \t"))
                trailing_end = start + len(line)
                issues.append(
                    LintIssue(
                        rule="trailing-whitespace",
                        level=LintLevel.STYLE,
                        message="Trailing whitespace detected",
                        pos_start=context.source_index_to_position(trailing_start),
                        pos_end=context.source_index_to_position(trailing_end),
                        file=context.filename,
                        line=line,
                        fix_start=trailing_start,
                        fix_end=trailing_end,
                        replacement="",
                    )
                )

            if len(line) > context.config.max_line_length:
                line_start, line_end = context.line_bounds(line_index)
                pos_start = context.source_index_to_position(line_start + context.config.max_line_length)
                pos_end = context.source_index_to_position(line_end)
                issues.append(
                    LintIssue(
                        rule="max-line-length",
                        level=LintLevel.STYLE,
                        message=f"Line exceeds {context.config.max_line_length} characters",
                        pos_start=pos_start,
                        pos_end=pos_end,
                        file=context.filename,
                        line=line,
                        suggestion="Break the line into smaller pieces",
                    )
                )

            if not line.strip():
                previous_blank_lines += 1
                if previous_blank_lines >= 3:
                    start, end = context.line_bounds(line_index)
                    issues.append(
                        LintIssue(
                            rule="empty-lines",
                            level=LintLevel.STYLE,
                            message="Too many consecutive empty lines",
                            pos_start=context.source_index_to_position(start),
                            pos_end=context.source_index_to_position(end),
                            file=context.filename,
                            line=line,
                            suggestion="Collapse consecutive empty lines",
                            fix_start=start,
                            fix_end=end,
                            replacement="",
                        )
                    )
            else:
                previous_blank_lines = 0

            if _is_spacing_violation(line):
                start, end = context.line_bounds(line_index)
                issues.append(
                    LintIssue(
                        rule="spacing-operators",
                        level=LintLevel.STYLE,
                        message="Missing spaces around an operator",
                        pos_start=context.source_index_to_position(start),
                        pos_end=context.source_index_to_position(end),
                        file=context.filename,
                        line=line,
                        suggestion="Insert spaces around operators",
                    )
                )

        return issues

    def _filter_issues(self, issues, config):
        if self.rules:
            allowed = set(self.rules)
            issues = [issue for issue in issues if issue.rule in allowed]
        elif config.rules:
            enabled = set()
            disabled = set()
            for rule_name, value in config.rules.items():
                if value is False:
                    disabled.add(rule_name)
                else:
                    enabled.add(rule_name)
            issues = [issue for issue in issues if issue.rule not in disabled and (not enabled or issue.rule in enabled)]

        if config.level == "error":
            issues = [issue for issue in issues if issue.level == LintLevel.ERROR]
        return issues

    def _error_to_issue(self, context, error, rule):
        pos_start = getattr(error, "pos_start", None)
        pos_end = getattr(error, "pos_end", pos_start)
        line = context.get_line(pos_start) if pos_start else ""
        return LintIssue(
            rule=rule,
            level=LintLevel.ERROR,
            message=getattr(error, "details", None) or getattr(error, "message", None) or str(error),
            pos_start=pos_start,
            pos_end=pos_end,
            file=context.filename,
            line=line,
        )


def lint_text(filename, source, config_path=None, level=None, rules=None, fix=False, json_output=False, failfast=False):
    runner = LintRunner(config_path=config_path, level=level, rules=rules, fix=fix, json_output=json_output, failfast=failfast)
    result = runner.lint_source(filename, source)
    return result
