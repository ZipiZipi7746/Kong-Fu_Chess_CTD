from src.domain.motion import Motion


class RealTimeArbiter:
    """Owns deterministic, virtual-time bookkeeping (Rule 9) for
    in-flight Motions and airborne (jumping) pieces. Time only ever
    advances via explicit advance(ms) calls - never real clocks or
    blocking sleeps - so simultaneous arrivals resolve deterministically
    and repeatably. Renamed from the original MoveScheduler to match the
    roadmap's "RealTimeArbiter" component (Phase 6).
    """

    def __init__(self, jump_duration_ms):
        self.clock = 0
        self.pending_motions = []
        self.airborne = {}
        self._jump_duration_ms = jump_duration_ms

    def has_pending_move_from(self, row, col):
        for motion in self.pending_motions:
            if motion.from_row == row and motion.from_col == col:
                return True
        return False

    def is_airborne(self, row, col):
        finish = self.airborne.get((row, col))
        return finish is not None and finish >= self.clock

    def airborne_finish_time(self, row, col):
        return self.airborne.get((row, col))

    def schedule_move(self, from_row, from_col, to_row, to_col, color=None):
        self.pending_motions.append(
            Motion(from_row, from_col, to_row, to_col, self.clock, color)
        )

    def has_opposing_color_pending(self, color):
        """True if any currently in-flight motion belongs to a piece of
        the OPPOSITE color. Same-color pieces may still move in
        parallel (the core kung-fu-chess mechanic) - only a piece of
        the opposing color is held back until the in-flight motion
        resolves."""
        for motion in self.pending_motions:
            if motion.color is not None and motion.color != color:
                return True
        return False

    def schedule_jump(self, row, col):
        self.airborne[(row, col)] = self.clock + self._jump_duration_ms

    def advance(self, ms):
        """Moves virtual time forward and returns the Motions that have
        arrived (Rule 9: event-driven, not thread-blocking)."""
        self.clock += ms

        arrived = [
            motion for motion in self.pending_motions
            if motion.has_arrived(self.clock)
        ]
        for motion in arrived:
            self.pending_motions.remove(motion)

        finished = [
            cell for cell, finish_time in self.airborne.items()
            if finish_time < self.clock
        ]
        for cell in finished:
            del self.airborne[cell]

        return arrived
