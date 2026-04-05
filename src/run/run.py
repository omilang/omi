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
import src.var.flags as flags

global_symbol_table = SymbolTable()
global_symbol_table.set("null", Null())
global_symbol_table.set("true", Boolean.true)
global_symbol_table.set("false", Boolean.false)

BuiltInFunction.print = BuiltInFunction("print")
BuiltInFunction.input = BuiltInFunction("input")
BuiltInFunction.input_int = BuiltInFunction("input_int")
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
BuiltInFunction.is_null = BuiltInFunction("is_null")
BuiltInFunction.typeof = BuiltInFunction("typeof")
BuiltInFunction.to_string = BuiltInFunction("to_string")
BuiltInFunction.to_int = BuiltInFunction("to_int")
BuiltInFunction.to_float = BuiltInFunction("to_float")
BuiltInFunction.to_bool = BuiltInFunction("to_bool")

global_symbol_table.set("print", BuiltInFunction.print)
global_symbol_table.set("input", BuiltInFunction.input)
global_symbol_table.set("input_int", BuiltInFunction.input_int)
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
global_symbol_table.set("eval", BuiltInFunction.eval)

def run(fn, text):
    flags.debug = False
    flags.noecho = False
    flags.eval_enabled = False
    flags.notypes = False

    clean_text = process(text)

    lexer = Lexer(fn, clean_text)
    tokens, error = lexer.make_tokens()
    if error: return None, error, {}

    parser = Parser(tokens)
    ast = parser.parse()
    if ast.error: return None, ast.error, {}

    interpreter = Interpreter()
    context = Context("<program>")
    context.symbol_table = global_symbol_table
    result = interpreter.visit(ast.node, context)

    file_flags = {
        'debug': flags.debug,
        'noecho': flags.noecho,
        'eval': flags.eval_enabled,
    }
    return result.value, result.error, file_flags