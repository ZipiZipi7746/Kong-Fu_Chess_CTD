"""Pure ELO rating functions (Master Plan v2 Decision 4/Section 10.2) -
no game/session/repository state, no side effects. GameService calls
these on a completed, rated game's GameEndedEvent; matchmaking_service
calls expected_score indirectly through nothing at all (matching is
purely rating-distance based, no odds calculation needed there).

DEFAULT_K_FACTOR follows this project's existing convention of a plain
class/module-level constant rather than a separate Config class
hierarchy (see RealTimeArbiter.DEFAULT_MOVE_COOLDOWN_MS, GameController.
JUMP_DURATION_MS, auth_service.DEFAULT_RATING) - no such Config
hierarchy exists anywhere else in this codebase, so one wasn't invented
for this module either."""

DEFAULT_K_FACTOR = 32


def expected_score(rating_a, rating_b):
    """The standard logistic Elo expected score for a player rated
    rating_a against an opponent rated rating_b - a value in (0, 1)."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_rating(rating, expected, actual, k=DEFAULT_K_FACTOR):
    """actual is always exactly 1.0 (win) or 0.0 (loss) - Decision 12,
    no draws anywhere in this project. Always rounds to the nearest
    int: ratings are whole numbers, never fractional."""
    return round(rating + k * (actual - expected))


def apply_game_result(white_rating, black_rating, winner, k=DEFAULT_K_FACTOR):
    """Returns (new_white_rating, new_black_rating) for a just-completed
    rated game. winner is "w" or "b" - this project has no draw outcome
    (Decision 12), so actual is always exactly 1.0/0.0 for one side and
    the complementary 0.0/1.0 for the other."""
    white_expected = expected_score(white_rating, black_rating)
    black_expected = expected_score(black_rating, white_rating)
    white_actual = 1.0 if winner == "w" else 0.0
    black_actual = 1.0 - white_actual

    new_white = update_rating(white_rating, white_expected, white_actual, k)
    new_black = update_rating(black_rating, black_expected, black_actual, k)
    return new_white, new_black
