"""NDJSON structured logging (Master Plan v2 Decision 11) - one logging
setup used by every server module, in place of ad hoc print/inconsistent
logging.getLogger formatting. Every log record is emitted as a single
JSON line; message_id/game_id/session_token_hash are included whenever
a caller supplies them via logging's own `extra={...}` mechanism, giving
end-to-end correlation across log lines for the same request/game -
never the plaintext session token (hash_token one-ways it first).

Local files only in this scope (Decision 11) - no external log shipping.
server/reference_client.py mirrors this exact NDJSON shape/correlation
convention on the client side, since it is the example every future
client implementation follows.
"""

import hashlib
import json
import logging

_CORRELATION_FIELDS = ("message_id", "game_id", "session_token_hash")


class NdjsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _CORRELATION_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def hash_token(token):
    """One-ways a session token for safe inclusion in a log line - never
    log the plaintext token itself. None passes through as None (no
    token to correlate, e.g. an anonymous connection)."""
    if token is None:
        return None
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


def configure_logging(log_path="kungfu_chess_server.log", level=logging.INFO):
    """Composition-root entry point - server_main.py calls this instead
    of logging.basicConfig, so every log record across every server
    module gets the same NDJSON shape, in the log file and on the
    console alike."""
    formatter = NdjsonFormatter()

    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(level)
    root.addHandler(file_handler)
    root.addHandler(console_handler)
