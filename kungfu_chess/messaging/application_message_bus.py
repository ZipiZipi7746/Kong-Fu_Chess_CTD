import logging

logger = logging.getLogger(__name__)


class ApplicationMessageBus:
    """Server-wide in-memory pub/sub, a sibling to engine/events.EventBus
    (one EventBus per game; one ApplicationMessageBus for the whole
    server). Unlike EventBus, subscribers register for a specific event
    type rather than receiving everything and filtering with isinstance -
    the server has many more event types and consumers than a single
    game's small, fixed subscriber set.

    A handler raising is logged and isolated (Risk Register: "Message Bus
    handler failure") - one broken consumer (e.g. a crashed WebSocket
    write) must never stop other consumers of the same event, or stop
    later publishes entirely.
    """

    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_type, callback):
        self._subscribers.setdefault(event_type, []).append(callback)

    def publish(self, event):
        for callback in self._subscribers.get(type(event), []):
            try:
                callback(event)
            except Exception:
                logger.exception(
                    "ApplicationMessageBus handler %r raised while handling %r",
                    callback, type(event).__name__)
