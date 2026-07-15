from kungfu_chess.engine.events import EventBus, MoveResolvedEvent


class TestEventBus:
    def test_publish_with_no_subscribers_does_nothing(self):
        bus = EventBus()
        bus.publish("anything")  # must not raise

    def test_subscriber_receives_published_event(self):
        bus = EventBus()
        received = []
        bus.subscribe(received.append)
        event = MoveResolvedEvent(0, 0, 0, 1, moving_piece="wR", captured_piece=None)
        bus.publish(event)
        assert received == [event]

    def test_multiple_subscribers_all_receive_the_event(self):
        bus = EventBus()
        a, b = [], []
        bus.subscribe(a.append)
        bus.subscribe(b.append)
        bus.publish("event")
        assert a == ["event"]
        assert b == ["event"]


class TestMoveResolvedEvent:
    def test_stores_all_fields(self):
        event = MoveResolvedEvent(1, 2, 3, 4, moving_piece="wP", captured_piece="bN")
        assert (event.from_row, event.from_col) == (1, 2)
        assert (event.to_row, event.to_col) == (3, 4)
        assert event.moving_piece == "wP"
        assert event.captured_piece == "bN"

    def test_captured_piece_defaults_to_none(self):
        event = MoveResolvedEvent(0, 0, 0, 1, moving_piece="wR")
        assert event.captured_piece is None
