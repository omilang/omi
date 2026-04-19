class Context:
    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.symbol_table = None

        if parent is not None and hasattr(parent, "task_queue"):
            self.task_queue = parent.task_queue
            self.event_loop = parent.event_loop
        else:
            self.task_queue = []
            self.event_loop = None

        if parent is not None and hasattr(parent, "async_group_stack"):
            self.async_group_stack = parent.async_group_stack
        else:
            self.async_group_stack = []

        self.defer_scopes = []

        self.in_async_function = False