from src.domain.motion import Motion


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
