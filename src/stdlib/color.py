import sys

from src.error.message.rt import RTError
from src.main.symboltable import SymbolTable
from src.run.runtime import RTResult
from src.values.function.stdlib import StdlibFunction
from src.values.types.boolean import Boolean
from src.values.types.module import Module
from src.values.types.number import Number
from src.values.types.string import String
import src.var.ansi as ansi


class ColorBuiltInFunction(StdlibFunction):
    def __init__(self, name):
        super().__init__(name)
        self.is_async = True

    def copy(self):
        copy = ColorBuiltInFunction(self.name)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        return f"<built-in function color.{self.name}>"

    def _expect_string(self, value, exec_ctx, where):
        if not isinstance(value, String):
            return None, RTError(
                self.pos_start,
                self.pos_end,
                f"{where}: argument must be a string",
                exec_ctx,
            )
        return value.value, None

    def _expect_number(self, value, exec_ctx, where):
        if not isinstance(value, Number):
            return None, RTError(
                self.pos_start,
                self.pos_end,
                f"{where}: value must be a number",
                exec_ctx,
            )
        return int(value.value), None

    def _single_style(self, exec_ctx, style_name):
        text_val = exec_ctx.symbol_table.get("text")
        text, err = self._expect_string(text_val, exec_ctx, f"color.{self.name}()")
        if err:
            return RTResult().failure(err)
        return RTResult().success(String(ansi.wrap(text, style_name)))

    def execute_red(self, exec_ctx):
        return self._single_style(exec_ctx, "red")
    execute_red.arg_names = ["text"]

    def execute_green(self, exec_ctx):
        return self._single_style(exec_ctx, "green")
    execute_green.arg_names = ["text"]

    def execute_yellow(self, exec_ctx):
        return self._single_style(exec_ctx, "yellow")
    execute_yellow.arg_names = ["text"]

    def execute_blue(self, exec_ctx):
        return self._single_style(exec_ctx, "blue")
    execute_blue.arg_names = ["text"]

    def execute_magenta(self, exec_ctx):
        return self._single_style(exec_ctx, "magenta")
    execute_magenta.arg_names = ["text"]

    def execute_cyan(self, exec_ctx):
        return self._single_style(exec_ctx, "cyan")
    execute_cyan.arg_names = ["text"]

    def execute_white(self, exec_ctx):
        return self._single_style(exec_ctx, "white")
    execute_white.arg_names = ["text"]

    def execute_black(self, exec_ctx):
        return self._single_style(exec_ctx, "black")
    execute_black.arg_names = ["text"]

    def execute_bg_red(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_red")
    execute_bg_red.arg_names = ["text"]

    def execute_bg_green(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_green")
    execute_bg_green.arg_names = ["text"]

    def execute_bg_yellow(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_yellow")
    execute_bg_yellow.arg_names = ["text"]

    def execute_bg_blue(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_blue")
    execute_bg_blue.arg_names = ["text"]

    def execute_bg_magenta(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_magenta")
    execute_bg_magenta.arg_names = ["text"]

    def execute_bg_cyan(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_cyan")
    execute_bg_cyan.arg_names = ["text"]

    def execute_bg_white(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_white")
    execute_bg_white.arg_names = ["text"]

    def execute_bg_black(self, exec_ctx):
        return self._single_style(exec_ctx, "bg_black")
    execute_bg_black.arg_names = ["text"]

    def execute_bold(self, exec_ctx):
        return self._single_style(exec_ctx, "bold")
    execute_bold.arg_names = ["text"]

    def execute_dim(self, exec_ctx):
        return self._single_style(exec_ctx, "dim")
    execute_dim.arg_names = ["text"]

    def execute_italic(self, exec_ctx):
        return self._single_style(exec_ctx, "italic")
    execute_italic.arg_names = ["text"]

    def execute_underline(self, exec_ctx):
        return self._single_style(exec_ctx, "underline")
    execute_underline.arg_names = ["text"]

    def execute_blink(self, exec_ctx):
        return self._single_style(exec_ctx, "blink")
    execute_blink.arg_names = ["text"]

    def execute_reverse(self, exec_ctx):
        return self._single_style(exec_ctx, "reverse")
    execute_reverse.arg_names = ["text"]

    def execute_hidden(self, exec_ctx):
        return self._single_style(exec_ctx, "hidden")
    execute_hidden.arg_names = ["text"]

    def execute_strikethrough(self, exec_ctx):
        return self._single_style(exec_ctx, "strikethrough")
    execute_strikethrough.arg_names = ["text"]

    def execute_reset(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        text, err = self._expect_string(text_val, exec_ctx, "color.reset()")
        if err:
            return RTResult().failure(err)
        return RTResult().success(String(ansi.reset_after(text)))
    execute_reset.arg_names = ["text"]

    def execute_clear(self, exec_ctx):
        seq = ansi.clear_seq()
        if seq:
            print(seq, end="")
            sys.stdout.flush()
        return RTResult().success(Number.null)
    execute_clear.arg_names = []

    def execute_enable(self, exec_ctx):
        ansi.enable()
        return RTResult().success(Number.null)
    execute_enable.arg_names = []

    def execute_disable(self, exec_ctx):
        ansi.disable()
        return RTResult().success(Number.null)
    execute_disable.arg_names = []

    def execute_rgb(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        r_val = exec_ctx.symbol_table.get("r")
        g_val = exec_ctx.symbol_table.get("g")
        b_val = exec_ctx.symbol_table.get("b")

        text, err = self._expect_string(text_val, exec_ctx, "color.rgb()")
        if err:
            return RTResult().failure(err)

        r, err = self._expect_number(r_val, exec_ctx, "color.rgb()")
        if err:
            return RTResult().failure(err)
        g, err = self._expect_number(g_val, exec_ctx, "color.rgb()")
        if err:
            return RTResult().failure(err)
        b, err = self._expect_number(b_val, exec_ctx, "color.rgb()")
        if err:
            return RTResult().failure(err)

        return RTResult().success(String(ansi.wrap_codes(text, ansi.rgb_code(r, g, b))))
    execute_rgb.arg_names = ["text", "r", "g", "b"]

    def execute_bg_rgb(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        r_val = exec_ctx.symbol_table.get("r")
        g_val = exec_ctx.symbol_table.get("g")
        b_val = exec_ctx.symbol_table.get("b")

        text, err = self._expect_string(text_val, exec_ctx, "color.bg_rgb()")
        if err:
            return RTResult().failure(err)

        r, err = self._expect_number(r_val, exec_ctx, "color.bg_rgb()")
        if err:
            return RTResult().failure(err)
        g, err = self._expect_number(g_val, exec_ctx, "color.bg_rgb()")
        if err:
            return RTResult().failure(err)
        b, err = self._expect_number(b_val, exec_ctx, "color.bg_rgb()")
        if err:
            return RTResult().failure(err)

        return RTResult().success(String(ansi.wrap_codes(text, ansi.bg_rgb_code(r, g, b))))
    execute_bg_rgb.arg_names = ["text", "r", "g", "b"]

    def execute_success(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        text, err = self._expect_string(text_val, exec_ctx, "color.success()")
        if err:
            return RTResult().failure(err)
        return RTResult().success(String(ansi.wrap(text, "bold", "green")))
    execute_success.arg_names = ["text"]

    def execute_error(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        text, err = self._expect_string(text_val, exec_ctx, "color.error()")
        if err:
            return RTResult().failure(err)
        return RTResult().success(String(ansi.wrap(text, "bold", "red")))
    execute_error.arg_names = ["text"]

    def execute_warning(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        text, err = self._expect_string(text_val, exec_ctx, "color.warning()")
        if err:
            return RTResult().failure(err)
        return RTResult().success(String(ansi.wrap(text, "yellow")))
    execute_warning.arg_names = ["text"]

    def execute_info(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        text, err = self._expect_string(text_val, exec_ctx, "color.info()")
        if err:
            return RTResult().failure(err)
        return RTResult().success(String(ansi.wrap(text, "blue")))
    execute_info.arg_names = ["text"]

    def execute_question(self, exec_ctx):
        text_val = exec_ctx.symbol_table.get("text")
        text, err = self._expect_string(text_val, exec_ctx, "color.question()")
        if err:
            return RTResult().failure(err)
        return RTResult().success(String(ansi.wrap(text, "cyan")))
    execute_question.arg_names = ["text"]


def _const(style_name):
    return String(ansi.code(style_name))


def create_color_module():
    symbol_table = SymbolTable()

    function_names = (
        "red", "green", "yellow", "blue", "magenta", "cyan", "white", "black",
        "bg_red", "bg_green", "bg_yellow", "bg_blue", "bg_magenta", "bg_cyan", "bg_white", "bg_black",
        "bold", "dim", "italic", "underline", "blink", "reverse", "hidden", "strikethrough",
        "reset", "clear", "enable", "disable", "rgb", "bg_rgb",
        "success", "error", "warning", "info", "question",
    )

    for name in function_names:
        symbol_table.set(name, ColorBuiltInFunction(name))

    for key in ansi.ANSI_CODES:
        symbol_table.set(key.upper(), _const(key))

    symbol_table.set("supported", Boolean.true if ansi.supported() else Boolean.false)

    return Module("color", symbol_table)
