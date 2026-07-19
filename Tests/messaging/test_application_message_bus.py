from kungfu_chess.messaging.application_message_bus import ApplicationMessageBus


class Alpha:
    def __init__(self, value=None):
        self.value = value


class Beta:
    def __init__(self, value=None):
        self.value = value


class TestSubscribeAndPublish:
    def test_subscriber_receives_only_its_own_event_type(self):
        bus = ApplicationMessageBus()
        received = []
        bus.subscribe(Alpha, received.append)

        bus.publish(Alpha("a"))
        bus.publish(Beta("b"))

        assert len(received) == 1
        assert received[0].value == "a"

    def test_publish_with_no_subscribers_does_nothing(self):
        bus = ApplicationMessageBus()
        bus.publish(Alpha())  # must not raise

    def test_multiple_subscribers_to_the_same_type_all_receive_it(self):
        bus = ApplicationMessageBus()
        a, b = [], []
        bus.subscribe(Alpha, a.append)
        bus.subscribe(Alpha, b.append)

        bus.publish(Alpha("x"))

        assert len(a) == 1
        assert len(b) == 1

    def test_subscribing_to_one_type_does_not_receive_a_different_type(self):
        bus = ApplicationMessageBus()
        received = []
        bus.subscribe(Beta, received.append)

        bus.publish(Alpha())

        assert received == []


class TestHandlerFailureIsolation:
    def test_one_handler_raising_does_not_prevent_other_handlers_from_running(self):
        bus = ApplicationMessageBus()
        received = []

        def bad_handler(event):
            raise RuntimeError("boom")

        bus.subscribe(Alpha, bad_handler)
        bus.subscribe(Alpha, received.append)

        bus.publish(Alpha("x"))  # must not raise

        assert len(received) == 1

    def test_one_handler_raising_does_not_prevent_a_later_publish_call(self):
        bus = ApplicationMessageBus()
        received = []

        def bad_handler(event):
            raise RuntimeError("boom")

        bus.subscribe(Alpha, bad_handler)
        bus.publish(Alpha("first"))  # swallowed

        bus.subscribe(Alpha, received.append)
        bus.publish(Alpha("second"))

        assert len(received) == 1
        assert received[0].value == "second"
