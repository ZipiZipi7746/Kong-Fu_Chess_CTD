from kungfu_chess.gui.animation.sprite_state import SpriteState

_GAME_DRIVEN_STATES = ("move", "jump")


class PieceViewModel:
    """Tracks one piece's animation state (idle/move/jump/short_rest/
    long_rest) across frames. Queries the engine only through booleans
    the caller already has (has_pending_move, is_airborne) - it never
    talks to GameEngine directly, keeping it trivially testable with a
    fake SpriteLibrary and no real engine at all.

    Transition rule:
      1. If the engine reports an active move or jump, that state wins
         immediately, resetting its animation clock.
      2. Otherwise, if we just came from a game-driven state (move/jump)
         ending, hand off to that state's own next_state_when_finished.
      3. Otherwise, if the current (resting) state's own animation has
         finished, hand off to its next_state_when_finished.
    """

    def __init__(self, sprite_library, piece_code):
        self.sprite_library = sprite_library
        self.piece_code = piece_code
        self._switch_to("idle")

    def _switch_to(self, state_name):
        self.state_name = state_name
        self._frames, self.config = self.sprite_library.load(self.piece_code, state_name)
        self.sprite_state = SpriteState(self.config, len(self._frames))

    def update(self, dt_ms, has_pending_move, is_airborne):
        # Advance first, so a state that finishes exactly within this
        # frame's dt hands off immediately rather than lingering one
        # extra frame.
        self.sprite_state.advance(dt_ms)

        game_state = "move" if has_pending_move else ("jump" if is_airborne else None)

        if game_state is not None:
            if self.state_name != game_state:
                self._switch_to(game_state)
        elif self.state_name in _GAME_DRIVEN_STATES:
            self._switch_to(self.config["physics"]["next_state_when_finished"])
        elif self.sprite_state.is_finished:
            self._switch_to(self.config["physics"]["next_state_when_finished"])

    @property
    def current_frame_path(self):
        return self._frames[self.sprite_state.current_frame_index]
