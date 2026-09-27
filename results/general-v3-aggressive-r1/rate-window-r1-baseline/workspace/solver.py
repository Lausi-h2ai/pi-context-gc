from collections import deque


def admit_requests(timestamps, limit, window_ms):
    """Return whether each timestamped request is admitted by a sliding-window limit."""
    if not isinstance(timestamps, list):
        raise ValueError("timestamps must be a list")
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    if isinstance(window_ms, bool) or not isinstance(window_ms, int) or window_ms <= 0:
        raise ValueError("window_ms must be a positive integer")

    accepted = deque()
    result = []
    previous = -1

    for timestamp in timestamps:
        if (isinstance(timestamp, bool) or not isinstance(timestamp, int)
                or timestamp < 0 or timestamp < previous):
            raise ValueError("timestamps must be nonnegative, nondecreasing integers")
        previous = timestamp

        cutoff = timestamp - window_ms
        while accepted and accepted[0] < cutoff:
            accepted.popleft()

        admitted = len(accepted) < limit
        result.append(admitted)
        if admitted:
            accepted.append(timestamp)

    return result
