import os
import src.values.function.function as Function
import src.var.flags as runtime_flags
from src.preprocessor import process
from src.values.types.number import Number, Int, Float
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.dict import Dict
from src.values.types.boolean import Boolean
from src.values.types.module import Module
from src.run.runtime import RTResult
from src.run.context import Context
from src.run.source import read_source_file
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError
from src.var.builtin import BUILTIN_MODULES
from src.var.keyword import FILE_FORMAT
from src.run.typecheck import check_type
from src.var.token import (
    TT_MUL, TT_DIV,
    TT_PLUS, TT_MINUS,
    TT_POW,
    TT_KEYWORD,
    TT_EE, TT_NE, TT_LT, TT_GT,
                TT_LTE, TT_GTE
)

class Interpreter:
    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)
    
    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")
    
    def visit_NumberNode(self, node, context):
        from src.var.token import TT_INT as _TT_INT
        if node.tok.type == _TT_INT:
            val = Int(node.tok.value)
        else:
            val = Float(node.tok.value)
        return RTResult().success(
            val.set_context(context).set_pos(node.pos_start, node.pos_end)
        )
    
    def visit_StringNode(self, node, context):
        return RTResult().success(
            String(node.tok.value).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_ListNode(self, node, context):
        res = RTResult()
        elements = []

        for element_node in node.element_nodes:
            elements.append(res.register(self.visit(element_node, context)))
            if res.should_return(): return res

        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_DictNode(self, node, context):
        res = RTResult()
        entries = {}

        for key_node, value_node in node.pair_nodes:
            key_val = res.register(self.visit(key_node, context))
            if res.should_return(): return res

            if not isinstance(key_val, String):
                return res.failure(RTError(
                    key_node.pos_start, key_node.pos_end,
                    "Dict keys must be strings",
                    context,
                ))

            value_val = res.register(self.visit(value_node, context))
            if res.should_return(): return res

            entries[key_val.value] = value_val

        return res.success(
            Dict(entries).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_VarAccessNode(self, node, context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = context.symbol_table.get(var_name)

        if not value:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"'{var_name}' is not defined",
                context
            ))

        from src.values.types.void import Uninitialized
        if isinstance(value, Uninitialized):
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Variable '{var_name}' has no value assigned",
                context
            ))

        value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(value)

    def visit_VarAssignNode(self, node, context):
        res = RTResult()
        var_name = node.var_name_tok.value
        from src.values.types.void import Uninitialized
        from src.values.types.list import List
        from src.nodes.types.typeannotation import TypeAnnotationNode

        if node.value_node is None:
            if node.type_annotation is None:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"Variable '{var_name}' must have either a type annotation or a value",
                    context
                ))
            if "void" in node.type_annotation.type_parts:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    "Cannot use 'void' as a variable type",
                    context
                ))
            uninit = Uninitialized(var_name, node.type_annotation)
            context.symbol_table.set(var_name, uninit)
            return res.success(uninit)

        value = res.register(self.visit(node.value_node, context))
        if res.should_return(): return res

        if node.is_reassign:
            existing = context.symbol_table.get(var_name)
            if existing is None:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"'{var_name}' is not defined",
                    context
                ))

            if hasattr(existing, 'is_const') and existing.is_const:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"Cannot reassign constant '{var_name}'",
                    context
                ))

            ann = None
            if isinstance(existing, Uninitialized) and existing.annotation is not None:
                ann = existing.annotation
            elif hasattr(existing, 'type_annotation') and existing.type_annotation is not None:
                ann = existing.type_annotation
            
            if ann is not None:
                if "void" in ann.type_parts:
                    return res.failure(RTError(
                        node.pos_start, node.pos_end,
                        "Cannot assign a value to a 'void'-typed variable",
                        context
                    ))
                err = check_type(value, ann, context, node.pos_start, node.pos_end)
                if err:
                    return res.failure(err)
                if isinstance(value, List):
                    if ann.array_elem_types is not None:
                        value.elem_annotation = TypeAnnotationNode(
                            ann.array_elem_types, ann.pos_start, ann.pos_end
                        )
                    if ann.max_size is not None:
                        value.max_size = ann.max_size
                value.set_annotation(ann)
            context.symbol_table.set(var_name, value)
            return res.success(value)

        if not runtime_flags.notypes and node.type_annotation is None:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Variable '{var_name}' has no type annotation. Use @use notypes to disable.",
                context
            ))

        if node.type_annotation:
            ann = node.type_annotation
            if "void" in ann.type_parts:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    "Cannot use 'void' as a variable type",
                    context
                ))
            err = check_type(value, ann, context, node.pos_start, node.pos_end)
            if err:
                return res.failure(err)
            if isinstance(value, List):
                if ann.array_elem_types is not None:
                    value.elem_annotation = TypeAnnotationNode(
                        ann.array_elem_types, ann.pos_start, ann.pos_end
                    )
                if ann.max_size is not None:
                    value.max_size = ann.max_size
            value.set_annotation(ann)

        if node.is_const:
            value.is_const = True
        context.symbol_table.set(var_name, value)
        return res.success(value)

    def visit_BinOpNode(self, node, context):
        res = RTResult()
        left = res.register(self.visit(node.left_node, context))
        if res.should_return(): return res
        right = res.register(self.visit(node.right_node, context))
        if res.should_return(): return res

        if node.op_tok.type == TT_PLUS:
            result, error = left.added_to(right)
        elif node.op_tok.type == TT_MINUS:
            result, error = left.subbed_by(right)
        elif node.op_tok.type == TT_MUL:
            result, error = left.multed_by(right)
        elif node.op_tok.type == TT_DIV:
            result, error = left.dived_by(right)
        elif node.op_tok.type == TT_POW:
            result, error = left.powed_by(right)

        elif node.op_tok.type == TT_EE:
            result, error = left.get_comparison_eq(right)
        elif node.op_tok.type == TT_NE:
            result, error = left.get_comparison_ne(right)
        elif node.op_tok.type == TT_LT:
            result, error = left.get_comparison_lt(right)
        elif node.op_tok.type == TT_GT:
            result, error = left.get_comparison_gt(right)
        elif node.op_tok.type == TT_LTE:
            result, error = left.get_comparison_lte(right)
        elif node.op_tok.type == TT_GTE:
            result, error = left.get_comparison_gte(right)
        elif node.op_tok.matches(TT_KEYWORD, 'and'):
            result, error = left.anded_by(right)
        elif node.op_tok.matches(TT_KEYWORD, 'or'):
            result, error = left.ored_by(right)
        
        if error:
            return res.failure(error)
        else:
            return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_UnaryOpNode(self, node, context):
        res = RTResult()
        number = res.register(self.visit(node.node, context))
        if res.should_return(): return res

        error = None

        if node.op_tok.type == TT_MINUS:
            number, error = number.multed_by(Number(-1))
        elif node.op_tok.matches(TT_KEYWORD, "isnt"):
            number, error = number.notted()
        elif node.op_tok.matches(TT_KEYWORD, "is"):
            number = Boolean(number.is_true()).set_context(number.context)

        if error:
            return res.failure(error)
        else:
            return res.success(number.set_pos(node.pos_start, node.pos_end))
        
    def visit_IfNode(self, node, context):
        res = RTResult()

        for condition, expr, should_return_null in node.cases:
            condition_value = res.register(self.visit(condition, context))
            if res.should_return(): return res

            if condition_value.is_true():
                expr_value = res.register(self.visit(expr, context))
                if res.should_return(): return res
                return res.success(Number.null if should_return_null else expr_value)

        if node.else_case:
            expr, should_return_null = node.else_case
            else_value = res.register(self.visit(expr, context))
            if res.should_return(): return res
            return res.success(Number.null if should_return_null else else_value)

        return res.success(Number.null)
    
    def visit_ForNode(self, node, context):
        res = RTResult()
        elements = []
        if node.start_value_node is None:
            iterable = res.register(self.visit(node.end_value_node, context))
            if res.should_return(): return res

            from src.values.types.list import List as ListValue
            if not isinstance(iterable, ListValue):
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    "Can only iterate over lists",
                    context
                ))

            for elem in iterable.elements:
                context.symbol_table.set(node.var_name_tok.value, elem.copy().set_context(context))

                value = res.register(self.visit(node.body_node, context))
                if res.should_return() and res.loop_should_continue == False and res.loop_should_break == False: return res

                if res.loop_should_continue:
                    continue

                if res.loop_should_break:
                    break

                elements.append(value)

            return res.success(
                Number.null if node.should_return_null else
                List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
            )

        start_value = res.register(self.visit(node.start_value_node, context))
        if res.should_return(): return res

        end_value = res.register(self.visit(node.end_value_node, context))
        if res.should_return(): return res

        if node.step_value_node:
            step_value = res.register(self.visit(node.step_value_node, context))
            if res.should_return(): return res
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
            if res.should_return() and res.loop_should_continue == False and res.loop_should_break == False: return res

            if res.loop_should_continue:
                continue
            
            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
                Number.null if node.should_return_null else
                List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
            )

    def visit_WhileNode(self, node, context):
        res = RTResult()
        elements = []

        while True:
            condition = res.register(self.visit(node.condition_node, context))
            if res.should_return(): return res

            if not condition.is_true(): 
                break

            value = res.register(self.visit(node.body_node, context))
            if res.should_return() and res.loop_should_continue == False and res.loop_should_break == False: return res

            if res.loop_should_continue:
                continue
            
            if res.loop_should_break:
                break

            elements.append(value)

        return res.success(
            Number.null if node.should_return_null else
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )
    
    def visit_FuncDefNode(self, node, context):
        res = RTResult()

        func_name = node.var_name_tok.value if node.var_name_tok else None
        body_node = node.body_node
        arg_names = [arg_name.value for arg_name in node.arg_name_toks]

        if not runtime_flags.notypes:
            label = f"'{func_name}'" if func_name else "anonymous function"
            if node.return_type is None:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"Function {label} is missing a return type annotation. Use @use notypes to disable.",
                    context
                ))
            if node.should_auto_return and node.return_type and "void" in node.return_type.type_parts:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"Arrow function {label} cannot have 'void' return type",
                    context
                ))
            for arg_tok, arg_type in zip(node.arg_name_toks, node.arg_types):
                if arg_type is None:
                    return res.failure(RTError(
                        arg_tok.pos_start, arg_tok.pos_end,
                        f"Argument '{arg_tok.value}' in function {label} is missing a type annotation.",
                        context
                    ))

        arg_defaults = []
        for default_node in node.arg_defaults:
            if default_node is not None:
                default_val = res.register(self.visit(default_node, context))
                if res.should_return(): return res
                arg_defaults.append(default_val)
            else:
                arg_defaults.append(None)

        func_value = Function.Function(
            func_name, body_node, arg_names, node.should_auto_return,
            return_type=node.return_type, arg_types=node.arg_types,
            arg_defaults=arg_defaults
        ).set_context(context).set_pos(node.pos_start, node.pos_end)
        
        if node.var_name_tok:
            context.symbol_table.set(func_name, func_value)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        res = RTResult()
        args = []
        kwargs = {}

        value_to_call = res.register(self.visit(node.node_to_call, context))
        if res.should_return(): return res
        value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)

        for arg_node in node.arg_nodes:
            args.append(res.register(self.visit(arg_node, context)))
            if res.should_return(): return res

        for kw_name, kw_node in node.kwarg_nodes.items():
            kwargs[kw_name] = res.register(self.visit(kw_node, context))
            if res.should_return(): return res

        import src.values.function.function as FuncModule
        if isinstance(value_to_call, FuncModule.Function):
            return_value = res.register(value_to_call.execute(args, kwargs))
        else:
            return_value = res.register(value_to_call.execute(args))
        if res.should_return(): return res
        return_value = return_value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(return_value)
    
    def visit_ImportNode(self, node, context):
        res = RTResult()
        module_path = node.module_path_tok.value
        alias = node.alias_tok.value

        if module_path in BUILTIN_MODULES:
            module_value = BUILTIN_MODULES[module_path]()
            module_value.set_context(context).set_pos(node.pos_start, node.pos_end)
            context.symbol_table.set(alias, module_value)
            return res.success(Number.null)

        if module_path.startswith("omi:"):
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Unknown standard library module '{module_path}'",
                context
            ))

        if module_path.startswith("omi/"):
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Built-in modules use 'omi:...' syntax, not 'omi/...'. Change '{module_path}' to '{module_path.replace('omi/', 'omi:')}'.",
                context
            ))

        current_fn = node.pos_start.fn
        if current_fn and current_fn != "<stdin>":
            base_dir = os.path.dirname(os.path.abspath(current_fn))
        else:
            base_dir = os.getcwd()

        module_file = None
        for ext in FILE_FORMAT:
            candidate = os.path.join(base_dir, module_path + ext)
            if os.path.isfile(candidate):
                module_file = candidate
                break

        if module_file is None:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Module '{module_path}' not found",
                context
            ))

        try:
            script = read_source_file(module_file)
        except Exception as e:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Failed to load module \"{module_path}\"\n" + str(e),
                context
            ))

        from src.main.lexer import Lexer
        from src.main.parser.parser import Parser
        from src.nodes.directives.useN import UseDirectiveNode

        clean_script = process(script)

        lexer = Lexer(module_file, clean_script)
        tokens, error = lexer.make_tokens()
        if error:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Error in module '{module_path}':\n" + error.as_string(),
                context
            ))

        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Error in module '{module_path}':\n" + ast.error.as_string(),
                context
            ))

        stmts = ast.node.element_nodes if hasattr(ast.node, 'element_nodes') else []
        has_module_decl = any(
            isinstance(s, UseDirectiveNode) and s.directive.lower() == 'module'
            for s in stmts
        )
        if not has_module_decl:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Cannot import '{module_path}': file does not declare '@use module'",
                context
            ))

        module_context = Context(f"<module:{module_path}>")
        module_symbol_table = SymbolTable(context.symbol_table)
        module_context.symbol_table = module_symbol_table

        module_result = res.register(self.visit(ast.node, module_context))
        if res.should_return(): return res

        module_value = Module(module_path, module_symbol_table).set_context(context).set_pos(node.pos_start, node.pos_end)
        context.symbol_table.set(alias, module_value)

        for key, val in module_symbol_table.symbols.items():
            if key.startswith("__type_") and key.endswith("__"):
                type_name = key[7:-2]
                context.symbol_table.set(f"__type_{alias}.{type_name}__", val)

        return res.success(Number.null)

    def visit_ModuleAccessNode(self, node, context):
        res = RTResult()

        module_value = res.register(self.visit(node.module_node, context))
        if res.should_return(): return res

        if not hasattr(module_value, 'get_member'):
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                "Cannot use '.' on this value (not a module or dict)",
                context
            ))

        attr_name = node.attribute_tok.value
        value, error = module_value.get_member(attr_name)
        if error:
            return res.failure(error)

        value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(value)

    def visit_ReturnNode(self, node, context):
        res = RTResult()
        from src.values.types.void import Void

        if node.node_to_return:
            value = res.register(self.visit(node.node_to_return, context))
            if res.should_return(): return res
        else:
            value = Void.void

        return res.success_return(value)

    def visit_ContinueNode(self, node, context):
        return RTResult().success_continue()

    def visit_BreakNode(self, node, context):
        return RTResult().success_break()

    def visit_FStringNode(self, node, context):
        res = RTResult()
        result = ""
        for kind, value in node.parts:
            if kind == "lit":
                result += value
            else:
                val = res.register(self.visit(value, context))
                if res.should_return(): return res
                if isinstance(val, String):
                    result += val.value
                else:
                    result += str(val)
        return res.success(
            String(result).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_TernaryOpNode(self, node, context):
        res = RTResult()
        cond = res.register(self.visit(node.cond_node, context))
        if res.should_return(): return res
        if cond.is_true():
            val = res.register(self.visit(node.true_node, context))
        else:
            val = res.register(self.visit(node.false_node, context))
        if res.should_return(): return res
        return res.success(val.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

    def visit_NullCoalNode(self, node, context):
        res = RTResult()
        from src.values.types.null import Null
        from src.values.types.void import Void

        left = res.register(self.visit(node.left, context))
        if res.should_return(): return res

        if isinstance(left, (Null, Void)):
            right = res.register(self.visit(node.right, context))
            if res.should_return(): return res
            return res.success(right.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

        return res.success(left.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

    def visit_DictSubscriptNode(self, node, context):
        res = RTResult()

        base = res.register(self.visit(node.base_node, context))
        if res.should_return(): return res

        index = res.register(self.visit(node.index_node, context))
        if res.should_return(): return res

        if isinstance(base, Dict):
            if not isinstance(index, String):
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"Dict key must be a string, got {type(index).__name__.lower()}",
                    context
                ))
            value, error = base.get_member(index.value)
            if error:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"Key '{index.value}' not found in dict",
                    context
                ))
            return res.success(value.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

        if isinstance(base, List):
            from src.values.types.number import Int
            if not isinstance(index, Int):
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"List index must be an integer, got {type(index).__name__.lower()}",
                    context
                ))
            try:
                value = base.elements[index.value]
            except IndexError:
                return res.failure(RTError(
                    node.pos_start, node.pos_end,
                    f"List index {index.value} out of range (length {len(base.elements)})",
                    context
                ))
            return res.success(value.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

        return res.failure(RTError(
            node.pos_start, node.pos_end,
            f"Subscript access '[]' is only supported for dicts and lists",
            context
        ))

    def visit_UseDirectiveNode(self, node, context):
        directive = node.directive.lower()
        if directive not in runtime_flags.VALID_DIRECTIVES:
            return RTResult().failure(RTError(
                node.pos_start, node.pos_end,
                f"Unknown directive '@use {directive}'. Valid: {', '.join(sorted(runtime_flags.VALID_DIRECTIVES))}",
                context
            ))
        if directive == 'debug':
            runtime_flags.debug = True
        elif directive == 'noecho':
            runtime_flags.noecho = True
        elif directive == 'eval':
            runtime_flags.eval_enabled = True
        elif directive == 'notypes':
            runtime_flags.notypes = True
        return RTResult().success(Number.null)

    def visit_TypeAliasNode(self, node, context):
        alias_name = node.name_tok.value
        context.symbol_table.set(f"__type_{alias_name}__", node.type_annotation)
        return RTResult().success(Number.null)

    def visit_SetDirectiveNode(self, node, context):
        lhs = node.lhs
        rhs = node.rhs
        type_key = f"__type_{lhs}__"
        resolved_type = context.symbol_table.get(type_key)
        if resolved_type is not None:
            context.symbol_table.set(f"__type_{rhs}__", resolved_type)
            return RTResult().success(Number.null)
        val = context.symbol_table.get(lhs)
        if val is not None:
            context.symbol_table.set(rhs, val)
        return RTResult().success(Number.null)