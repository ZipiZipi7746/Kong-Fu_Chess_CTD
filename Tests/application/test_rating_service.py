import pytest

from kungfu_chess.application import rating_service


class TestExpectedScore:
    def test_equal_ratings_gives_fifty_fifty_odds(self):
        assert rating_service.expected_score(1200, 1200) == pytest.approx(0.5)

    def test_a_higher_rated_player_has_greater_than_fifty_percent_odds(self):
        assert rating_service.expected_score(1400, 1200) > 0.5

    def test_a_lower_rated_player_has_less_than_fifty_percent_odds(self):
        assert rating_service.expected_score(1200, 1400) < 0.5

    def test_the_two_expected_scores_for_a_pairing_always_sum_to_one(self):
        a = rating_service.expected_score(1350, 1180)
        b = rating_service.expected_score(1180, 1350)
        assert a + b == pytest.approx(1.0)

    def test_a_400_point_gap_gives_the_standard_ten_to_one_odds_ratio(self):
        # The defining property of the logistic Elo formula: a 400-point
        # rating gap corresponds to a 10:1 expected-score ratio.
        higher = rating_service.expected_score(1600, 1200)
        assert higher == pytest.approx(10 / 11, abs=1e-6)


class TestUpdateRating:
    def test_a_win_against_an_equally_rated_opponent_gains_exactly_half_the_k_factor(self):
        new_rating = rating_service.update_rating(1200, expected=0.5, actual=1.0, k=32)
        assert new_rating == 1200 + 16

    def test_a_loss_against_an_equally_rated_opponent_loses_exactly_half_the_k_factor(self):
        new_rating = rating_service.update_rating(1200, expected=0.5, actual=0.0, k=32)
        assert new_rating == 1200 - 16

    def test_beating_a_much_stronger_opponent_gains_close_to_the_full_k_factor(self):
        # update_rating always rounds to the nearest int (see below) -
        # 1200 + 32*0.95 == 1230.4, rounds to 1230.
        new_rating = rating_service.update_rating(1200, expected=0.05, actual=1.0, k=32)
        assert new_rating == round(1200 + 32 * 0.95)

    def test_result_is_always_an_integer(self):
        new_rating = rating_service.update_rating(1200, expected=0.637, actual=1.0, k=32)
        assert isinstance(new_rating, int)


class TestApplyGameResult:
    def test_the_winner_gains_rating_and_the_loser_loses_the_same_amount(self):
        # Zero-sum by construction: expected_score(a, b) + expected_score(b, a) == 1,
        # so a symmetric K-factor means one side's gain equals the other's loss.
        new_white, new_black = rating_service.apply_game_result(
            white_rating=1200, black_rating=1200, winner="w", k=32)
        assert new_white == 1200 + 16
        assert new_black == 1200 - 16

    def test_apply_game_result_is_zero_sum_regardless_of_who_wins(self):
        new_white, new_black = rating_service.apply_game_result(
            white_rating=1300, black_rating=1250, winner="b", k=32)
        assert (new_white - 1300) == -(new_black - 1250)
