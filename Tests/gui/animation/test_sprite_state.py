from kungfu_chess.gui.animation.sprite_state import SpriteState


def make_config(frames_per_sec, is_loop):
    return {"graphics": {"frames_per_sec": frames_per_sec, "is_loop": is_loop}}


class TestCurrentFrameIndex:
    def test_starts_at_frame_zero(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=True), frame_count=5)
        assert state.current_frame_index == 0

    def test_advances_after_one_frame_duration(self):
        # 10 fps -> 100ms per frame
        state = SpriteState(make_config(frames_per_sec=10, is_loop=True), frame_count=5)
        state.advance(100)
        assert state.current_frame_index == 1

    def test_does_not_advance_before_a_full_frame_duration(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=True), frame_count=5)
        state.advance(99)
        assert state.current_frame_index == 0

    def test_loops_back_to_zero_when_is_loop_true(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=True), frame_count=5)
        state.advance(500)  # exactly 5 frames -> wraps to index 0
        assert state.current_frame_index == 0

    def test_clamps_to_last_frame_when_not_looping(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=False), frame_count=5)
        state.advance(1000)  # way past the 500ms full cycle
        assert state.current_frame_index == 4


class TestIsFinished:
    def test_looping_state_never_finishes(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=True), frame_count=5)
        state.advance(10_000)
        assert state.is_finished is False

    def test_non_looping_state_not_finished_partway_through(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=False), frame_count=5)
        state.advance(100)
        assert state.is_finished is False

    def test_non_looping_state_finished_exactly_at_total_duration(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=False), frame_count=5)
        state.advance(500)
        assert state.is_finished is True

    def test_non_looping_state_finished_past_total_duration(self):
        state = SpriteState(make_config(frames_per_sec=10, is_loop=False), frame_count=5)
        state.advance(999)
        assert state.is_finished is True
