from kungfu_chess.realtime.progress import progress_fraction


class TestProgressFraction:
    def test_normal_mid_range_value(self):
        assert progress_fraction(0, 1000, 250) == 0.25

    def test_clamped_to_zero_when_now_is_before_start(self):
        assert progress_fraction(1000, 2000, 500) == 0.0

    def test_clamped_to_one_when_now_is_after_finish(self):
        assert progress_fraction(0, 1000, 1500) == 1.0

    def test_one_exactly_at_finish(self):
        assert progress_fraction(0, 1000, 1000) == 1.0

    def test_zero_exactly_at_start(self):
        assert progress_fraction(0, 1000, 0) == 0.0

    def test_zero_duration_is_immediately_complete(self):
        assert progress_fraction(500, 500, 500) == 1.0

    def test_negative_duration_is_treated_as_immediately_complete(self):
        assert progress_fraction(1000, 500, 500) == 1.0
