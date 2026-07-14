from kungfu_chess.gui.board_geometry import cell_to_pixel
from kungfu_chess.gui.piece_view_model import PieceViewModel
from kungfu_chess.io.board_view import BoardRenderer


class ViewModelRegistry:
    """Owns PieceViewModels keyed by board cell, across frames.

    Pieces have no stable identity in the model, and Board only updates
    a cell's occupancy on arrival - so a moving piece's view model lives
    at its *source* cell the whole time it's in flight (matching how
    Board itself still reports it there). The instant the motion
    resolves, this relocates that same view model to the destination
    cell instead of creating a fresh one - so its already-in-progress
    move -> long_rest transition carries over rather than restarting at
    idle.
    """

    def __init__(self, sprite_library):
        self.sprite_library = sprite_library
        self._by_cell = {}
        self._pending_targets = {}  # cell -> destination cell, while state == "move"

    def state_name_at(self, row, col):
        view_model = self._by_cell.get((row, col))
        return view_model.state_name if view_model is not None else None

    def _migrate_arrived(self, engine):
        arrived_keys = [
            key for key, view_model in self._by_cell.items()
            if view_model.state_name == "move" and not engine.has_pending_move_from(*key)
        ]
        for key in arrived_keys:
            view_model = self._by_cell.pop(key)
            target = self._pending_targets.pop(key, None)
            if target is not None:
                self._by_cell[target] = view_model

    def render(self, board, renderer, engine, image_w, image_h, dt_ms):
        self._migrate_arrived(engine)

        cell_w = image_w // board.cols
        cell_h = image_h // board.rows

        for row_index, row in enumerate(BoardRenderer.to_rows(board)):
            for col_index, token in enumerate(row):
                if token == ".":
                    continue

                key = (row_index, col_index)
                if key not in self._by_cell:
                    self._by_cell[key] = PieceViewModel(self.sprite_library, token)
                view_model = self._by_cell[key]

                has_pending_move = engine.has_pending_move_from(row_index, col_index)
                is_airborne = engine.is_airborne(row_index, col_index)

                if has_pending_move:
                    self._pending_targets[key] = engine.motion_target(row_index, col_index)

                view_model.update(dt_ms, has_pending_move, is_airborne)

                if has_pending_move:
                    progress = engine.motion_progress(row_index, col_index)
                    to_row, to_col = self._pending_targets[key]
                    from_x, from_y = cell_to_pixel(row_index, col_index, cell_w, cell_h)
                    to_x, to_y = cell_to_pixel(to_row, to_col, cell_w, cell_h)
                    x = from_x + (to_x - from_x) * progress
                    y = from_y + (to_y - from_y) * progress
                else:
                    x, y = cell_to_pixel(row_index, col_index, cell_w, cell_h)

                renderer.draw_sprite(view_model.current_frame_path, int(x), int(y), (cell_w, cell_h))
