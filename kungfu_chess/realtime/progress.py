def progress_fraction(start, finish, now):
    """0..1 fraction of the way from start to finish at now, clamped to
    that range. A non-positive duration (finish <= start) is treated as
    already complete, matching how a zero-distance Motion or a
    zero-length cooldown are both instantly "done" rather than
    undefined. Shared by Motion.progress and
    RealTimeArbiter.cooldown_progress - both are purely cosmetic for
    the UI and never affect game rules or timing."""
    duration = finish - start
    if duration <= 0:
        return 1.0
    return max(0.0, min(1.0, (now - start) / duration))
