class SpriteState:
    """A single piece's animation clock for one state (idle/move/jump/
    short_rest/long_rest), driven purely by config.json's frames_per_sec
    and is_loop - no knowledge of the game engine or any other state."""

    def __init__(self, config, frame_count):
        self.frames_per_sec = config["graphics"]["frames_per_sec"]
        self.is_loop = config["graphics"]["is_loop"]
        self.frame_count = frame_count
        self._elapsed_ms = 0

    def advance(self, dt_ms):
        self._elapsed_ms += dt_ms

    @property
    def _frame_duration_ms(self):
        return 1000 / self.frames_per_sec

    @property
    def current_frame_index(self):
        raw_index = int(self._elapsed_ms // self._frame_duration_ms)
        if self.is_loop:
            return raw_index % self.frame_count
        return min(raw_index, self.frame_count - 1)

    @property
    def is_finished(self):
        if self.is_loop:
            return False
        total_duration_ms = self._frame_duration_ms * self.frame_count
        return self._elapsed_ms >= total_duration_ms
