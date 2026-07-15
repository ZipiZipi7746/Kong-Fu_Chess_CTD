from kungfu_chess.input.board_mapper import BoardMapper
from kungfu_chess.io.board_view import BoardRenderer
from kungfu_chess.engine.game_engine import GameEngine


class GameController:
    """Controller: the boundary between raw textual/pixel commands and
    the GameEngine. Interprets pixel clicks into grid cells (via
    BoardMapper, Rule 4), tracks click-to-click piece selection, and
    then delegates the actual "is this move legal / schedule it"
    decision to GameEngine.request_move (Rule 5: decoupling *who
    clicked* from *whether the move is valid*).

    Exposes the same public methods the command layer already relies on
    (click, jump, wait, print_board) so commands.py / main.py do not
    need to change.
    """

    CELL_SIZE = 100
    JUMP_DURATION_MS = 1000

    def __init__(self, board, mapper=None, engine=None):
        """mapper and engine are optional Dependency Injection points
        (tests can supply fakes/stubs here instead of monkeypatching);
        production code omits them and gets the real collaborators."""
        self.board = board
        self.mapper = mapper if mapper is not None else BoardMapper(self.CELL_SIZE)
        self.engine = engine if engine is not None else GameEngine(board, self.JUMP_DURATION_MS)
        self.selected = None

    def click(self, x, y):
        if self.engine.game_over:
            return

        row, col = self.mapper.to_cell(x, y)

        if not self.board.is_inside(row, col):
            return

        token = self.board.get_cell(row, col)

        if self.selected is None:
            if token is None:
                return
            if self.engine.has_pending_move_from(row, col):
                return
            if self.engine.is_airborne(row, col):
                return
            self.selected = (row, col)
            return

        selected_row, selected_col = self.selected
        selected_piece = self.board.get_cell(selected_row, selected_col)

        if selected_piece is None:
            # The selected piece is gone - captured by an unrelated
            # in-flight motion while this click was pending. Drop the
            # stale selection instead of acting on a piece that no
            # longer exists.
            self.selected = None
            return

        if token is not None and token.color == selected_piece.color:
            self.selected = (row, col)
            return

        result = self.engine.request_move(selected_row, selected_col, row, col)
        if result == "invalid":
            # Keep the current selection so the user can try again.
            return

        self.selected = None

    def jump(self, x, y):
        if self.engine.game_over:
            return

        row, col = self.mapper.to_cell(x, y)

        if not self.board.is_inside(row, col):
            return

        self.engine.request_jump(row, col)

    def wait(self, ms):
        self.engine.advance_time(ms)

    def print_board(self):
        BoardRenderer.render(self.board)
