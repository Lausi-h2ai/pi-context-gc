from collections import deque


def admit_requests(timestamps, limit, window_ms):
    if not isinstance(timestamps, list):
        raise ValueError("timestamps must be a list")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    if isinstance(window_ms, bool) or not isinstance(window_ms, int) or window_ms <= 0:
        raise ValueError("window_ms must be a positive integer")

    previous = None
    for timestamp in timestamps:
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamps must be nonnegative integers")
        if previous is not None and timestamp < previous:
            raise ValueError("timestamps must be nondecreasing")
        previous = timestamp

    active = deque()
    decisions = []
    for timestamp in timestamps:
        cutoff = timestamp - window_ms
        while active and active[0] < cutoff:
            active.popleft()
        admitted = len(active) < limit
        decisions.append(admitted)
        if admitted:
            active.append(timestamp)
    return decisions
