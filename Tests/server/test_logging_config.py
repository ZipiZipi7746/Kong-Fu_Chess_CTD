import json
import logging

from kungfu_chess.server.logging_config import NdjsonFormatter, hash_token


def make_record(message, level=logging.INFO, **extra):
    record = logging.LogRecord(
        name="kungfu_chess.server.websocket_gateway", level=level, pathname=__file__,
        lineno=1, msg=message, args=(), exc_info=None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


class TestNdjsonFormatter:
    def test_output_is_valid_json(self):
        formatter = NdjsonFormatter()
        line = formatter.format(make_record("hello"))
        json.loads(line)  # must not raise

    def test_includes_level_logger_and_message(self):
        formatter = NdjsonFormatter()
        payload = json.loads(formatter.format(make_record("hello world")))
        assert payload["level"] == "INFO"
        assert payload["logger"] == "kungfu_chess.server.websocket_gateway"
        assert payload["message"] == "hello world"

    def test_includes_correlation_fields_when_present(self):
        formatter = NdjsonFormatter()
        record = make_record("dispatch", message_id="m-1", game_id="g_1")
        payload = json.loads(formatter.format(record))
        assert payload["message_id"] == "m-1"
        assert payload["game_id"] == "g_1"

    def test_omits_correlation_fields_when_absent(self):
        formatter = NdjsonFormatter()
        payload = json.loads(formatter.format(make_record("no correlation here")))
        assert "message_id" not in payload
        assert "game_id" not in payload
        assert "session_token_hash" not in payload

    def test_each_formatted_record_is_exactly_one_line(self):
        formatter = NdjsonFormatter()
        line = formatter.format(make_record("hello"))
        assert "\n" not in line


class TestHashToken:
    def test_the_same_token_always_hashes_the_same_way(self):
        assert hash_token("abc123") == hash_token("abc123")

    def test_different_tokens_hash_differently(self):
        assert hash_token("abc123") != hash_token("xyz789")

    def test_never_returns_the_plaintext_token(self):
        token = "super-secret-session-token"
        assert hash_token(token) != token
        assert token not in hash_token(token)

    def test_none_hashes_to_none(self):
        assert hash_token(None) is None
