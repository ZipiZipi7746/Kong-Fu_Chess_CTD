from src.controller.board_mapper import BoardMapper


class TestToCell:
    def test_origin_maps_to_cell_zero_zero(self):
        mapper = BoardMapper(100)
        assert mapper.to_cell(0, 0) == (0, 0)

    def test_maps_within_cell_bounds(self):
        mapper = BoardMapper(100)
        assert mapper.to_cell(50, 50) == (0, 0)
        assert mapper.to_cell(99, 99) == (0, 0)

    def test_maps_to_next_cell_at_boundary(self):
        mapper = BoardMapper(100)
        assert mapper.to_cell(100, 100) == (1, 1)

    def test_x_and_y_map_independently(self):
        mapper = BoardMapper(100)
        assert mapper.to_cell(300, 500) == (5, 3)

    def test_different_cell_size(self):
        mapper = BoardMapper(50)
        assert mapper.to_cell(120, 220) == (4, 2)
