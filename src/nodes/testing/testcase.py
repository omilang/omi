class TestCaseNode:
    def __init__(self, description_tok, body_node, is_async, is_skipped, pos_start, pos_end):
        self.description_tok = description_tok
        self.body_node = body_node
        self.is_async = is_async
        self.is_skipped = is_skipped
        self.pos_start = pos_start
        self.pos_end = pos_end
