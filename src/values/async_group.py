from src.values.value import Value


class AsyncGroupValue(Value):
    def __init__(self, timeout=None):
        super().__init__()
        self.timeout = timeout
        self.members = []
        self._timeout_future = None
        self._cancelled = False

    def add_future(self, future):
        self.members.append(future)
        if self._cancelled:
            future.cancel()
        return self

    def set_timeout_future(self, future):
        self._timeout_future = future
        return self

    def cancel(self):
        self._cancelled = True
        if self._timeout_future is not None:
            self._timeout_future.cancel()
        for future in self.members:
            future.cancel()
        return self

    def is_done(self):
        return all(future.is_done() for future in self.members)

    def copy(self):
        copy = AsyncGroupValue(self.timeout)
        copy.members = self.members
        copy._timeout_future = self._timeout_future
        copy._cancelled = self._cancelled
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        state = "cancelled" if self._cancelled else ("done" if self.is_done() else "pending")
        return f"<async group {state}>"
