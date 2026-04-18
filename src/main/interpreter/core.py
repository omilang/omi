import src.var.flags as runtime_flags

from src.error.message.rt import RTError
from src.run.runtime import RTResult
from src.run.typecheck import check_type
from src.values.types.boolean import Boolean
from src.values.types.dict import Dict
from src.values.types.list import List
from src.values.types.number import Number, Int, Float
from src.values.types.string import String
from src.var.token import (
    TT_MUL,
    TT_DIV,
    TT_PLUS,
    TT_MINUS,
    TT_POW,
    TT_KEYWORD,
    TT_EE,
    TT_NE,
    TT_LT,
    TT_GT,
    TT_LTE,
    TT_GTE,
)


class InterpreterCoreMixin:
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
            if res.should_return():
                return res

        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_BlockNode(self, node, context):
        res = RTResult()
        elements = []

        for element_node in node.element_nodes:
            elements.append(res.register(self.visit(element_node, context)))
            if res.should_return():
                return res

        return res.success(
            List(elements).set_context(context).set_pos(node.pos_start, node.pos_end)
        )

    def visit_DictNode(self, node, context):
        res = RTResult()
        entries = {}

        for key_node, value_node in node.pair_nodes:
            key_val = res.register(self.visit(key_node, context))
            if res.should_return():
                return res

            if not isinstance(key_val, String):
                return res.failure(RTError(
                    key_node.pos_start,
                    key_node.pos_end,
                    "Dict keys must be strings",
                    context,
                ))

            value_val = res.register(self.visit(value_node, context))
            if res.should_return():
                return res

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
                node.pos_start,
                node.pos_end,
                f"'{var_name}' is not defined",
                context,
            ))

        from src.values.types.void import Uninitialized

        if isinstance(value, Uninitialized):
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Variable '{var_name}' has no value assigned",
                context,
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
                    node.pos_start,
                    node.pos_end,
                    f"Variable '{var_name}' must have either a type annotation or a value",
                    context,
                ))
            if "void" in node.type_annotation.type_parts:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    "Cannot use 'void' as a variable type",
                    context,
                ))
            uninit = Uninitialized(var_name, node.type_annotation)
            context.symbol_table.set(var_name, uninit)
            return res.success(uninit)

        value = res.register(self.visit(node.value_node, context))
        if res.should_return():
            return res

        if node.is_reassign:
            existing = context.symbol_table.get(var_name)
            if existing is None:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"'{var_name}' is not defined",
                    context,
                ))

            if hasattr(existing, "is_const") and existing.is_const:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Cannot reassign constant '{var_name}'",
                    context,
                ))

            ann = None
            if isinstance(existing, Uninitialized) and existing.annotation is not None:
                ann = existing.annotation
            elif hasattr(existing, "type_annotation") and existing.type_annotation is not None:
                ann = existing.type_annotation

            if ann is not None:
                if "void" in ann.type_parts:
                    return res.failure(RTError(
                        node.pos_start,
                        node.pos_end,
                        "Cannot assign a value to a 'void'-typed variable",
                        context,
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

                from src.values.types.dict import Dict
                from src.nodes.types.typeannotation import DictTypeAnnotation

                if isinstance(value, Dict):
                    if not isinstance(ann, DictTypeAnnotation) and hasattr(ann, "type_parts") and ann.type_parts:
                        type_name = ann.type_parts[0]
                        if "<" in type_name:
                            type_name = type_name[:type_name.index("<")]
                        value.type_name = type_name

                value.set_annotation(ann)
            context.symbol_table.set(var_name, value)
            return res.success(value)

        if not runtime_flags.notypes and node.type_annotation is None:
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Variable '{var_name}' has no type annotation. Use @use notypes to disable.",
                context,
            ))

        if node.type_annotation:
            ann = node.type_annotation
            if "void" in ann.type_parts:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    "Cannot use 'void' as a variable type",
                    context,
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

            from src.values.types.dict import Dict
            from src.nodes.types.typeannotation import DictTypeAnnotation

            if isinstance(value, Dict):
                if not isinstance(ann, DictTypeAnnotation) and hasattr(ann, "type_parts") and ann.type_parts:
                    type_name = ann.type_parts[0]
                    if "<" in type_name:
                        type_name = type_name[:type_name.index("<")]
                    value.type_name = type_name

            value.set_annotation(ann)
        if node.is_const:
            value.is_const = True
        context.symbol_table.set(var_name, value)
        return res.success(value)

    def visit_BinOpNode(self, node, context):
        res = RTResult()
        left = res.register(self.visit(node.left_node, context))
        if res.should_return():
            return res
        right = res.register(self.visit(node.right_node, context))
        if res.should_return():
            return res

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
        elif node.op_tok.matches(TT_KEYWORD, "and"):
            result, error = left.anded_by(right)
        elif node.op_tok.matches(TT_KEYWORD, "or"):
            result, error = left.ored_by(right)

        if error:
            return res.failure(error)
        return res.success(result.set_pos(node.pos_start, node.pos_end))

    def visit_UnaryOpNode(self, node, context):
        res = RTResult()
        number = res.register(self.visit(node.node, context))
        if res.should_return():
            return res

        error = None

        if node.op_tok.type == TT_MINUS:
            number, error = number.multed_by(Number(-1))
        elif node.op_tok.matches(TT_KEYWORD, "isnt"):
            number, error = number.notted()
        elif node.op_tok.matches(TT_KEYWORD, "is"):
            number = Boolean(number.is_true()).set_context(number.context)

        if error:
            return res.failure(error)
        return res.success(number.set_pos(node.pos_start, node.pos_end))

    def visit_FStringNode(self, node, context):
        res = RTResult()
        result = ""
        for kind, value in node.parts:
            if kind == "lit":
                result += value
            else:
                val = res.register(self.visit(value, context))
                if res.should_return():
                    return res
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
        if res.should_return():
            return res
        if cond.is_true():
            val = res.register(self.visit(node.true_node, context))
        else:
            val = res.register(self.visit(node.false_node, context))
        if res.should_return():
            return res
        return res.success(val.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

    def visit_NullCoalNode(self, node, context):
        res = RTResult()
        from src.values.types.null import Null
        from src.values.types.void import Void

        left = res.register(self.visit(node.left, context))
        if res.should_return():
            return res

        if isinstance(left, (Null, Void)):
            right = res.register(self.visit(node.right, context))
            if res.should_return():
                return res
            return res.success(right.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

        return res.success(left.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

    def visit_DictSubscriptNode(self, node, context):
        res = RTResult()

        base = res.register(self.visit(node.base_node, context))
        if res.should_return():
            return res

        index = res.register(self.visit(node.index_node, context))
        if res.should_return():
            return res

        if isinstance(base, Dict):
            if not isinstance(index, String):
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Dict key must be a string, got {type(index).__name__.lower()}",
                    context,
                ))
            value, error = base.get_member(index.value)
            if error:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"Key '{index.value}' not found in dict",
                    context,
                ))
            return res.success(value.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

        if isinstance(base, List):
            from src.values.types.number import Int

            if not isinstance(index, Int):
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"List index must be an integer, got {type(index).__name__.lower()}",
                    context,
                ))
            try:
                value = base.elements[index.value]
            except IndexError:
                return res.failure(RTError(
                    node.pos_start,
                    node.pos_end,
                    f"List index {index.value} out of range (length {len(base.elements)})",
                    context,
                ))
            return res.success(value.copy().set_pos(node.pos_start, node.pos_end).set_context(context))

        return res.failure(RTError(
            node.pos_start,
            node.pos_end,
            "Subscript access '[]' is only supported for dicts and lists",
            context,
        ))
