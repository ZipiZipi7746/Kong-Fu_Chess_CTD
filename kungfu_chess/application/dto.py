"""Domain <-> application DTO mapping - kept distinct from server/schemas.py
(network <-> application), per the architecture plan's Part 4: two separate
translation layers, not collapsed into one. This module is the only place
that reads BoardRenderer/GameSession/GameEngine to build a JSON-serializable
snapshot; server/websocket_gateway.py just wraps whatever this returns into
a schemas envelope, never touching Board/BoardRenderer itself."""

from kungfu_chess.io.board_view import BoardRenderer


def build_state_snapshot(session):
    engine = session.engine
    return {
        "board": BoardRenderer.to_rows(engine.board),
        "sequence": session.sequence,
        "game_over": engine.game_over,
        "winner": engine.winner,
    }
