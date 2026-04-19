from src.main.lexer import Lexer
from src.main.parser.parser import Parser
from src.main.interpret import Interpreter
from src.main.symboltable import SymbolTable
from src.run.context import Context
from src.values.types.number import Number
from src.values.types.boolean import Boolean
from src.values.types.null import Null
from src.values.function.buildin import BuiltInFunction
from src.preprocessor import process
from src.run.async_runtime import ensure_event_loop, run_pending_tasks
from src.linter import LintRunner
from src.linter.context import LintOptions
import src.var.flags as flags
import asyncio


class LintAbortError:
    def __init__(self, message):
        self.message = message

    def as_string(self):
        return self.message

global_symbol_table = SymbolTable()
global_symbol_table.set("null", Null())
global_symbol_table.set("true", Boolean.true)
global_symbol_table.set("false", Boolean.false)

BuiltInFunction.print = BuiltInFunction("print")
BuiltInFunction.println = BuiltInFunction("println")
BuiltInFunction.output = BuiltInFunction("output")
BuiltInFunction.reprint = BuiltInFunction("reprint")
BuiltInFunction.input = BuiltInFunction("input")
BuiltInFunction.clear = BuiltInFunction("clear")
BuiltInFunction.is_number = BuiltInFunction("is_number")
BuiltInFunction.is_int = BuiltInFunction("is_int")
BuiltInFunction.is_float = BuiltInFunction("is_float")
BuiltInFunction.is_bool = BuiltInFunction("is_bool")
BuiltInFunction.is_string = BuiltInFunction("is_string")
BuiltInFunction.is_list = BuiltInFunction("is_list")
BuiltInFunction.is_array = BuiltInFunction("is_array")
BuiltInFunction.is_dict = BuiltInFunction("is_dict")
BuiltInFunction.is_function = BuiltInFunction("is_function")
BuiltInFunction.append = BuiltInFunction("append")
BuiltInFunction.pop = BuiltInFunction("pop")
BuiltInFunction.extend = BuiltInFunction("extend")
BuiltInFunction.len = BuiltInFunction("len")
BuiltInFunction.eval = BuiltInFunction("eval")
BuiltInFunction.cancel = BuiltInFunction("cancel")
BuiltInFunction.is_null = BuiltInFunction("is_null")
BuiltInFunction.typeof = BuiltInFunction("typeof")
BuiltInFunction.to_string = BuiltInFunction("to_string")
BuiltInFunction.to_int = BuiltInFunction("to_int")
BuiltInFunction.to_float = BuiltInFunction("to_float")
BuiltInFunction.to_bool = BuiltInFunction("to_bool")
BuiltInFunction.range = BuiltInFunction("range")

global_symbol_table.set("print", BuiltInFunction.print)
global_symbol_table.set("println", BuiltInFunction.println)
global_symbol_table.set("output", BuiltInFunction.output)
global_symbol_table.set("reprint", BuiltInFunction.reprint)
global_symbol_table.set("input", BuiltInFunction.input)
global_symbol_table.set("clear", BuiltInFunction.clear)
global_symbol_table.set("cls", BuiltInFunction.clear)
global_symbol_table.set("is_num", BuiltInFunction.is_number)
global_symbol_table.set("is_int", BuiltInFunction.is_int)
global_symbol_table.set("is_float", BuiltInFunction.is_float)
global_symbol_table.set("is_bool", BuiltInFunction.is_bool)
global_symbol_table.set("is_str", BuiltInFunction.is_string)
global_symbol_table.set("is_list", BuiltInFunction.is_list)
global_symbol_table.set("is_array", BuiltInFunction.is_array)
global_symbol_table.set("is_dict", BuiltInFunction.is_dict)
global_symbol_table.set("is_func", BuiltInFunction.is_function)
global_symbol_table.set("is_null", BuiltInFunction.is_null)
global_symbol_table.set("typeof", BuiltInFunction.typeof)
global_symbol_table.set("to_string", BuiltInFunction.to_string)
global_symbol_table.set("to_int", BuiltInFunction.to_int)
global_symbol_table.set("to_float", BuiltInFunction.to_float)
global_symbol_table.set("to_bool", BuiltInFunction.to_bool)
global_symbol_table.set("append", BuiltInFunction.append)
global_symbol_table.set("pop", BuiltInFunction.pop)
global_symbol_table.set("extend", BuiltInFunction.extend)
global_symbol_table.set("len", BuiltInFunction.len)
global_symbol_table.set("range", BuiltInFunction.range)
global_symbol_table.set("eval", BuiltInFunction.eval)
global_symbol_table.set("cancel", BuiltInFunction.cancel)

def run(fn, text, preserve_flags=False, lint_options=None):
    if not preserve_flags:
        keep_no_colors = flags.no_colors
        flags.debug = False
        flags.noecho = False
        flags.eval_enabled = False
        flags.notypes = False
        flags.noasync = False
        flags.no_colors = keep_no_colors
        flags.use_json = False
        flags.use_fix = False
        flags.use_failfast = False
        flags.use_level = None
        flags.use_rules = None
        flags.use_config = None
        flags.use_save = None
        flags.repl_output_emitted = False
        flags.repl_output_ended_with_newline = True

    script_text = text

    if lint_options is not None:
        try:
            runner = LintRunner(
                config_path=lint_options.config_path,
                level=lint_options.level,
                rules=lint_options.rules,
                fix=lint_options.fix,
                json_output=lint_options.json_output,
                failfast=lint_options.failfast,
            )
            lint_result = runner.lint_source(fn, script_text)
        except ValueError as e:
            return None, LintAbortError(str(e)), {}

        if lint_options.json_output:
            print(lint_result.report.to_json())
        else:
            print(lint_result.report.to_text())

        fixed_source = lint_result.fixed_sources.get(fn)
        if fixed_source is not None:
            script_text = fixed_source
            if fn != "<stdin>":
                with open(fn, "w", encoding="utf-8", newline="") as handle:
                    handle.write(script_text)

        if lint_options.failfast and lint_result.report.summary.get("errors", 0) > 0:
            return None, LintAbortError("Lint failed: execution stopped"), {}

    clean_text = process(script_text)

    lexer = Lexer(fn, clean_text)
    tokens, error = lexer.make_tokens()
    if error: return None, error, {}

    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error: return None, ast.error, {}

    interpreter = Interpreter()
    context = Context("<program>")
    context.symbol_table = global_symbol_table
    loop = ensure_event_loop(context)
    result = interpreter.visit(ast.node, context)

    pending_err = None
    if result.error is None and result.signal != "exception":
        pending_err = run_pending_tasks(context)

    if loop is not None and not loop.is_closed():
        pending = [task for task in asyncio.all_tasks(loop) if not task.done()]
        if pending:
            for task in pending:
                task.cancel()
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.close()

    if result.signal == "exception" and result.exception_data is not None:
        return None, result.exception_data, {}
    if pending_err is not None:
        return None, pending_err, {}

    file_flags = {
        'debug': flags.debug,
        'noecho': flags.noecho,
        'eval': flags.eval_enabled,
        'noasync': flags.noasync,
    }
    return result.value, result.error, file_flags