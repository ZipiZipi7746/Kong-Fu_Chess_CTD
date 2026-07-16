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


class TestGetPendingMotion:
    def test_no_pending_motion_returns_none(self):
        arbiter = RealTimeArbiter(1000)
        assert arbiter.get_pending_motion(0, 0) is None

    def test_returns_the_matching_motion(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        motion = arbiter.get_pending_motion(0, 0)
        assert (motion.from_row, motion.from_col) == (0, 0)
        assert (motion.to_row, motion.to_col) == (1, 1)

    def test_non_matching_cell_returns_none(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        assert arbiter.get_pending_motion(2, 2) is None


class TestCancelPendingMoveFrom:
    def test_removes_the_matching_motion(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        arbiter.cancel_pending_move_from(0, 0)
        assert arbiter.get_pending_motion(0, 0) is None
        assert arbiter.pending_motions == []

    def test_leaves_non_matching_motions_alone(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        arbiter.schedule_move(2, 2, 3, 3)
        arbiter.cancel_pending_move_from(0, 0)
        assert arbiter.get_pending_motion(0, 0) is None
        assert arbiter.get_pending_motion(2, 2) is not None

    def test_no_matching_motion_is_a_noop(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_move(0, 0, 1, 1)
        arbiter.cancel_pending_move_from(5, 5)
        assert arbiter.get_pending_motion(0, 0) is not None


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

    def test_finished_cooldown_cell_is_cleared(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        arbiter.advance(RealTimeArbiter.DEFAULT_MOVE_COOLDOWN_MS + 1)
        assert arbiter.is_on_cooldown(0, 0) is False

    def test_cooldown_cell_still_within_window_is_kept(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        arbiter.advance(RealTimeArbiter.DEFAULT_MOVE_COOLDOWN_MS)
        assert arbiter.is_on_cooldown(0, 0) is True


class TestCooldownDefaults:
    def test_default_move_cooldown_is_500ms(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        assert arbiter.cooldowns[(0, 0)] == 500

    def test_default_jump_cooldown_is_1000ms(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_jump_cooldown(0, 0)
        assert arbiter.cooldowns[(0, 0)] == 1000

    def test_durations_are_configurable(self):
        arbiter = RealTimeArbiter(1000, move_cooldown_ms=200, jump_cooldown_ms=300)
        arbiter.start_move_cooldown(0, 0)
        arbiter.start_jump_cooldown(1, 1)
        assert arbiter.cooldowns[(0, 0)] == 200
        assert arbiter.cooldowns[(1, 1)] == 300


class TestIsOnCooldown:
    def test_not_started_is_not_on_cooldown(self):
        arbiter = RealTimeArbiter(1000)
        assert arbiter.is_on_cooldown(0, 0) is False

    def test_started_and_not_yet_finished_is_on_cooldown(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        assert arbiter.is_on_cooldown(0, 0) is True

    def test_relative_to_current_clock(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.clock = 500
        arbiter.start_move_cooldown(0, 0)
        assert arbiter.cooldowns[(0, 0)] == 1000  # 500 + default 500ms
        assert arbiter.is_on_cooldown(0, 0) is True

    def test_exactly_at_finish_clock_is_still_on_cooldown(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        arbiter.clock = 500  # == default move cooldown
        assert arbiter.is_on_cooldown(0, 0) is True

    def test_past_finish_clock_is_not_on_cooldown(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        arbiter.clock = 501
        assert arbiter.is_on_cooldown(0, 0) is False


class TestJumpEndingStartsItsOwnCooldown:
    def test_cooldown_begins_when_airborne_window_finishes(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)  # airborne until clock 1000
        arbiter.advance(1001)  # airborne window just ended
        assert arbiter.is_on_cooldown(0, 0) is True

    def test_cooldown_not_started_while_still_airborne(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.schedule_jump(0, 0)
        arbiter.advance(500)  # still airborne
        assert arbiter.is_on_cooldown(0, 0) is False


class TestCooldownProgress:
    def test_none_when_not_on_cooldown(self):
        arbiter = RealTimeArbiter(1000)
        assert arbiter.cooldown_progress(0, 0) is None

    def test_zero_at_the_instant_it_starts(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        assert arbiter.cooldown_progress(0, 0) == 0.0

    def test_half_way_through_the_default_move_cooldown(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        arbiter.clock = 250  # half of the default 500ms
        assert arbiter.cooldown_progress(0, 0) == 0.5

    def test_one_at_the_instant_it_finishes(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        arbiter.clock = 500
        assert arbiter.cooldown_progress(0, 0) == 1.0

    def test_none_once_past_the_finish_clock(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.start_move_cooldown(0, 0)
        arbiter.clock = 501
        assert arbiter.cooldown_progress(0, 0) is None

    def test_relative_to_the_clock_when_it_started(self):
        arbiter = RealTimeArbiter(1000)
        arbiter.clock = 500
        arbiter.start_move_cooldown(0, 0)
        arbiter.clock = 750  # half of the default 500ms past the start
        assert arbiter.cooldown_progress(0, 0) == 0.5

    def test_zero_duration_cooldown_is_immediately_complete(self):
        arbiter = RealTimeArbiter(1000, move_cooldown_ms=0)
        arbiter.start_move_cooldown(0, 0)
        assert arbiter.cooldown_progress(0, 0) == 1.0
