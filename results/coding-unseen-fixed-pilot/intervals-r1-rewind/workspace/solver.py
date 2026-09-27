def merge_windows(windows):
    """Return the sorted union of strictly overlapping intervals."""
    if not isinstance(windows, list):
        raise ValueError("windows must be a list")

    intervals = []
    for window in windows:
        if not isinstance(window, list) or len(window) != 2:
            raise ValueError("each window must be a two-item list")
        start, end = window
        if (not isinstance(start, int) or isinstance(start, bool) or
                not isinstance(end, int) or isinstance(end, bool)):
            raise ValueError("window endpoints must be integers")
        if start > end:
            raise ValueError("window start must not exceed end")
        if start != end:
            intervals.append((start, end))

    intervals.sort()
    merged = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return merged
