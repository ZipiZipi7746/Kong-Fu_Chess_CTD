"""JSON typed message envelope (Part 6 of the architecture plan) - every
message, both directions, shares this shape. This module only knows JSON
in, dict out (and back) - it has no knowledge of GameEngine, GameService,
or WebSocket connections, and never imports anything from
kungfu_chess.model/rules/realtime/engine (see the forbidden-imports rule)."""

import json
import time
import uuid

# Master Plan v2, Section 6.2: bumped only when the envelope/payload shape
# changes in a way an old client couldn't safely ignore - cheap to carry
# now, expensive to retrofit once real clients exist outside this repo.
PROTOCOL_VERSION = 1


class MalformedMessageError(Exception):
    """Raised by decode() for anything that isn't a well-formed envelope -
    the gateway catches this and replies with an "error" message rather
    than closing the connection or letting the exception propagate."""


def make_envelope(type_, payload, game_id=None, correlation_id=None, message_id=None):
    return {
        "type": type_,
        "message_id": message_id if message_id is not None else str(uuid.uuid4()),
        "correlation_id": correlation_id,
        "timestamp": int(time.time() * 1000),
        "game_id": game_id,
        "protocol_version": PROTOCOL_VERSION,
        "payload": payload,
    }


def encode(envelope):
    return json.dumps(envelope)


def decode(raw_text):
    try:
        data = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        raise MalformedMessageError("payload is not valid JSON")

    if not isinstance(data, dict):
        raise MalformedMessageError("envelope must be a JSON object")

    if "type" not in data:
        raise MalformedMessageError("envelope missing required 'type' field")

    data.setdefault("payload", {})
    data.setdefault("message_id", None)
    data.setdefault("correlation_id", None)
    data.setdefault("game_id", None)
    data.setdefault("protocol_version", PROTOCOL_VERSION)
    return data
