import asyncio

import src.values.function.function as Function
import src.var.flags as runtime_flags
from src.error.message.rt import RTError
from src.run.async_runtime import ensure_event_loop, register_future
from src.run.runtime import RTResult
from src.values.async_group import AsyncGroupValue
from src.values.future import FutureValue, OmiAsyncTaskError
from src.values.types.list import List
from src.values.types.number import Number


class InterpreterFunctionsAsyncMixin:
    def visit_FuncDefNode(self, node, context):
        res = RTResult()

        func_name = node.var_name_tok.value if node.var_name_tok else None
        body_node = node.body_node
        arg_names = [arg_name.value for arg_name in node.arg_name_toks]

        if not runtime_flags.notypes:
            label = f"'{func_name}'" if func_name else "anonymous function"
            if node.return_type is None:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Function {label} is missing a return type annotation. Use @use notypes to disable.",
                    context,
                ))
            if node.should_auto_return and node.return_type and "void" in node.return_type.type_parts:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Arrow function {label} cannot have 'void' return type",
                    context,
                ))
            for arg_tok, arg_type in zip(node.arg_name_toks, node.arg_types):
                if arg_type is None:
                    return res.failure(RTError(
                        arg_tok.pos_start,
                        arg_tok.pos_end,
                        f"Argument '{arg_tok.value}' in function {label} is missing a type annotation.",
                        context,
                    ))

        arg_defaults = []
        for default_node in node.arg_defaults:
            if default_node is not None:
                default_val = res.register(self.visit(default_node, context))
                if res.should_return():
                    return res
                arg_defaults.append(default_val)
            else:
                arg_defaults.append(None)

        func_value = Function.Function(
            func_name,
            body_node,
            arg_names,
            node.should_auto_return,
            return_type=node.return_type,
            arg_types=node.arg_types,
            arg_defaults=arg_defaults,
            type_params=getattr(node, "type_params", []),
            is_async=node.is_async,
        ).set_context(context).set_pos(node.pos_start, node.pos_end)

        if node.var_name_tok:
            context.symbol_table.set(func_name, func_value)
            if len(node.arg_types) > 0 and node.arg_types[0] is not None:
                first_arg_type = node.arg_types[0]
                type_parts = first_arg_type.type_parts if hasattr(first_arg_type, "type_parts") else []
                if type_parts:
                    base_type_str = type_parts[0]
                    if "<" in base_type_str:
                        base_type_str = base_type_str[:base_type_str.index("<")]
                    method_key = f"__method_{base_type_str}_{func_name}__"
                    context.symbol_table.set(method_key, func_value)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        res = RTResult()
        args = []
        kwargs = {}

        value_to_call = res.register(self.visit(node.node_to_call, context))
        if res.should_return():
            return res
        value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)

        for arg_node in node.arg_nodes:
            args.append(res.register(self.visit(arg_node, context)))
            if res.should_return():
                return res

        for kw_name, kw_node in node.kwarg_nodes.items():
            kwargs[kw_name] = res.register(self.visit(kw_node, context))
            if res.should_return():
                return res

        import src.values.function.function as FuncModule
        from src.values.function.stdlib import StdlibFunction as StdlibFunctionType

        is_user_function = isinstance(value_to_call, FuncModule.Function)
        is_stdlib_function = isinstance(value_to_call, StdlibFunctionType)
        is_async_callable = getattr(value_to_call, "is_async", False)

        def _execute_sync_call():
            if is_user_function:
                return res.register(value_to_call.execute(args, kwargs))
            if is_stdlib_function:
                return res.register(value_to_call.execute(args, kwargs))
            return res.register(value_to_call.execute(args))

        if node.is_async and runtime_flags.noasync:
            print(
                f"Warning: async execution is disabled by '@use noasync'. Calling '{getattr(value_to_call, 'name', 'value')}' synchronously."
            )
            return_value = _execute_sync_call()
            if res.should_return():
                return res
            return_value = return_value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
            return res.success(return_value)

        if node.is_async and not is_async_callable:
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Function '{getattr(value_to_call, 'name', 'value')}' is synchronous and cannot be called with async",
                context,
            ))

        if not node.is_async and is_async_callable:
            if is_user_function and runtime_flags.noasync:
                print(
                    f"Warning: async function '{getattr(value_to_call, 'name', 'value')}' is executed synchronously because '@use noasync' is enabled."
                )
                return_value = _execute_sync_call()
                if res.should_return():
                    return res
                return_value = return_value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
                return res.success(return_value)

            if is_user_function:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Async function '{getattr(value_to_call, 'name', 'value')}' must be called with async",
                    context,
                ))

            return_value = _execute_sync_call()
            if res.should_return():
                return res
            return_value = return_value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
            return res.success(return_value)

        if node.is_async:
            if is_user_function:
                resolved_return_type = value_to_call.resolve_return_type(args, kwargs) if hasattr(value_to_call, "resolve_return_type") else value_to_call.return_type
                future = FutureValue(result_type_annotation=resolved_return_type)
                future.set_context(context).set_pos(node.pos_start, node.pos_end)

                def _invoke_function():
                    call_result = value_to_call.execute(args, kwargs)
                    if call_result.error:
                        raise OmiAsyncTaskError(call_result.error)
                    return call_result.value

                future.schedule_deferred(_invoke_function)
            else:
                loop = ensure_event_loop(context)
                future = FutureValue()
                future.set_context(context).set_pos(node.pos_start, node.pos_end)

                async def _invoke_value():
                    def _sync_call():
                        if is_stdlib_function:
                            call_result = value_to_call.execute(args, kwargs)
                        else:
                            call_result = value_to_call.execute(args)
                        if call_result.error:
                            raise OmiAsyncTaskError(call_result.error)
                        return call_result.value

                    return await asyncio.to_thread(_sync_call)

                future.schedule(loop, _invoke_value())

            register_future(context, future)
            return res.success(future)

        if is_user_function or is_stdlib_function:
            return_value = res.register(value_to_call.execute(args, kwargs))
        else:
            return_value = res.register(value_to_call.execute(args))
        if res.should_return():
            return res
        return_value = return_value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(return_value)

    def visit_AwaitNode(self, node, context):
        res = RTResult()

        if runtime_flags.noasync:
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                "'async <expr>' is disabled because '@use noasync' is enabled",
                context,
            ))

        if not getattr(context, "in_async_function", False):
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                "'async <expr>' (await form) is only allowed inside async functions",
                context,
            ))

        awaited = res.register(self.visit(node.expr_node, context))
        if res.should_return():
            return res

        if not isinstance(awaited, FutureValue):
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                "'async <expr>' expects a future value",
                context,
            ))

        loop = ensure_event_loop(context)
        value, err = awaited.await_value(loop, context, node.pos_start, node.pos_end)
        if err:
            return res.failure(err)
        return res.success(value)

    def visit_AsyncGroupNode(self, node, context):
        res = RTResult()

        if runtime_flags.noasync:
            print(
                f"Warning: async group '{node.name}' is disabled by '@use noasync'. Group body runs synchronously without async scheduling."
            )
            disabled_group = AsyncGroupValue()
            disabled_group.cancel()
            disabled_group.set_context(context).set_pos(node.pos_start, node.pos_end)
            context.symbol_table.set(node.name, disabled_group)

            body_result = self.visit(node.body_node, context)
            if body_result.error:
                return body_result
            return res.success(disabled_group)

        timeout = None
        for param_name in node.params:
            if param_name != "timeout":
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Unknown async group parameter '{param_name}'",
                    context,
                ))

        if "timeout" in node.params:
            timeout_value = res.register(self.visit(node.params["timeout"], context))
            if res.should_return():
                return res
            if not isinstance(timeout_value, Number):
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    "Async group timeout must be a number",
                    context,
                ))
            timeout = timeout_value.value

        group = AsyncGroupValue(timeout)
        group.set_context(context).set_pos(node.pos_start, node.pos_end)
        context.symbol_table.set(node.name, group)

        from src.run.context import Context

        group_context = Context("async group", context, node.pos_start)
        group_context.symbol_table = context.symbol_table
        group_context.in_async_function = True

        context.async_group_stack.append(group)

        if timeout is not None:
            loop = ensure_event_loop(context)
            timeout_future = FutureValue()
            timeout_future.set_context(context).set_pos(node.pos_start, node.pos_end)

            async def _timeout_group():
                await asyncio.sleep(timeout)
                group.cancel()
                return Number.null

            timeout_future.schedule(loop, _timeout_group())
            group.set_timeout_future(timeout_future)
            register_future(context, timeout_future)

        try:
            body_result = self.visit(node.body_node, group_context)
            if body_result.error:
                group.cancel()
                return body_result
        finally:
            if context.async_group_stack and context.async_group_stack[-1] is group:
                context.async_group_stack.pop()

        return res.success(group)
