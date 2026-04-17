import asyncio


def _root_context(context):
    root = context
    while root.parent is not None:
        root = root.parent
    return root


def ensure_event_loop(context):
    root = _root_context(context)
    loop = getattr(root, "event_loop", None)
    if loop is None or loop.is_closed():
        loop = asyncio.new_event_loop()
        root.event_loop = loop
    return loop


def register_future(context, future):
    root = _root_context(context)
    if not hasattr(root, "task_queue"):
        root.task_queue = []
    root.task_queue.append(future)

    group_stack = getattr(root, "async_group_stack", [])
    if group_stack:
        group_stack[-1].add_future(future)


def run_pending_tasks(context):
    root = _root_context(context)
    queue = getattr(root, "task_queue", [])
    if not queue:
        return None

    loop = ensure_event_loop(root)
    asyncio.set_event_loop(loop)

    idx = 0
    while idx < len(queue):
        future = queue[idx]
        if not future.is_done():
            future.run_deferred(root, future.pos_start, future.pos_end)
        idx += 1

    pending = [future._task for future in queue if getattr(future, "_task", None) is not None and not future.is_done()]
    if pending:
        loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))

    for future in queue:
        err = future.get_error(root, future.pos_start, future.pos_end)
        if err is not None:
            return err

    return None
