import asyncio

from src.values.value import Value
from src.error.message.rt import RTError


class OmiAsyncTaskError(Exception):
    def __init__(self, rt_error):
        super().__init__(str(getattr(rt_error, "details", rt_error)))
        self.rt_error = rt_error


class FutureValue(Value):
    def __init__(self, result_type_annotation=None):
        super().__init__()
        self.result_type_annotation = result_type_annotation
        self._task = None
        self._callback = None
        self._result = None
        self._error = None
        self._done = False
        self._cancelled = False

    def schedule(self, loop, coro):
        self._task = loop.create_task(coro)
        return self

    def schedule_deferred(self, callback):
        self._callback = callback
        return self

    def schedule_callable(self, loop, callback):
        async def _runner():
            return callback()

        self._task = loop.create_task(_runner())
        return self

    def is_done(self):
        if self._cancelled:
            return True
        if self._task is not None:
            return self._task.done()
        return self._done

    def cancel(self):
        self._cancelled = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
        return self

    def run_deferred(self, context, pos_start, pos_end):
        if self._done or self._cancelled:
            return
        if self._callback is None:
            return
        try:
            self._result = self._callback()
            self._done = True
        except Exception as exc:
            self._error = self._to_runtime_error(exc, context, pos_start, pos_end)
            self._done = True

    def result(self):
        if self._cancelled:
            return None
        if self._task is None:
            if not self._done or self._error is not None:
                return None
            return self._result

        if not self.is_done():
            return None
        if self._task.cancelled() or self._task.exception() is not None:
            return None
        return self._task.result()

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
        if self._cancelled:
            return None
        if self._task is None:
            return self._error

        if self._task is None or not self._task.done():
            return None
        if self._task.cancelled():
            return None
        exc = self._task.exception()
        if exc is None:
            return None
        return self._to_runtime_error(exc, context, pos_start, pos_end)

    def await_value(self, loop, context, pos_start, pos_end):
        if self._cancelled:
            return None, RTError(pos_start, pos_end, "Async task was cancelled", context)
        if self._task is None:
            if not self._done:
                self.run_deferred(context, pos_start, pos_end)
            if self._error is not None:
                return None, self._error
            if not self._done:
                return None, RTError(pos_start, pos_end, "Future is not scheduled", context)
            return self._result, None

        if not self._task.done():
            try:
                if loop.is_running():
                    return None, RTError(
                        pos_start,
                        pos_end,
                        "Cannot block on await while event loop is running",
                        context,
                    )
                loop.run_until_complete(asyncio.shield(self._task))
            except asyncio.CancelledError:
                return None, RTError(pos_start, pos_end, "Async task was cancelled", context)
            except Exception as exc:
                return None, self._to_runtime_error(exc, context, pos_start, pos_end)

        err = self.get_error(context, pos_start, pos_end)
        if err is not None:
            return None, err

        return self._task.result(), None

    def copy(self):
        copy = FutureValue(self.result_type_annotation)
        copy._task = self._task
        copy._callback = self._callback
        copy._result = self._result
        copy._error = self._error
        copy._done = self._done
        copy._cancelled = self._cancelled
        copy.set_context(self.context)
        copy.set_pos(self.pos_start, self.pos_end)
        return copy

    def __repr__(self):
        state = "done" if self.is_done() else "pending"
        return f"<future {state}>"
