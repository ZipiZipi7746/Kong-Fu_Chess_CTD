from kungfu_chess.realtime.motion import Motion


class RealTimeArbiter:
    """Owns deterministic, virtual-time bookkeeping (Rule 9) for
    in-flight Motions and airborne (jumping) pieces. Time only ever
    advances via explicit advance(ms) calls - never real clocks or
    blocking sleeps - so simultaneous arrivals resolve deterministically
    and repeatably. Renamed from the original MoveScheduler to match the
    roadmap's "RealTimeArbiter" component (Phase 6).
    """

    DEFAULT_MOVE_COOLDOWN_MS = 500
    DEFAULT_JUMP_COOLDOWN_MS = 1000

    def __init__(self, jump_duration_ms, move_cooldown_ms=None, jump_cooldown_ms=None):
        self.clock = 0
        self.pending_motions = []
        self.airborne = {}
        self.cooldowns = {}
        self._jump_duration_ms = jump_duration_ms
        self._move_cooldown_ms = (
            move_cooldown_ms if move_cooldown_ms is not None else self.DEFAULT_MOVE_COOLDOWN_MS)
        self._jump_cooldown_ms = (
            jump_cooldown_ms if jump_cooldown_ms is not None else self.DEFAULT_JUMP_COOLDOWN_MS)

    def has_pending_move_from(self, row, col):
        for motion in self.pending_motions:
            if motion.from_row == row and motion.from_col == col:
                return True
        return False

    def get_pending_motion(self, row, col):
        for motion in self.pending_motions:
            if motion.from_row == row and motion.from_col == col:
                return motion
        return None

    def is_airborne(self, row, col):
        finish = self.airborne.get((row, col))
        return finish is not None and finish >= self.clock

    def airborne_finish_time(self, row, col):
        return self.airborne.get((row, col))

    def schedule_move(self, from_row, from_col, to_row, to_col):
        self.pending_motions.append(
            Motion(from_row, from_col, to_row, to_col, self.clock)
        )

    def schedule_jump(self, row, col):
        self.airborne[(row, col)] = self.clock + self._jump_duration_ms

    def is_on_cooldown(self, row, col):
        finish = self.cooldowns.get((row, col))
        return finish is not None and finish >= self.clock

    def start_move_cooldown(self, row, col):
        self.cooldowns[(row, col)] = self.clock + self._move_cooldown_ms

    def start_jump_cooldown(self, row, col):
        self.cooldowns[(row, col)] = self.clock + self._jump_cooldown_ms

    def advance(self, ms):
        """Moves virtual time forward and returns the Motions that have
        arrived (Rule 9: event-driven, not thread-blocking)."""
        self.clock += ms

        arrived = [
            motion for motion in self.pending_motions
            if motion.has_arrived(self.clock)
        ]
        arrived.sort(key=lambda motion: motion.arrival_time)
        for motion in arrived:
            self.pending_motions.remove(motion)

        finished_airborne = [
            cell for cell, finish_time in self.airborne.items()
            if finish_time < self.clock
        ]
        for cell in finished_airborne:
            del self.airborne[cell]
            self.start_jump_cooldown(*cell)

        finished_cooldowns = [
            cell for cell, finish_time in self.cooldowns.items()
            if finish_time < self.clock
        ]
        for cell in finished_cooldowns:
            del self.cooldowns[cell]

        return arrived
