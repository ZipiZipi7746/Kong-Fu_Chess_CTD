import json

import pytest

from kungfu_chess.server import schemas


class TestMakeEnvelope:
    def test_includes_the_given_type_and_payload(self):
        envelope = schemas.make_envelope("move_request", {"from_row": 1})
        assert envelope["type"] == "move_request"
        assert envelope["payload"] == {"from_row": 1}

    def test_generates_a_message_id_when_none_given(self):
        envelope = schemas.make_envelope("ping", {})
        assert isinstance(envelope["message_id"], str)
        assert envelope["message_id"] != ""

    def test_uses_the_given_message_id_when_provided(self):
        envelope = schemas.make_envelope("ping", {}, message_id="fixed-id")
        assert envelope["message_id"] == "fixed-id"

    def test_correlation_id_defaults_to_none(self):
        envelope = schemas.make_envelope("ping", {})
        assert envelope["correlation_id"] is None

    def test_game_id_defaults_to_none(self):
        envelope = schemas.make_envelope("ping", {})
        assert envelope["game_id"] is None

    def test_includes_a_numeric_timestamp(self):
        envelope = schemas.make_envelope("ping", {})
        assert isinstance(envelope["timestamp"], int)
        assert envelope["timestamp"] > 0

    def test_carries_through_correlation_id_and_game_id(self):
        envelope = schemas.make_envelope(
            "move_accepted", {}, game_id="g_1", correlation_id="req-1")
        assert envelope["game_id"] == "g_1"
        assert envelope["correlation_id"] == "req-1"

    def test_protocol_version_defaults_to_1(self):
        envelope = schemas.make_envelope("ping", {})
        assert envelope["protocol_version"] == 1


class TestEncodeDecodeRoundTrip:
    def test_encode_produces_valid_json(self):
        envelope = schemas.make_envelope("ping", {}, message_id="m1")
        raw = schemas.encode(envelope)
        assert json.loads(raw)["type"] == "ping"

    def test_decode_recovers_the_encoded_envelope(self):
        envelope = schemas.make_envelope("move_request", {"from_row": 1}, game_id="g_1")
        decoded = schemas.decode(schemas.encode(envelope))
        assert decoded == envelope


class TestDecodeRejectsMalformedInput:
    def test_non_json_text_raises(self):
        with pytest.raises(schemas.MalformedMessageError):
            schemas.decode("not json at all")

    def test_json_that_is_not_an_object_raises(self):
        with pytest.raises(schemas.MalformedMessageError):
            schemas.decode("[1, 2, 3]")

    def test_missing_type_field_raises(self):
        with pytest.raises(schemas.MalformedMessageError):
            schemas.decode(json.dumps({"payload": {}}))

    def test_missing_payload_defaults_to_empty_dict(self):
        decoded = schemas.decode(json.dumps({"type": "ping"}))
        assert decoded["payload"] == {}

    def test_missing_optional_fields_default_to_none(self):
        decoded = schemas.decode(json.dumps({"type": "ping"}))
        assert decoded["message_id"] is None
        assert decoded["correlation_id"] is None
        assert decoded["game_id"] is None

    def test_missing_protocol_version_defaults_to_1(self):
        decoded = schemas.decode(json.dumps({"type": "ping"}))
        assert decoded["protocol_version"] == 1
