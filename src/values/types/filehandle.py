from src.values.value import Value


class _FileHandleState:
    def __init__(self, py_file, path, mode):
        self.py_file = py_file
        self.path = path
        self.mode = mode
        self.closed = False

    def close(self):
        if self.closed:
            return
        try:
            self.py_file.close()
        finally:
            self.closed = True

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass


class FileHandleValue(Value):
    def __init__(self, state):
        super().__init__()
        self._state = state

    @property
    def path(self):
        return self._state.path

    @property
    def mode(self):
        return self._state.mode

    @property
    def closed(self):
        return self._state.closed

    def close(self):
        self._state.close()

    def read(self, count=-1):
        return self._state.py_file.read(count)

    def write(self, data):
        written = self._state.py_file.write(data)
        self._state.py_file.flush()
        return written

    def copy(self):
        copy = FileHandleValue(self._state)
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        state = "closed" if self.closed else "open"
        return f"<file_handle {state} '{self.path}' mode='{self.mode}'>"
