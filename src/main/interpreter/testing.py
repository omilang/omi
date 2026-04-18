import time

from src.error.message.rt import RTError
from src.main.symboltable import SymbolTable
from src.nodes.testing.suite import SuiteNode
from src.nodes.testing.testcase import TestCaseNode
from src.run.async_runtime import run_pending_tasks
from src.run.context import Context
from src.run.runtime import RTResult
from src.values.types.number import Number


class InterpreterTestingMixin:
    def _report_test_event(self, method_name, *args):
        reporter = getattr(self, "test_reporter", None)
        if reporter is None:
            return
        method = getattr(reporter, method_name, None)
        if callable(method):
            method(*args)

    def _result_to_runtime_error(self, result, node, context, label):
        if result.signal == "exception" and result.exception_data is not None:
            return result.exception_data
        if result.error is not None:
            return result.error
        if result.func_return_value is not None:
            return RTError(
                node.pos_start,
                node.pos_end,
                f"{label} cannot use 'return'",
                context,
            )
        if result.loop_should_continue:
            return RTError(
                node.pos_start,
                node.pos_end,
                f"{label} cannot use 'continue'",
                context,
            )
        if result.loop_should_break:
            return RTError(
                node.pos_start,
                node.pos_end,
                f"{label} cannot use 'break'",
                context,
            )
        return None

    def _run_test_case_node(self, node, parent_context):
        start_time = time.perf_counter()

        if node.is_skipped:
            duration = time.perf_counter() - start_time
            return "skipped", None, duration

        case_context = Context(
            f"test:{node.description_tok.value}",
            parent=parent_context,
            parent_entry_pos=node.pos_start,
        )
        case_context.symbol_table = SymbolTable(parent_context.symbol_table)
        case_context.in_async_function = bool(node.is_async)

        body_result = self.visit(node.body_node, case_context)
        runtime_error = self._result_to_runtime_error(
            body_result,
            node,
            case_context,
            "Test case",
        )

        if runtime_error is None:
            runtime_error = run_pending_tasks(case_context)

        duration = time.perf_counter() - start_time
        if runtime_error is not None:
            return "failed", runtime_error, duration

        return "passed", None, duration

    def _execute_hook_list(self, hooks, hook_context):
        for hook_node in hooks:
            hook_result = self.visit(hook_node.body_node, hook_context)
            runtime_error = self._result_to_runtime_error(
                hook_result,
                hook_node,
                hook_context,
                f"Hook '{hook_node.hook_type}'",
            )
            if runtime_error is not None:
                return runtime_error
        return None

    def visit_ExpectNode(self, node, context):
        res = RTResult()

        condition_value = res.register(self.visit(node.expr_node, context))
        if res.should_return():
            return res

        if condition_value.is_true():
            return res.success(Number.null)

        message = "Expectation failed"
        if node.message_node is not None:
            message_value = res.register(self.visit(node.message_node, context))
            if res.should_return():
                return res
            message = str(message_value)

        return res.failure(RTError(
            node.pos_start,
            node.pos_end,
            message,
            context,
            is_test_assertion=True,
        ))

    def visit_TestCaseNode(self, node, context):
        status, runtime_error, duration = self._run_test_case_node(node, context)
        self._report_test_event("record_test", node, status, duration, runtime_error)

        if runtime_error is not None:
            return RTResult().failure(runtime_error)

        return RTResult().success(Number.null)

    def visit_SuiteNode(self, node, context):
        res = RTResult()
        self._report_test_event("begin_suite", node)

        suite_context = Context(
            f"suite:{node.name_tok.value}",
            parent=context,
            parent_entry_pos=node.pos_start,
        )
        suite_context.symbol_table = SymbolTable(context.symbol_table)

        before_error = self._execute_hook_list(node.hooks.get("before", []), suite_context)
        if before_error is not None:
            self._report_test_event("record_suite_error", node, before_error)
            self._report_test_event("end_suite", node)
            return res.success(Number.null)

        for child_node in node.body_nodes:
            if isinstance(child_node, TestCaseNode):
                per_test_context = Context(
                    f"test-scope:{child_node.description_tok.value}",
                    parent=suite_context,
                    parent_entry_pos=child_node.pos_start,
                )
                per_test_context.symbol_table = SymbolTable(suite_context.symbol_table)

                hook_error = None
                if not child_node.is_skipped:
                    hook_error = self._execute_hook_list(node.hooks.get("before_each", []), per_test_context)

                if hook_error is not None:
                    duration = 0.0
                    self._report_test_event("record_test", child_node, "failed", duration, hook_error)
                    continue

                status, runtime_error, duration = self._run_test_case_node(child_node, per_test_context)

                if not child_node.is_skipped:
                    after_each_error = self._execute_hook_list(node.hooks.get("after_each", []), per_test_context)
                    if after_each_error is not None and runtime_error is None:
                        status = "failed"
                        runtime_error = after_each_error

                self._report_test_event("record_test", child_node, status, duration, runtime_error)
                continue

            if isinstance(child_node, SuiteNode):
                nested_result = self.visit(child_node, suite_context)
                if nested_result.error:
                    self._report_test_event("record_suite_error", node, nested_result.error)
                continue

            _ = res.register(self.visit(child_node, suite_context))
            if res.should_return():
                self._report_test_event("record_suite_error", node, res.error or res.exception_data)
                self._report_test_event("end_suite", node)
                return res

        after_error = self._execute_hook_list(node.hooks.get("after", []), suite_context)
        if after_error is not None:
            self._report_test_event("record_suite_error", node, after_error)

        self._report_test_event("end_suite", node)
        return res.success(Number.null)
