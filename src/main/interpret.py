from src.main.interpreter.control_flow import InterpreterControlFlowMixin
from src.main.interpreter.core import InterpreterCoreMixin
from src.main.interpreter.functions_async import InterpreterFunctionsAsyncMixin
from src.main.interpreter.modules_directives import InterpreterModulesDirectivesMixin


class Interpreter(
    InterpreterCoreMixin,
    InterpreterControlFlowMixin,
    InterpreterFunctionsAsyncMixin,
    InterpreterModulesDirectivesMixin,
):
    pass