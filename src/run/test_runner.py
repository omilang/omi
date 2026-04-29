import asyncio
import json
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
import src.var.ansi as ansi


class TestReporter:
    def __init__(self, failfast=False):
        self._suite_stack = []
        self.events = []
        self.records = []
        self.suite_errors = []
        self.failfast = bool(failfast)
        self.stop_requested = False

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
        if self.failfast and status == "failed":
            self.stop_requested = True

    def record_suite_error(self, suite_node, error):
        suite_name = suite_node.name_tok.value
        depth = len(self._suite_stack)
        self.suite_errors.append((suite_name, error))
        self.events.append(("suite_error", depth, suite_name, error))
        if self.failfast:
            self.stop_requested = True


class _Colors:
    GREEN = "green"
    RED = "red"
    YELLOW = "yellow"
    CYAN = "cyan"


def _color(text, ansi_color):
    return ansi.wrap(text, ansi_color)


def _format_runtime_error(error):
    if error is None:
        return ""

    details = getattr(error, "details", None)
    if details:
        return f"RTError: {details}"

    return str(error)


def _format_duration(duration):
    if duration > 0 and duration < 0.0005:
        return "0.001s"
    return f"{duration:.3f}s"


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


def _run_test_file(file_path, failfast=False):
    reporter = TestReporter(failfast=failfast)

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
            duration = _format_duration(record['duration'])
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


def _build_file_json_result(file_result):
    reporter = file_result["reporter"]
    passed = 0
    failed = 0
    skipped = 0

    records = []
    for record in reporter.records:
        if record["status"] == "passed":
            passed += 1
        elif record["status"] == "failed":
            failed += 1
        elif record["status"] == "skipped":
            skipped += 1

        records.append({
            "suite_path": list(record["suite_path"]),
            "description": record["description"],
            "status": record["status"],
            "duration": round(record["duration"], 6),
            "error": _format_runtime_error(record["error"]) if record["error"] is not None else None,
        })

    suite_errors = [
        {
            "suite": suite_name,
            "error": _format_runtime_error(error),
        }
        for suite_name, error in reporter.suite_errors
    ]

    fatal_error = file_result["fatal_error"]
    if fatal_error is not None:
        failed += 1

    return {
        "file": file_result["file"],
        "duration": round(file_result["duration"], 6),
        "passed": passed,
        "failed": failed + len(suite_errors),
        "skipped": skipped,
        "stopped_early": bool(reporter.stop_requested),
        "fatal_error": _format_runtime_error(fatal_error) if fatal_error is not None else None,
        "suite_errors": suite_errors,
        "tests": records,
    }


def _write_json_report(save_path, payload):
    if not save_path:
        return None
    try:
        with open(save_path, "w", encoding="utf-8") as report_file:
            json.dump(payload, report_file, ensure_ascii=False, indent=2)
    except Exception as exc:
        return f"Failed to save JSON report to '{save_path}': {exc}"
    return None


def run_tests(path, failfast=False, json_output=False, save_path=None):
    test_files = _discover_test_files(path)

    if save_path is None and len(test_files) > 0:
        if os.path.isdir(path):
            dir_name = os.path.basename(os.path.abspath(path))
            save_path = f"{dir_name}-test.json"
        elif os.path.isfile(path) and len(test_files) == 1:
            file_name = os.path.basename(test_files[0])
            if file_name.endswith(TEST_FILE_EXTENSION):
                name_without_ext = file_name[: -len(TEST_FILE_EXTENSION)]
                save_path = f"{name_without_ext}-test.json"
        elif len(test_files) > 1:
            save_path = "test-report.json"

    if not test_files:
        empty_payload = {
            "path": os.path.abspath(path),
            "failfast": bool(failfast),
            "stopped_early": False,
            "summary": {
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "duration": 0.0,
            },
            "files": [],
        }
        if json_output:
            print(json.dumps(empty_payload, ensure_ascii=False, indent=2))
        else:
            print("No .test.omi files found")

        save_error = _write_json_report(save_path, empty_payload)
        if save_error is not None:
            print(save_error)
            return 1
        return 0

    total_start = time.perf_counter()

    total_passed = 0
    total_failed = 0
    total_skipped = 0
    had_fatal = False
    stopped_early = False
    file_reports = []

    for file_path in test_files:
        file_result = _run_test_file(file_path, failfast=failfast)
        if not json_output:
            _print_report(file_result)

        file_json = _build_file_json_result(file_result)
        file_reports.append(file_json)

        reporter = file_result["reporter"]
        total_passed += file_json["passed"]
        total_failed += file_json["failed"]
        total_skipped += file_json["skipped"]

        if file_result["fatal_error"] is not None:
            had_fatal = True

        if failfast and reporter.stop_requested:
            stopped_early = True
            break

    total_duration = time.perf_counter() - total_start

    summary = (
        f"Summary: {total_passed} passed, {total_failed} failed, "
        f"{total_skipped} skipped ({_format_duration(total_duration)} total)"
    )

    payload = {
        "path": os.path.abspath(path),
        "failfast": bool(failfast),
        "stopped_early": bool(stopped_early),
        "summary": {
            "passed": total_passed,
            "failed": total_failed,
            "skipped": total_skipped,
            "duration": round(total_duration, 6),
        },
        "files": file_reports,
    }

    if json_output:
        print(json.dumps(payload, ensure_ascii=False, indent=2))

    save_error = _write_json_report(save_path, payload)
    if save_error is not None:
        print(save_error)
        return 1

    if total_failed > 0 or had_fatal:
        if not json_output:
            print(_color(summary, _Colors.RED))
            if stopped_early:
                print(_color("Stopped early because --failfast is enabled", _Colors.YELLOW))
        return 1

    if not json_output:
        print(_color(summary, _Colors.GREEN))
        if stopped_early:
            print(_color("Stopped early because --failfast is enabled", _Colors.YELLOW))
    return 0
