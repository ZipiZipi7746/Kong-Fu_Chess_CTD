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


def build_render_state(session):
    """Phase F Milestone 1: the periodic broadcast a networked GUI client
    animates from - everything ViewModelRegistry/GameController already
    read locally (has_pending_move_from, is_airborne, cooldown_progress,
    motion_progress, motion_target), serialized the same way
    build_state_snapshot serializes board/game_over/winner. Reads only
    GameEngine's existing public accessor methods - no new engine-layer
    state or behavior."""
    engine = session.engine
    board = engine.board

    motions, cooldowns, airborne = [], [], []
    for row in range(board.rows):
        for col in range(board.cols):
            if engine.has_pending_move_from(row, col):
                to_row, to_col = engine.motion_target(row, col)
                motions.append({
                    "from": [row, col], "to": [to_row, to_col],
                    "progress": engine.motion_progress(row, col),
                })
            if engine.is_airborne(row, col):
                airborne.append({"row": row, "col": col})
            progress = engine.cooldown_progress(row, col)
            if progress is not None:
                cooldowns.append({"row": row, "col": col, "progress": progress})

    return {
        "board": BoardRenderer.to_rows(board),
        "sequence": session.sequence,
        "game_over": engine.game_over,
        "winner": engine.winner,
        "motions": motions,
        "cooldowns": cooldowns,
        "airborne": airborne,
    }
