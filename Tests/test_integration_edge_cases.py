"""Full-stack integration tests for kfChess edge conditions.

Every test here drives kungfu_chess.main.run() - the same entry point
main() uses - with a text Board + Commands script and asserts on the
captured "print board" output. Nothing is faked or mocked: BoardParser,
Board, BoardMapper, GameController, GameEngine, RealTimeArbiter,
RuleEngine and PromotionRule all run for real, exactly as they would
from a real stdin session. This complements the (extensive) unit-level
coverage in Tests/engine/test_game_engine.py, which exercises the same
mechanics directly through GameEngine's own API rather than through the
pixel-click/jump/wait surface a real player or script actually drives.

Coordinates: BoardMapper's default cell size is 100, and x maps to
column, y to row (see board_mapper.py) - so "click 100 0" means column
1, row 0. Motion travel time is 1000ms per cell of Chebyshev distance
(realtime/motion.py); GameController's defaults are a 1000ms jump
duration, 500ms move cooldown and 1000ms jump cooldown.
"""
from kungfu_chess.main import run


class TestClickSelectionEdgeCases:
    def test_click_on_empty_cell_and_outside_board_are_ignored(self, capsys):
        # Neither no-op should corrupt controller state - a normal
        # select-then-move sequence must still work right afterward.
        run([
            "Board:", "wR .", "Commands:",
            "click 100 0",   # empty cell, no piece to select
            "click 999 999",  # far outside the 1x2 board
            "click 0 0", "click 100 0", "wait 1000", "print board",
        ])
        assert capsys.readouterr().out == ". wR\n"

    def test_switching_selection_before_committing_a_move(self, capsys):
        # Clicking a second same-color piece switches the selection
        # instead of requesting a move - the first piece (the rook)
        # must never move, only the newly-selected knight does.
        run([
            "Board:", "wR wN .", ". . .", ". . .", "Commands:",
            "click 0 0",    # select the rook at (0, 0)
            "click 100 0",  # same color -> switches selection to the knight at (0, 1)
            "click 0 200",  # knight's L-shaped move to (2, 0): distance 2, arrives 2000
            "wait 2000",
            "print board",
        ])
        assert capsys.readouterr().out == "wR . .\n. . .\nwN . .\n"

    def test_invalid_move_keeps_selection_for_a_retry(self, capsys):
        # A diagonal rook move is illegal and must not clear the
        # selection - the very next click can still complete a
        # legal move with the same piece.
        run([
            "Board:", "wR . .", ". . .", "Commands:",
            "click 0 0",     # select (0, 0)
            "click 100 100",  # illegal diagonal to (1, 1) -> invalid, selection kept
            "click 200 0",   # legal straight move to (0, 2), distance 2, arrives 2000
            "wait 2000",
            "print board",
        ])
        assert capsys.readouterr().out == ". . wR\n. . .\n"

    def test_a_move_blocked_by_jumping_the_same_selected_piece_recovers_after_cooldown(self, capsys):
        # Selecting a piece and then jumping it mid-selection makes the
        # completing click's request_move return "blocked" (airborne),
        # not "invalid" - the piece never moves. Once the jump's own
        # airborne window and cooldown both fully elapse, the same
        # piece can be selected and moved normally again.
        run([
            "Board:", "wR . .", "Commands:",
            "click 0 0", "jump 0 0",
            "click 100 0",  # completes the earlier selection while airborne -> blocked
            "wait 1000", "print board",
            # small steps, mirroring a real per-frame loop, so the
            # airborne-end and cooldown-end boundaries land precisely
            "wait 1", "wait 1000", "wait 1",
            "click 0 0", "click 100 0", "wait 1000", "print board",
        ])
        assert capsys.readouterr().out == "wR . .\n. wR .\n"

    def test_second_jump_blocked_by_its_own_cooldown_does_not_go_airborne_again(self, capsys):
        # A jump's cooldown must actually prevent re-triggering flight -
        # proven indirectly (jumping leaves no board-visible trace on
        # its own) by racing an incoming capture against it: if the
        # second jump attempt wrongly succeeded, the piece would still
        # be airborne when the attacker arrives and would survive
        # (killing the attacker instead); since it's genuinely blocked,
        # the attacker captures it normally.
        run([
            "Board:", "wR . bN", "Commands:",
            "jump 200 0",              # bN airborne until clock 1000
            "click 0 0", "click 200 0",  # wR move scheduled, arrives at clock 2000 (distance 2)
            "wait 1001",                # clock 1001: bN's airborne window ends, its cooldown starts
            "jump 200 0",               # blocked: bN is on cooldown
            "wait 999",                 # clock 2000: wR arrives, bN is not airborne -> normal capture
            "print board",
        ])
        assert capsys.readouterr().out == ". . wR\n"


