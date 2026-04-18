import os

import src.var.flags as runtime_flags
from src.error.message.rt import RTError
from src.main.symboltable import SymbolTable
from src.preprocessor import process
from src.run.context import Context
from src.run.runtime import RTResult
from src.run.source import read_source_file
from src.values.function.enumvariant import EnumVariantConstructor
from src.values.types.module import Module
from src.values.types.number import Number
from src.var.builtin import BUILTIN_MODULES
from src.var.keyword import FILE_FORMAT


class InterpreterModulesDirectivesMixin:
    def visit_ImportNode(self, node, context):
        res = RTResult()
        module_path = node.module_path_tok.value
        alias = node.alias_tok.value

        if module_path in BUILTIN_MODULES:
            module_value = BUILTIN_MODULES[module_path]()
            module_value.set_context(context).set_pos(node.pos_start, node.pos_end)
            context.symbol_table.set(alias, module_value)

            for key, val in module_value.symbol_table.symbols.items():
                if key.startswith("__type_") and key.endswith("__"):
                    type_name = key[7:-2]
                    context.symbol_table.set(f"__type_{alias}.{type_name}__", val)
                if key.startswith("__trait_") and key.endswith("__"):
                    trait_name = key[8:-2]
                    context.symbol_table.set(f"__trait_{alias}.{trait_name}__", val)

            return res.success(Number.null)

        if module_path.startswith("omi:"):
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Unknown standard library module '{module_path}'",
                context,
            ))

        if module_path.startswith("omi/"):
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Built-in modules use 'omi:...' syntax, not 'omi/...'. Change '{module_path}' to '{module_path.replace('omi/', 'omi:')}'.",
                context,
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
                node.pos_start,
                node.pos_end,
                f"Module '{module_path}' not found",
                context,
            ))

        try:
            script = read_source_file(module_file)
        except Exception as e:
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Failed to load module \"{module_path}\"\n" + str(e),
                context,
            ))

        from src.main.lexer import Lexer
        from src.main.parser.parser import Parser
        from src.nodes.directives.useN import UseDirectiveNode

        clean_script = process(script)

        lexer = Lexer(module_file, clean_script)
        tokens, error = lexer.make_tokens()
        if error:
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Error in module '{module_path}':\n" + error.as_string(),
                context,
            ))

        parser = Parser(tokens)
        ast = parser.parse()
        if ast.error:
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Error in module '{module_path}':\n" + ast.error.as_string(),
                context,
            ))

        stmts = ast.node.element_nodes if hasattr(ast.node, "element_nodes") else []
        has_module_decl = any(
            isinstance(s, UseDirectiveNode) and s.directive.lower() == "module"
            for s in stmts
        )
        if not has_module_decl:
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Cannot import '{module_path}': file does not declare '@use module'",
                context,
            ))

        module_context = Context(f"<module:{module_path}>")
        module_symbol_table = SymbolTable(context.symbol_table)
        module_context.symbol_table = module_symbol_table

        _ = res.register(self.visit(ast.node, module_context))
        if res.should_return():
            return res

        module_value = Module(module_path, module_symbol_table).set_context(context).set_pos(node.pos_start, node.pos_end)
        context.symbol_table.set(alias, module_value)

        for key, val in module_symbol_table.symbols.items():
            if key.startswith("__type_") and key.endswith("__"):
                type_name = key[7:-2]
                context.symbol_table.set(f"__type_{alias}.{type_name}__", val)
            if key.startswith("__trait_") and key.endswith("__"):
                trait_name = key[8:-2]
                context.symbol_table.set(f"__trait_{alias}.{trait_name}__", val)

        return res.success(Number.null)

    def visit_ModuleAccessNode(self, node, context):
        res = RTResult()

        module_value = res.register(self.visit(node.module_node, context))
        if res.should_return():
            return res

        if not hasattr(module_value, "get_member"):
            return res.failure(RTError(
                node.pos_start,
                node.pos_end,
                "Cannot use '.' on this value (not a module or dict)",
                context,
            ))

        attr_name = node.attribute_tok.value
        value, error = module_value.get_member(attr_name)
        if error:
            return res.failure(error)

        value = value.copy().set_pos(node.pos_start, node.pos_end).set_context(context)
        return res.success(value)

    def visit_UseDirectiveNode(self, node, context):
        directive = node.directive.lower()
        if directive not in runtime_flags.VALID_DIRECTIVES:
            return RTResult().failure(RTError(
                node.pos_start,
                node.pos_end,
                f"Unknown directive '@use {directive}'. Valid: {', '.join(sorted(runtime_flags.VALID_DIRECTIVES))}",
                context,
            ))
        if directive == "debug":
            runtime_flags.debug = True
        elif directive == "noecho":
            runtime_flags.noecho = True
        elif directive == "eval":
            runtime_flags.eval_enabled = True
        elif directive == "notypes":
            runtime_flags.notypes = True
        elif directive == "noasync":
            runtime_flags.noasync = True
        return RTResult().success(Number.null)

    def visit_TypeAliasNode(self, node, context):
        alias_name = node.name_tok.value
        context.symbol_table.set(f"__type_{alias_name}__", node.type_annotation)
        return RTResult().success(Number.null)

    def visit_EnumDefNode(self, node, context):
        from src.run.typecheck import build_enum_annotation
        from src.values.types.dict import Dict
        from src.values.types.string import String

        enum_annotation = build_enum_annotation(node)
        context.symbol_table.set(f"__type_{node.name}__", enum_annotation)

        for variant in node.variants:
            if variant.payload_type is None:
                value = Dict({"__tag": String(variant.name)}).set_context(context).set_pos(node.pos_start, node.pos_end)
                value.set_annotation(enum_annotation)
                value.type_name = node.name
                context.symbol_table.set(variant.name, value)
            else:
                constructor = EnumVariantConstructor(node.name, variant.name, variant.payload_type, enum_annotation)
                constructor.set_context(context).set_pos(node.pos_start, node.pos_end)
                context.symbol_table.set(variant.name, constructor)

        return RTResult().success(Number.null)

    def visit_TraitDefNode(self, node, context):
        trait_name = node.name
        context.symbol_table.set(f"__trait_{trait_name}__", node)
        return RTResult().success(Number.null)

    def visit_SetDirectiveNode(self, node, context):
        lhs = node.lhs
        rhs = node.rhs
        type_key = f"__type_{lhs}__"
        resolved_type = context.symbol_table.get(type_key)
        if resolved_type is not None:
            context.symbol_table.set(f"__type_{rhs}__", resolved_type)
            return RTResult().success(Number.null)
        trait_key = f"__trait_{lhs}__"
        resolved_trait = context.symbol_table.get(trait_key)
        if resolved_trait is not None:
            context.symbol_table.set(f"__trait_{rhs}__", resolved_trait)
            return RTResult().success(Number.null)
        val = context.symbol_table.get(lhs)
        if val is not None:
            context.symbol_table.set(rhs, val)
        return RTResult().success(Number.null)
