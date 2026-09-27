def merge_windows(windows):
    """Return the union of valid intervals, merging strict overlaps."""
    intervals = []

    for pair in windows:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError("each interval must be a two-item list")
        start, end = pair
        if (isinstance(start, bool) or not isinstance(start, int) or
                isinstance(end, bool) or not isinstance(end, int)):
            raise ValueError("interval endpoints must be integers")
        if start > end:
            raise ValueError("interval start must not exceed its end")
        if start != end:
            intervals.append([start, end])

    intervals.sort(key=lambda interval: (interval[0], interval[1]))
    merged = []
    for start, end in intervals:
        if merged and start < merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1][1] = end
        else:
            merged.append([start, end])
    return merged