class TestMovementRuleEdgeCases:
    def test_rook_cannot_move_diagonally(self, capsys):
        run(["Board:", "wR .", ". .", "Commands:",
             "click 0 0", "click 100 100", "print board"])
        assert capsys.readouterr().out == "wR .\n. .\n"

    def test_bishop_cannot_move_straight(self, capsys):
        run(["Board:", "wB .", ". .", "Commands:",
             "click 0 0", "click 100 0", "print board"])
        assert capsys.readouterr().out == "wB .\n. .\n"

    def test_queen_is_blocked_by_an_intervening_piece(self, capsys):
        run(["Board:", "wQ wN .", "Commands:",
             "click 0 0", "click 200 0", "print board"])
        assert capsys.readouterr().out == "wQ wN .\n"

    def test_knight_must_move_in_an_l_shape(self, capsys):
        run(["Board:", "wN .", ". .", "Commands:",
             "click 0 0", "click 100 0", "print board"])
        assert capsys.readouterr().out == "wN .\n. .\n"

    def test_king_cannot_move_two_squares(self, capsys):
        run(["Board:", "wK . .", "Commands:",
             "click 0 0", "click 200 0", "print board"])
        assert capsys.readouterr().out == "wK . .\n"

    def test_pawn_double_step_is_illegal_off_the_start_row_but_single_step_still_works(self, capsys):
        # 5 rows -> white's start row is rows - 2 == 3. The pawn here
        # sits one row ahead of that, so its two-step attempt is
        # illegal; a normal one-step forward still succeeds right after.
        run([
            "Board:", ".", ".", "wP", ".", ".", "Commands:",
            "click 0 200",  # select (2, 0)
            "click 0 0",    # illegal two-step to (0, 0): not on the start row
            "click 0 100",  # legal one-step to (1, 0)
            "wait 1000",
            "print board",
        ])
        assert capsys.readouterr().out == ".\nwP\n.\n.\n.\n"

    def test_pawn_double_step_is_blocked_by_an_intervening_piece(self, capsys):
        run([
            "Board:", ".", "wN", "wP", ".", "Commands:",
            "click 0 200", "click 0 0", "print board",
        ])
        assert capsys.readouterr().out == ".\nwN\nwP\n.\n"

    def test_pawn_cannot_capture_straight_ahead(self, capsys):
        run([
            "Board:", "bN", "wP", "Commands:",
            "click 0 100", "click 0 0", "print board",
        ])
        assert capsys.readouterr().out == "bN\nwP\n"

    def test_pawn_cannot_move_diagonally_onto_an_empty_square(self, capsys):
        run([
            "Board:", ". .", "wP .", "Commands:",
            "click 0 100", "click 100 0", "print board",
        ])
        assert capsys.readouterr().out == ". .\nwP .\n"

    def test_pawn_diagonal_capture_succeeds(self, capsys):
        run([
            "Board:", ". .", ". bN", "wP .", "Commands:",
            "click 0 200", "click 100 100", "wait 1000", "print board",
        ])
        assert capsys.readouterr().out == ". .\n. wP\n. .\n"


