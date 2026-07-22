"""ConnectionService (Master Plan v2 Section 10.3, Decision 7) - tracks
players who disconnected mid-game and their reconnect grace window.
Deterministic and clock-injected, like MatchmakingService/RealTimeArbiter
(Rule 9): the composition root's tick loop advances this clock via
now_ms - nothing here ever reads a real wall clock.

Does NOT pause GameEngine/RealTimeArbiter while a player is
disconnected - the game keeps running in real time (an in-flight Motion
or an expiring cooldown still resolves) exactly as if they were still
connected. This module only tracks the grace-period countdown for the
disconnected player's own return; GameService.forfeit (called once the
countdown expires) is what actually ends the game.
"""

DEFAULT_GRACE_PERIOD_MS = 20_000


class _DisconnectedPlayer:
    def __init__(self, game_id, identity, disconnected_at_ms):
        self.game_id = game_id
        self.identity = identity
        self.disconnected_at_ms = disconnected_at_ms


class ConnectionService:
    def __init__(self, grace_period_ms=DEFAULT_GRACE_PERIOD_MS):
        self.grace_period_ms = grace_period_ms
        self._disconnected = {}

    def record_disconnect(self, game_id, identity, now_ms):
        self._disconnected[identity] = _DisconnectedPlayer(game_id, identity, now_ms)

    def reconnect(self, identity):
        """Cancels the grace timer for this identity, if any, and
        returns the game_id they were in - or None if they weren't (or
        are no longer) tracked as disconnected."""
        player = self._disconnected.pop(identity, None)
        return player.game_id if player is not None else None

    def is_disconnected(self, identity):
        return identity in self._disconnected

    def pop_expired(self, now_ms):
        """Removes and returns [(game_id, identity), ...] for every
        player whose grace period has elapsed - the caller forfeits
        each of them exactly once."""
        expired = [
            player for player in self._disconnected.values()
            if now_ms - player.disconnected_at_ms >= self.grace_period_ms
        ]
        for player in expired:
            del self._disconnected[player.identity]
        return [(player.game_id, player.identity) for player in expired]
