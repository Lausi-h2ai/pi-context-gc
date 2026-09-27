from collections import deque


def admit_requests(timestamps, limit, window_ms):
    def is_integer(value):
        return isinstance(value, int) and not isinstance(value, bool)

    if not isinstance(timestamps, list):
        raise ValueError("timestamps must be a list")
    if not is_integer(limit) or limit <= 0:
        raise ValueError("limit must be a positive integer")
    if not is_integer(window_ms) or window_ms <= 0:
        raise ValueError("window_ms must be a positive integer")

    previous = None
    for timestamp in timestamps:
        if not is_integer(timestamp) or timestamp < 0:
            raise ValueError("timestamps must be nonnegative integers")
        if previous is not None and timestamp < previous:
            raise ValueError("timestamps must be nondecreasing")
        previous = timestamp

    active = deque()
    admitted = []
    for timestamp in timestamps:
        boundary = timestamp - window_ms
        while active and active[0] < boundary:
            active.popleft()
        if len(active) < limit:
            admitted.append(True)
            active.append(timestamp)
        else:
            admitted.append(False)
    return admitted
