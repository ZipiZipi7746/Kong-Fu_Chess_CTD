def legal_destinations(piece, from_row, from_col, board, rule_engine):
    """Every (row, col) the given piece could legally move to right now,
    by asking the existing RuleEngine about every cell on the board -
    RuleEngine itself is untouched, this just orchestrates it for the
    UI's highlighting needs."""
    destinations = []
    for row in range(board.rows):
        for col in range(board.cols):
            if rule_engine.is_legal(piece, from_row, from_col, row, col, board):
                destinations.append((row, col))
    return destinations
