import asyncio

from src.values.value import Value
from src.error.message.rt import RTError


class OmiAsyncTaskError(Exception):
    def __init__(self, rt_error):
        super().__init__(str(getattr(rt_error, "details", rt_error)))
        self.rt_error = rt_error


class _FutureState:
    def __init__(self):
        self.task = None
        self.callback = None
        self.result = None
        self.error = None
        self.done = False
        self.cancelled = False


class FutureValue(Value):
    def __init__(self, result_type_annotation=None):
        super().__init__()
        self.result_type_annotation = result_type_annotation
        self._state = _FutureState()

    def schedule(self, loop, coro):
        self._state.task = loop.create_task(coro)
        return self

    def schedule_deferred(self, callback):
        self._state.callback = callback
        return self

    def schedule_callable(self, loop, callback):
        async def _runner():
            return callback()

        self._state.task = loop.create_task(_runner())
        return self

    def is_done(self):
        if self._state.cancelled:
            return True
        if self._state.task is not None:
            return self._state.task.done()
        return self._state.done

    def cancel(self):
        self._state.cancelled = True
        if self._state.task is not None and not self._state.task.done():
            self._state.task.cancel()
        return self

    def run_deferred(self, context, pos_start, pos_end):
        if self._state.done or self._state.cancelled:
            return
        if self._state.callback is None:
            return
        try:
            self._state.result = self._state.callback()
            self._state.done = True
        except Exception as exc:
            self._state.error = self._to_runtime_error(exc, context, pos_start, pos_end)
            self._state.done = True

    def result(self):
        if self._state.cancelled:
            return None
        if self._state.task is None:
            if not self._state.done or self._state.error is not None:
                return None
            return self._state.result

        if not self.is_done():
            return None
        if self._state.task.cancelled() or self._state.task.exception() is not None:
            return None
        return self._state.task.result()

    def _to_runtime_error(self, exc, context, pos_start, pos_end):
        if isinstance(exc, OmiAsyncTaskError):
            return exc.rt_error
        if isinstance(exc, RTError):
            return exc
        return RTError(
            pos_start,
            pos_end,
            f"Async task failed: {exc}",
            context,
        )

    def get_error(self, context, pos_start=None, pos_end=None):
        if self._state.cancelled:
            return None
        if self._state.task is None:
            return self._state.error

        if self._state.task is None or not self._state.task.done():
            return None
        if self._state.task.cancelled():
            return None
        exc = self._state.task.exception()
        if exc is None:
            return None
        return self._to_runtime_error(exc, context, pos_start, pos_end)

    def await_value(self, loop, context, pos_start, pos_end):
        if self._state.cancelled:
            return None, RTError(pos_start, pos_end, "Async task was cancelled", context)
        if self._state.task is None:
            if not self._state.done:
                self.run_deferred(context, pos_start, pos_end)
            if self._state.error is not None:
                return None, self._state.error
            if not self._state.done:
                return None, RTError(pos_start, pos_end, "Future is not scheduled", context)
            return self._state.result, None

        if not self._state.task.done():
            try:
                if loop.is_running():
                    return None, RTError(
                        pos_start,
                        pos_end,
                        "Cannot block on await while event loop is running",
                        context,
                    )
                loop.run_until_complete(asyncio.shield(self._state.task))
            except asyncio.CancelledError:
                return None, RTError(pos_start, pos_end, "Async task was cancelled", context)
            except Exception as exc:
                return None, self._to_runtime_error(exc, context, pos_start, pos_end)

        err = self.get_error(context, pos_start, pos_end)
        if err is not None:
            return None, err

        return self._state.task.result(), None

    def copy(self):
        copy = FutureValue(self.result_type_annotation)
        copy._state = self._state
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        state = "done" if self.is_done() else "pending"
        return f"<future {state}>"
