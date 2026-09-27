from collections import deque


def admit_requests(timestamps, limit, window_ms):
    """Return whether each chronologically ordered request fits the rate limit."""
    if not isinstance(timestamps, list):
        raise ValueError("timestamps must be a list")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    if isinstance(window_ms, bool) or not isinstance(window_ms, int) or window_ms <= 0:
        raise ValueError("window_ms must be a positive integer")

    accepted_times = deque()
    result = []
    previous = None
    for timestamp in timestamps:
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamps must be nonnegative integers")
        if previous is not None and timestamp < previous:
            raise ValueError("timestamps must be nondecreasing")
        previous = timestamp

        cutoff = timestamp - window_ms
        while accepted_times and accepted_times[0] < cutoff:
            accepted_times.popleft()
        admitted = len(accepted_times) < limit
        result.append(admitted)
        if admitted:
            accepted_times.append(timestamp)

    return result
