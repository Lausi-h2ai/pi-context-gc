from collections import deque


def admit_requests(timestamps, limit, window_ms):
    """Admit requests subject to a sliding-window limit."""
    if isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    if isinstance(window_ms, bool) or not isinstance(window_ms, int) or window_ms <= 0:
        raise ValueError("window_ms must be a positive integer")
    if not isinstance(timestamps, list):
        raise ValueError("timestamps must be a list")

    for timestamp in timestamps:
        if isinstance(timestamp, bool) or not isinstance(timestamp, int) or timestamp < 0:
            raise ValueError("timestamps must be nonnegative integers")
    if any(timestamps[i] < timestamps[i - 1] for i in range(1, len(timestamps))):
        raise ValueError("timestamps must be nondecreasing")

    accepted = deque()
    result = []
    for timestamp in timestamps:
        while accepted and accepted[0] < timestamp - window_ms:
            accepted.popleft()
        if len(accepted) < limit:
            result.append(True)
            accepted.append(timestamp)
        else:
            result.append(False)
    return result
