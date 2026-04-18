from src.error.message.rt import RTError
from src.main.symboltable import SymbolTable
from src.nodes.block import BlockNode
from src.run.context import Context
from src.run.runtime import RTResult
from src.values.types.dict import Dict
from src.values.types.list import List
from src.values.types.number import Number
from src.values.types.string import String


class InterpreterControlFlowMixin:
    def visit_IfNode(self, node, context):
        res = RTResult()

        for condition, expr, should_return_null in node.cases:
            condition_value = res.register(self.visit(condition, context))
            if res.should_return():
                return res

            if condition_value.is_true():
                expr_value = res.register(self.visit(expr, context))
                if res.should_return():
                    return res
                return res.success(Number.null if should_return_null else expr_value)

        if node.else_case:
            expr, should_return_null = node.else_case
            else_value = res.register(self.visit(expr, context))
            if res.should_return():
                return res
            return res.success(Number.null if should_return_null else else_value)

        return res.success(Number.null)

    def visit_ForNode(self, node, context):
        res = RTResult()
        elements = []
        if node.start_value_node is None:
            iterable = res.register(self.visit(node.end_value_node, context))
            if res.should_return():
                return res

            from src.values.types.list import List as ListValue

            if not isinstance(iterable, ListValue):
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    "Can only iterate over lists",
                    context,
                ))

            for elem in iterable.elements:
                context.symbol_table.set(node.var_name_tok.value, elem.copy().set_context(context))

                value = res.register(self.visit(node.body_node, context))
                if res.should_return() and res.loop_should_continue is False and res.loop_should_break is False:
                    return res

                if res.loop_should_continue:
                    continue

                if res.loop_should_break:
                    break

                elements.append(value)

            return res.success(
                Number.null if node.should_return_null else List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        start_value = res.register(self.visit(node.start_value_node, context))
        if res.should_return():
            return res

        end_value = res.register(self.visit(node.end_value_node, context))
        if res.should_return():
            return res

        if node.step_value_node:
            step_value = res.register(self.visit(node.step_value_node, context))
            if res.should_return():
                return res
        else:
            step_value = Number(1)

        i = start_value.value

        if step_value.value >= 0:
            condition = lambda: i < end_value.value
        else:
            condition = lambda: i > end_value.value

        while condition():
            context.symbol_table.set(node.var_name_tok.value, Number(i))
            i += step_value.value

            value = res.register(self.visit(node.body_node, context))
            if res.should_return() and res.loop_should_continue is False and res.loop_should_break is False:
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
            Number.null if node.should_return_null else List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_WhileNode(self, node, context):
        res = RTResult()
        elements = []

        while True:
            condition = res.register(self.visit(node.condition_node, context))
            if res.should_return():
                return res

            if not condition.is_true():
                break

            value = res.register(self.visit(node.body_node, context))
            if res.should_return() and res.loop_should_continue is False and res.loop_should_break is False:
                return res

            if res.loop_should_continue:
                continue

            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
            Number.null if node.should_return_null else List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_ReturnNode(self, node, context):
        res = RTResult()
        from src.values.types.void import Void

        if node.node_to_return:
            value = res.register(self.visit(node.node_to_return, context))
            if res.should_return():
                return res
        else:
            value = Void.void

        return res.success_return(value)

    def _runtime_error_value(self, error, context, pos_start, pos_end):
        trace_lines = error.as_dict()["trace"]
        trace_values = [
            String(line).set_context(context).set_pos(pos_start, pos_end)
            for line in trace_lines
        ]
        return Dict({
            "type": String(error.as_dict()["type"]),
            "msg": String(error.as_dict()["msg"]),
            "trace": List(trace_values).set_context(context).set_pos(pos_start, pos_end),
        }).set_context(context).set_pos(pos_start, pos_end)

    def _pattern_matches(self, pattern, value, context):
        from src.nodes.types.typeannotation import TypeAnnotationNode
        from src.run.typecheck import check_type

        if pattern.kind == "wildcard":
            return True, {}, None

        if pattern.kind == "literal":
            if isinstance(value, String):
                return (value.value == pattern.value), {}, None
            from src.values.types.number import Int, Float
            if isinstance(value, (Int, Float)) and isinstance(pattern.value, (int, float)):
                return (value.value == pattern.value), {}, None
            from src.values.types.boolean import Boolean
            if isinstance(value, Boolean) and isinstance(pattern.value, bool):
                return (value.value == pattern.value), {}, None
            from src.values.types.null import Null
            if isinstance(value, Null) and pattern.value is None:
                return True, {}, None
            return False, {}, None

        if pattern.kind == "variant":
            if not isinstance(value, Dict):
                return False, {}, None

            tag = value.entries.get("__tag")
            if not isinstance(tag, String) or tag.value != pattern.name:
                return False, {}, None

            bindings = {}
            if pattern.capture_var_tok is not None:
                if "value" not in value.entries:
                    return False, {}, RTError(
                        pattern.pos_start,
                        pattern.pos_end,
                        f"Variant '{pattern.name}' does not carry a payload to capture",
                        context,
                    )
                bindings[pattern.capture_var_tok.value] = value.entries["value"].copy().set_context(context)
            return True, bindings, None

        if pattern.kind == "identifier":
            if isinstance(value, Dict):
                tag = value.entries.get("__tag")
                if isinstance(tag, String) and tag.value == pattern.name:
                    return True, {}, None

            ann = TypeAnnotationNode([pattern.name], pattern.pos_start, pattern.pos_end)
            err = check_type(value, ann, context, pattern.pos_start, pattern.pos_end)
            if err is None:
                return True, {}, None
            return False, {}, None

        return False, {}, None

    def _match_case_missing_message(self, node, value, context):
        from src.nodes.types.typeannotation import DictTypeAnnotation

        type_name = getattr(value, "type_name", None)
        if type_name:
            enum_ann = context.symbol_table.get(f"__type_{type_name}__")
            if isinstance(enum_ann, DictTypeAnnotation) and getattr(enum_ann, "enum_name", None):
                covered = set()
                for case in node.cases:
                    if case.pattern.kind in ("identifier", "variant"):
                        covered.add(case.pattern.name)
                all_tags = [name for name, _ in enum_ann.enum_variants]
                missing = [tag for tag in all_tags if tag not in covered]
                if missing:
                    return f"Non-exhaustive match for enum '{type_name}'. Missing cases: {', '.join(missing)}"
                return f"Non-exhaustive match for enum '{type_name}'. Add case _ or handle all variants"

        return "Non-exhaustive match. Add case _ to handle unmatched values"

    def _execute_block_last(self, block_node, context):
        res = RTResult()
        last_value = Number.null

        for statement in block_node.element_nodes:
            last_value = res.register(self.visit(statement, context))
            if res.should_return():
                return res

        return res.success(last_value)

    def visit_TryNode(self, node, context):
        res = RTResult()

        try_context = Context("try", parent=context, parent_entry_pos=node.pos_start)
        try_context.symbol_table = SymbolTable(context.symbol_table)

        result_value = Number.null

        try_value = res.register(self.visit(node.try_body, try_context))
        pending_signal = None
        pending_exception = None
        pending_error = None
        pending_return_value = None
        pending_continue = False
        pending_break = False

        if res.signal == "exception" and res.exception_data is not None:
            catch_context = Context("catch", parent=context, parent_entry_pos=node.pos_start)
            catch_context.symbol_table = SymbolTable(context.symbol_table)
            catch_value = self._runtime_error_value(res.exception_data, catch_context, node.pos_start, node.pos_end)
            catch_context.symbol_table.set(node.catch_var_tok.value, catch_value)

            catch_res = self._execute_block_last(node.catch_body, catch_context) if isinstance(node.catch_body, BlockNode) else self.visit(node.catch_body, catch_context)

            if catch_res.signal == "exception" and catch_res.exception_data is not None:
                pending_signal = "exception"
                pending_exception = catch_res.exception_data
            elif catch_res.error:
                pending_error = catch_res.error
            elif catch_res.func_return_value is not None:
                pending_return_value = catch_res.func_return_value
            elif catch_res.loop_should_continue:
                pending_continue = True
            elif catch_res.loop_should_break:
                pending_break = True
            else:
                result_value = catch_res.value if catch_res.value is not None else Number.null
        elif res.error:
            pending_error = res.error
        elif res.func_return_value is not None:
            pending_return_value = res.func_return_value
        elif res.loop_should_continue:
            pending_continue = True
        elif res.loop_should_break:
            pending_break = True
        else:
            result_value = try_value if try_value is not None else Number.null

        if node.final_body is not None:
            final_context = Context("final", parent=context, parent_entry_pos=node.pos_start)
            final_context.symbol_table = SymbolTable(context.symbol_table)
            final_res = self._execute_block_last(node.final_body, final_context) if isinstance(node.final_body, BlockNode) else self.visit(node.final_body, final_context)

            if final_res.signal == "exception" and final_res.exception_data is not None:
                return RTResult().register_exception(final_res.exception_data)
            if final_res.error:
                return RTResult().failure(final_res.error)
            if final_res.func_return_value is not None:
                return RTResult().success_return(final_res.func_return_value)
            if final_res.loop_should_continue:
                return RTResult().success_continue()
            if final_res.loop_should_break:
                return RTResult().success_break()

        if pending_signal == "exception" and pending_exception is not None:
            return RTResult().register_exception(pending_exception)
        if pending_error:
            return RTResult().failure(pending_error)
        if pending_return_value is not None:
            return RTResult().success_return(pending_return_value)
        if pending_continue:
            return RTResult().success_continue()
        if pending_break:
            return RTResult().success_break()

        return RTResult().success(result_value)

    def visit_MatchNode(self, node, context):
        res = RTResult()
        value = res.register(self.visit(node.expr, context))
        if res.should_return():
            return res

        for case in node.cases:
            matched, bindings, error = self._pattern_matches(case.pattern, value, context)
            if error:
                return res.failure(error)
            if not matched:
                continue

            case_context = Context("match", parent=context, parent_entry_pos=node.pos_start)
            case_context.symbol_table = SymbolTable(context.symbol_table)

            for name, bound_value in bindings.items():
                case_context.symbol_table.set(name, bound_value)

            if isinstance(case.body, BlockNode):
                return self._execute_block_last(case.body, case_context)

            case_result = res.register(self.visit(case.body, case_context))
            if res.should_return():
                return res
            return res.success(case_result)

        return res.failure(RTError(
            node.pos_start,
            node.pos_end,
            self._match_case_missing_message(node, value, context),
            context,
        ))

    def visit_ContinueNode(self, node, context):
        return RTResult().success_continue()

    def visit_BreakNode(self, node, context):
        return RTResult().success_break()
