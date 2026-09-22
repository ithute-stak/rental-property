from contextvars import ContextVar

current_request_id: ContextVar[str | None] = ContextVar("mosala_request_id", default=None)
