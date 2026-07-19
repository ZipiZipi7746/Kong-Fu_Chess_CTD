from kungfu_chess.model.board_topology import RectangularTopology


class TestRectangularTopology:
    def test_contains_inside_bounds(self):
        topology = RectangularTopology(rows=3, cols=3)
        assert topology.contains(0, 0) is True
        assert topology.contains(2, 2) is True

    def test_contains_negative_row_or_col_is_false(self):
        topology = RectangularTopology(rows=3, cols=3)
        assert topology.contains(-1, 0) is False
        assert topology.contains(0, -1) is False

    def test_contains_beyond_bounds_is_false(self):
        topology = RectangularTopology(rows=3, cols=3)
        assert topology.contains(3, 0) is False
        assert topology.contains(0, 3) is False

    def test_zero_sized_topology_contains_nothing(self):
        topology = RectangularTopology(rows=0, cols=0)
        assert topology.contains(0, 0) is False
