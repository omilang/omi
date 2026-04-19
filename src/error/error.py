from src.arrow import arrow
import src.var.ansi as ansi


class Error:
    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def _format_location(self):
        if self.pos_start is None:
            return None

        filename = self.pos_start.fn or "<unknown>"
        line = self.pos_start.ln + 1
        column = self.pos_start.col + 1
        return f"at {filename}:{line}:{column}"

    def _format_frame(self):
        if self.pos_start is None or self.pos_end is None:
            return None

        frame = arrow(self.pos_start.ftxt, self.pos_start, self.pos_end)
        return frame or None

    def as_string(self):
        lines = [ansi.wrap(f"{self.error_name}: {self.details}", "bold", "red")]

        location = self._format_location()
        if location:
            lines.append(ansi.wrap(location, "cyan"))

        frame = self._format_frame()
        if frame:
            lines.append(frame)

        return "\n".join(lines)