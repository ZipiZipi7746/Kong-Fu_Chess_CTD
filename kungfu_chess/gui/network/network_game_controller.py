"""Phase F Milestone 1: the client-side click-to-command state machine
for networked play - the network analogue of input.controller.
GameController, but it never decides legality itself. A click either
selects a friendly piece (a UX-only convenience - not a rules decision;
the pending/airborne/cooldown filtering below only reads booleans the
server already told this client via self.engine, a NetworkEngineView)
or submits a move_request/jump_request for the server to accept or
reject. Holds no board-legality logic and imports nothing from
kungfu_chess.rules/model - the server remains the sole authority
(Master Plan v2 Section 1).

self.engine mirrors input.controller.GameController's own self.engine
attribute on purpose (same name, same read-only surface for game_over/
has_pending_move_from/is_airborne/is_on_cooldown/cooldown_progress/
motion_progress/motion_target) so game_loop.py's existing
_draw_game_over_overlay helper works unchanged against either
controller."""

from kungfu_chess.gui.network.network_engine_view import NetworkEngineView


class NetworkGameController:
    def __init__(self, my_color, on_move_request, on_jump_request, engine=None):
        self.my_color = my_color
        self._on_move_request = on_move_request
        self._on_jump_request = on_jump_request
        self.engine = engine if engine is not None else NetworkEngineView()
        self.selected = None

    def click(self, row, col, board_rows):
        if self.engine.game_over:
            return

        token = board_rows[row][col]

        if self.selected is None:
            if token == "." or token[0] != self.my_color:
                return
            if (self.engine.has_pending_move_from(row, col)
                    or self.engine.is_airborne(row, col)
                    or self.engine.is_on_cooldown(row, col)):
                return
            self.selected = (row, col)
            return

        selected_row, selected_col = self.selected
        selected_token = board_rows[selected_row][selected_col]
        if selected_token == ".":
            # The selected piece is gone (captured while this click was
            # pending) - drop the stale selection instead of moving it.
            self.selected = None
            return

        if token != "." and token[0] == selected_token[0]:
            self.selected = (row, col)
            return

        self._on_move_request(selected_row, selected_col, row, col)
        self.selected = None

    def jump(self, row, col, board_rows):
        token = board_rows[row][col]
        if token == "." or token[0] != self.my_color:
            return
        self._on_jump_request(row, col)
