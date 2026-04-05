from src.error.error import Error
from src.arrow import arrow


class RTError(Error):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, "Runtime Error", details)
        self.context = context

    def as_string(self):
        result = self.generate_traceback()
        result += f"{self.error_name}: {self.details}"

        frame = arrow(self.pos_start.ftxt, self.pos_start, self.pos_end)
        if frame:
            result += f"\n{frame}"

        return result

    def generate_traceback(self):
        lines = ["Traceback (most recent call last):"]
        pos = self.pos_start
        ctx = self.context

        while ctx:
            lines.append(f"  File {pos.fn}, line {pos.ln + 1}, in {ctx.display_name}")
            pos = ctx.parent_entry_pos if ctx.parent_entry_pos else pos
            ctx = ctx.parent

        return "\n".join(lines) + "\n"