class TestPromotionEdgeCases:
    def test_white_pawn_promotes_on_reaching_the_back_rank(self, capsys):
        run(["Board:", ".", "wP", "Commands:",
             "click 0 100", "click 0 0", "wait 1000", "print board"])
        assert capsys.readouterr().out == "wQ\n.\n"

    def test_black_pawn_promotes_on_reaching_the_back_rank(self, capsys):
        run(["Board:", "bP", ".", "Commands:",
             "click 0 0", "click 0 100", "wait 1000", "print board"])
        assert capsys.readouterr().out == ".\nbQ\n"

    def test_non_pawn_reaching_the_back_rank_does_not_promote(self, capsys):
        run(["Board:", ".", "wR", "Commands:",
             "click 0 100", "click 0 0", "wait 1000", "print board"])
        assert capsys.readouterr().out == "wR\n.\n"


class TestCaptureRaceAndCollisionEdgeCases:
    def test_friendly_collision_on_a_tie_leaves_the_second_mover_at_its_own_source(self, capsys):
        run([
            "Board:", "wR . wR", "Commands:",
            "click 0 0", "click 100 0",   # requested first, lands normally
            "click 200 0", "click 100 0",  # requested second, ties -> stays put
            "wait 1000", "print board",
        ])
        assert capsys.readouterr().out == ". wR wR\n"

    def test_knight_friendly_collision_stays_at_its_own_source(self, capsys):
        # A blocked knight has no straight-line midpoint to fall back
        # to, so it must stay exactly at its source rather than land on
        # some arbitrary interpolated cell.
        run([
            "Board:", "wN . . .", ". . . .", ". . wR .", "Commands:",
            "click 0 0", "click 100 200",     # knight: distance 2, arrives 2000
            "click 200 200", "click 100 200",  # rook: distance 1, arrives 1000, claims first
            "wait 2000", "print board",
        ])
        assert capsys.readouterr().out == "wN . . .\n. . . .\n. wR . .\n"

    def test_landing_on_a_still_airborne_piece_kills_the_mover_instead_of_capturing(self, capsys):
        run([
            "Board:", "wR bN", "Commands:",
            "jump 100 0",  # bN airborne until clock 1000
            "click 0 0", "click 100 0",  # wR: distance 1, also arrives at clock 1000
            "wait 1000", "print board",
        ])
        assert capsys.readouterr().out == ". bN\n"

    def test_attacker_captures_a_slower_fleeing_defender_and_nothing_teleports_later(self, capsys):
        # Regression coverage (end-to-end) for the capture/stale-motion
        # interaction fixed in RealTimeArbiter.cancel_pending_move_from:
        # bR starts fleeing but wR is faster and captures it first. bR's
        # own flee-motion must not still be "in flight" - if it were,
        # it would later relocate wR (the piece that's now standing on
        # bR's old square) to bR's intended destination, which never
        # happens with the fix in place.
        run([
            "Board:", "wR bR", ". .", ". .", ". .", "Commands:",
            "click 0 0", "click 100 0",    # wR: distance 1, arrives 1000
            "click 100 0", "click 100 300",  # bR's flee attempt: distance 3, would arrive 3000
            "wait 1000", "print board",   # wR captures bR at (0, 1)
            "wait 2000", "print board",   # clock 3000: bR's flee-motion would have arrived
        ])
        assert capsys.readouterr().out == ". wR\n. .\n. .\n. .\n. wR\n. .\n. .\n. .\n"


class TestGameOverEdgeCases:
    def test_king_capture_ends_the_game_and_freezes_all_further_input(self, capsys):
        run([
            "Board:", "wR bK", "Commands:",
            "click 0 0", "click 100 0", "wait 1000",  # wR captures bK, game over
            "click 100 0", "click 0 0", "jump 100 0", "wait 500",  # all ignored post game-over
            "print board",
        ])
        assert capsys.readouterr().out == ". wR\n"
