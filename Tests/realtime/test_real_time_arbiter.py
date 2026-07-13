from kungfu_chess.realtime.real_time_arbiter import RealTimeArbiter


class TestHasPendingMoveFrom:
    def test_no_pending_moves_returns_false(self):
        arbiter = RealTimeArbiter(1000)
        assert arbiter.has_pending_move_from(0, 0) is False

    def test_matching_pending_move_returns_true(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        assert arbiter.has_pending_move_from(0, 0) is True

    def test_non_matching_pending_move_returns_false(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        assert arbiter.has_pending_move_from(2, 2) is False


class TestIsAirborne:
    def test_not_scheduled_is_not_airborne(self):
        arbiter = RealTimeArbiter(1000)
        assert arbiter.is_airborne(0, 0) is False

    def test_scheduled_and_not_yet_finished_is_airborne(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)
        assert arbiter.is_airborne(0, 0) is True

    def test_still_airborne_exactly_at_finish_clock(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)
        arbiter.clock = 1000
        assert arbiter.is_airborne(0, 0) is True

    def test_not_airborne_after_finish_clock(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)
        arbiter.clock = 1001
        assert arbiter.is_airborne(0, 0) is False


class TestAirborneFinishTime:
    def test_returns_none_when_not_airborne(self):
        arbiter = RealTimeArbiter(1000)
        assert arbiter.airborne_finish_time(0, 0) is None

    def test_returns_finish_time_when_airborne(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)
        assert arbiter.airborne_finish_time(0, 0) == 1000


class TestScheduleMove:
    def test_appends_a_pending_motion(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        assert len(arbiter.pending_motions) == 1
        motion = arbiter.pending_motions[0]
        assert (motion.from_row, motion.from_col) == (0, 0)
        assert (motion.to_row, motion.to_col) == (1, 1)


class TestScheduleJump:
    def test_sets_finish_time_relative_to_clock(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.clock = 500
        arbiter.schedule_jump(3, 4)
        assert arbiter.airborne[(3, 4)] == 1500


class TestAdvance:
    def test_advance_moves_clock_forward(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.advance(250)
        assert arbiter.clock == 250

    def test_arrived_motion_is_returned_and_removed(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 0, 1)
        arrived = arbiter.advance(1000)
        assert len(arrived) == 1
        assert arrived[0].from_row == 0
        assert arbiter.pending_motions == []

    def test_not_yet_arrived_motion_stays_pending(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 0, 1)
        arrived = arbiter.advance(500)
        assert arrived == []
        assert len(arbiter.pending_motions) == 1

    def test_finished_airborne_cell_is_cleared(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)
        arbiter.advance(1001)
        assert (0, 0) not in arbiter.airborne

    def test_airborne_cell_still_at_finish_clock_is_kept(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)
        arbiter.advance(1000)
        assert (0, 0) in arbiter.airborne

    def test_multiple_advances_accumulate_clock(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.advance(300)
        arbiter.advance(400)
        assert arbiter.clock == 700

    def test_arrived_motions_are_ordered_by_arrival_time_not_request_order(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 0, 3)  # requested first, arrives later (3000)
        arbiter.schedule_move(0, 4, 0, 3)  # requested second, arrives sooner (1000)
        arrived = arbiter.advance(3000)
        assert [(m.from_row, m.from_col) for m in arrived] == [(0, 4), (0, 0)]
