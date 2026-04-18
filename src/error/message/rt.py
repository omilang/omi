from src.error.error import Error
from src.arrow import arrow


class RTError(Error):
    def __init__(self, pos_start, pos_end, details, context, is_test_assertion=False):
        super().__init__(pos_start, pos_end, "Runtime Error", details)
        self.context = context
        self.is_test_assertion = is_test_assertion
        self.name = type(self).__name__
        self.trace = self.generate_traceback()

    def as_string(self):
        lines = list(self.trace)
        lines.append(f"{self.error_name}: {self.details}")

        frame = self._format_frame()
        if frame:
            lines.append(frame)

        return "\n".join(lines)

    def as_dict(self):
        return {
            "type": self.name,
            "msg": self.details,
            "trace": self.trace,
            "is_test_assertion": self.is_test_assertion,
        }

    def generate_traceback(self):
        lines = ["Traceback (most recent call last):"]
        pos = self.pos_start
        ctx = self.context

        while ctx:
            filename = pos.fn or "<unknown>"
            lines.append(f"  at {filename}:{pos.ln + 1}:{pos.col + 1} in {ctx.display_name}")
            pos = ctx.parent_entry_pos if ctx.parent_entry_pos else pos
            ctx = ctx.parent

        return lines