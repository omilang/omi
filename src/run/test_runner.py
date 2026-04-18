import asyncio
import os
import time

from src.main.interpret import Interpreter
from src.main.lexer import Lexer
from src.main.parser.parser import Parser
from src.main.symboltable import SymbolTable
from src.preprocessor import process
from src.run.async_runtime import ensure_event_loop, run_pending_tasks
from src.run.context import Context
from src.run.run import global_symbol_table
from src.run.source import read_source_file
from src.var.keyword import TEST_FILE_EXTENSION
import src.var.flags as runtime_flags


class TestReporter:
    def __init__(self):
        self._suite_stack = []
        self.events = []
        self.records = []
        self.suite_errors = []

    def begin_suite(self, suite_node):
        suite_name = suite_node.name_tok.value
        depth = len(self._suite_stack)
        self.events.append(("suite_start", depth, suite_name))
        self._suite_stack.append(suite_name)

    def end_suite(self, suite_node):
        if self._suite_stack:
            suite_name = self._suite_stack.pop()
        else:
            suite_name = suite_node.name_tok.value
        depth = len(self._suite_stack)
        self.events.append(("suite_end", depth, suite_name))

    def record_test(self, test_node, status, duration, error):
        depth = len(self._suite_stack)
        record = {
            "suite_path": list(self._suite_stack),
            "description": test_node.description_tok.value,
            "status": status,
            "duration": duration,
            "error": error,
            "node": test_node,
        }
        self.records.append(record)
        self.events.append(("test", depth, record))

    def record_suite_error(self, suite_node, error):
        suite_name = suite_node.name_tok.value
        depth = len(self._suite_stack)
        self.suite_errors.append((suite_name, error))
        self.events.append(("suite_error", depth, suite_name, error))


class _Colors:
    RESET = "\033[0m"
    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    CYAN = "\033[36m"


def _supports_color():
    if os.environ.get("NO_COLOR"):
        return False
    return hasattr(os.sys.stdout, "isatty") and os.sys.stdout.isatty()


def _color(text, ansi_color):
    if not _supports_color():
        return text
    return f"{ansi_color}{text}{_Colors.RESET}"


def _format_runtime_error(error):
    if error is None:
        return ""

    details = getattr(error, "details", None)
    if details:
        return f"RTError: {details}"

    return str(error)


def _discover_test_files(path):
    if os.path.isfile(path):
        if not path.lower().endswith(TEST_FILE_EXTENSION):
            raise ValueError("RTError: Test files must have .test.omi extension")
        return [os.path.abspath(path)]

    if not os.path.isdir(path):
        raise FileNotFoundError(f"Path not found: {path}")

    discovered = []
    for root, _, files in os.walk(path):
        for file_name in files:
            if file_name.lower().endswith(TEST_FILE_EXTENSION):
                discovered.append(os.path.abspath(os.path.join(root, file_name)))

    discovered.sort()
    return discovered


def _run_test_file(file_path):
    reporter = TestReporter()

    runtime_flags.debug = False
    runtime_flags.noecho = False
    runtime_flags.eval_enabled = False
    runtime_flags.notypes = False
    runtime_flags.noasync = False
    runtime_flags.repl_output_emitted = False
    runtime_flags.repl_output_ended_with_newline = True

    script = read_source_file(file_path)
    clean_script = process(script)

    lexer = Lexer(file_path, clean_script)
    tokens, lex_error = lexer.make_tokens()
    if lex_error:
        return {
            "file": file_path,
            "reporter": reporter,
            "fatal_error": lex_error,
            "duration": 0.0,
        }

    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error:
        return {
            "file": file_path,
            "reporter": reporter,
            "fatal_error": ast.error,
            "duration": 0.0,
        }

    interpreter = Interpreter()
    interpreter.test_reporter = reporter

    file_context = Context(f"<test:{os.path.basename(file_path)}>")
    file_context.symbol_table = SymbolTable(global_symbol_table)

    start = time.perf_counter()
    loop = ensure_event_loop(file_context)

    result = interpreter.visit(ast.node, file_context)
    fatal_error = None

    if result.signal == "exception" and result.exception_data is not None:
        fatal_error = result.exception_data
    elif result.error is not None:
        fatal_error = result.error

    if fatal_error is None:
        pending_error = run_pending_tasks(file_context)
        if pending_error is not None:
            fatal_error = pending_error

    if loop is not None and not loop.is_closed():
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending:
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    duration = time.perf_counter() - start
    return {
        "file": file_path,
        "reporter": reporter,
        "fatal_error": fatal_error,
        "duration": duration,
    }


def _print_report(file_result):
    file_path = file_result["file"]
    reporter = file_result["reporter"]

    print(_color(f"Running tests: {file_path}", _Colors.CYAN))

    if file_result["fatal_error"] is not None:
        print(_color(f"  FATAL: {_format_runtime_error(file_result['fatal_error'])}", _Colors.RED))
        print("")
        return

    for event in reporter.events:
        event_type = event[0]

        if event_type == "suite_start":
            _, depth, suite_name = event
            indent = "  " * depth
            print(f"{indent}{_color('[SUITE]', _Colors.CYAN)} {suite_name}")
            continue

        if event_type == "suite_error":
            _, depth, suite_name, error = event
            indent = "  " * (depth + 1)
            print(f"{indent}{_color('[SUITE-ERROR]', _Colors.RED)} {suite_name}: {_format_runtime_error(error)}")
            continue

        if event_type == "test":
            _, depth, record = event
            indent = "  " * (depth + 1)
            duration = f"{record['duration']:.3f}s"
            if record["status"] == "passed":
                marker = _color("[PASS]", _Colors.GREEN)
            elif record["status"] == "failed":
                marker = _color("[FAIL]", _Colors.RED)
            else:
                marker = _color("[SKIP]", _Colors.YELLOW)

            print(f"{indent}{marker} {record['description']} ({duration})")
            if record["error"] is not None:
                print(f"{indent}  {_format_runtime_error(record['error'])}")

    print("")


def run_tests(path):
    test_files = _discover_test_files(path)

    if not test_files:
        print("No .test.omi files found")
        return 0

    total_start = time.perf_counter()

    total_passed = 0
    total_failed = 0
    total_skipped = 0
    had_fatal = False

    for file_path in test_files:
        file_result = _run_test_file(file_path)
        _print_report(file_result)

        reporter = file_result["reporter"]
        for record in reporter.records:
            if record["status"] == "passed":
                total_passed += 1
            elif record["status"] == "failed":
                total_failed += 1
            elif record["status"] == "skipped":
                total_skipped += 1

        total_failed += len(reporter.suite_errors)

        if file_result["fatal_error"] is not None:
            had_fatal = True
            total_failed += 1

    total_duration = time.perf_counter() - total_start

    summary = (
        f"Summary: {total_passed} passed, {total_failed} failed, "
        f"{total_skipped} skipped ({total_duration:.3f}s total)"
    )

    if total_failed > 0 or had_fatal:
        print(_color(summary, _Colors.RED))
        return 1

    print(_color(summary, _Colors.GREEN))
    return 0
