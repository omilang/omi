import os
import src.values.function.function as Function
from src.values.types.number import Number
from src.values.types.string import String
from src.values.types.list import List
from src.values.types.module import Module
from src.run.runtime import RTResult
from src.run.context import Context
from src.main.symboltable import SymbolTable
from src.error.message.rt import RTError
from src.var.keyword import FILE_FORMAT
from src.stdlib.system import create_system_module
from src.stdlib.files import create_files_module
from src.stdlib.paths import create_paths_module
from src.stdlib.time import create_time_module
from src.stdlib.math import create_math_module
from src.var.token import (
    TT_MUL, TT_DIV,
    TT_PLUS, TT_MINUS,
    TT_POW,
    TT_KEYWORD,
    TT_EE, TT_NE, TT_LT, TT_GT,
                TT_LTE, TT_GTE
)

BUILTIN_MODULES = {
    "system": create_system_module,
    "files": create_files_module,
    "paths": create_paths_module,
    "time": create_time_module,
    "math": create_math_module,
}

class Interpreter:
    def visit(self, node, context):
        method_name = f"visit_{type(node).__name__}"
        method = getattr(self, method_name, self.no_visit_method)
        return method(node, context)
    
    def no_visit_method(self, node, context):
        raise Exception(f"No visit_{type(node).__name__} method defined")
    
    def visit_NumberNode(self, node, context):
        return RTResult().success(
            Number(node.tok.value).set_context(context).set_pos(node.pos_start, node.pos_end)
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
        
        value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(value)

    def visit_VarAssignNode(self, node, context):
        res = RTResult()
        var_name = node.var_name_tok.value
        value = res.register(self.visit(node.value_node, context))
        if res.should_return(): return res

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
            number = Number(1 if number.is_true() else 0).set_context(number.context)

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
        func_value = Function.Function(func_name, body_node, arg_names, node.should_auto_return).set_context(context).set_pos(node.pos_start, node.pos_end)
        
        if node.var_name_tok:
            context.symbol_table.set(func_name, func_value)

        return res.success(func_value)

    def visit_CallNode(self, node, context):
        res = RTResult()
        args = []

        value_to_call = res.register(self.visit(node.node_to_call, context))
        if res.should_return(): return res
        value_to_call = value_to_call.copy().set_pos(node.pos_start, node.pos_end)

        for arg_node in node.arg_nodes:
            args.append(res.register(self.visit(arg_node, context)))
            if res.should_return(): return res

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
            with open(module_file, "r") as f:
                script = f.read()
        except Exception as e:
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                f"Failed to load module \"{module_path}\"\n" + str(e),
                context
            ))

        from src.main.lexer import Lexer
        from src.main.parser.parser import Parser

        lexer = Lexer(module_file, script)
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

        module_context = Context(f"<module:{module_path}>")
        module_symbol_table = SymbolTable(context.symbol_table)
        module_context.symbol_table = module_symbol_table

        module_result = res.register(self.visit(ast.node, module_context))
        if res.should_return(): return res

        module_value = Module(module_path, module_symbol_table).set_context(context).set_pos(node.pos_start, node.pos_end)
        context.symbol_table.set(alias, module_value)

        return res.success(Number.null)

    def visit_ModuleAccessNode(self, node, context):
        res = RTResult()

        module_value = res.register(self.visit(node.module_node, context))
        if res.should_return(): return res

        if not isinstance(module_value, Module):
            return res.failure(RTError(
                node.pos_start, node.pos_end,
                "Cannot access member of non-module value",
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

        if node.node_to_return:
            value = res.register(self.visit(node.node_to_return, context))
            if res.should_return(): return res
        else:
            value = Number.null
        
        return res.success_return(value)

    def visit_ContinueNode(self, node, context):
        return RTResult().success_continue()

    def visit_BreakNode(self, node, context):
        return RTResult().success_break()