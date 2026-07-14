from kungfu_chess.realtime.motion import Motion


class TestInit:
    def test_arrival_time_is_start_plus_fixed_duration(self):
        motion = Motion(0, 0, 1, 1, start_time=500)
        assert motion.arrival_time == 500 + Motion.TIME_PER_CELL_MS

    def test_stores_from_and_to_coordinates(self):
        motion = Motion(2, 3, 4, 5, start_time=0)
        assert (motion.from_row, motion.from_col) == (2, 3)
        assert (motion.to_row, motion.to_col) == (4, 5)


class TestHasArrived:
    def test_before_arrival_time_is_false(self):
        motion = Motion(0, 0, 1, 1, start_time=0)
        assert motion.has_arrived(500) is False

    def test_exactly_at_arrival_time_is_true(self):
        motion = Motion(0, 0, 1, 1, start_time=0)
        assert motion.has_arrived(Motion.TIME_PER_CELL_MS) is True

    def test_after_arrival_time_is_true(self):
        motion = Motion(0, 0, 1, 1, start_time=0)
        assert motion.has_arrived(Motion.TIME_PER_CELL_MS + 100) is True


class TestPreviousCell:
    def test_horizontal_motion(self):
        motion = Motion(0, 0, 0, 3, start_time=0)
        assert motion.previous_cell() == (0, 2)

    def test_vertical_motion(self):
        motion = Motion(0, 0, 3, 0, start_time=0)
        assert motion.previous_cell() == (2, 0)

    def test_diagonal_motion(self):
        motion = Motion(0, 0, 3, 3, start_time=0)
        assert motion.previous_cell() == (2, 2)

    def test_negative_direction(self):
        motion = Motion(3, 3, 0, 0, start_time=0)
        assert motion.previous_cell() == (1, 1)

    def test_single_cell_distance_returns_source(self):
        motion = Motion(2, 2, 2, 3, start_time=0)
        assert motion.previous_cell() == (2, 2)

    def test_knight_shaped_motion_has_no_midpoint_so_returns_source(self):
        motion = Motion(0, 0, 2, 1, start_time=0)
        assert motion.previous_cell() == (0, 0)


class TestProgress:
    def test_zero_at_start_time(self):
        motion = Motion(0, 0, 0, 2, start_time=1000)  # 2000ms duration
        assert motion.progress(1000) == 0.0

    def test_one_at_arrival_time(self):
        motion = Motion(0, 0, 0, 2, start_time=1000)
        assert motion.progress(motion.arrival_time) == 1.0

    def test_half_at_the_midpoint(self):
        motion = Motion(0, 0, 0, 2, start_time=1000)  # arrives at 3000
        assert motion.progress(2000) == 0.5

    def test_clamped_to_one_past_arrival(self):
        motion = Motion(0, 0, 0, 1, start_time=0)
        assert motion.progress(5000) == 1.0

    def test_clamped_to_zero_before_start(self):
        motion = Motion(0, 0, 0, 1, start_time=1000)
        assert motion.progress(0) == 0.0
