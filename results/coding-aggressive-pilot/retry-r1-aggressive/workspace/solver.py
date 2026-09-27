import math
import numbers


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    statuses = list(statuses)
    if not statuses:
        return []

    method = method.upper() if isinstance(method, str) else ""
    if method == "POST":
        allowed = isinstance(idempotency_key, str) and bool(idempotency_key.strip())
    else:
        allowed = method in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
    if not allowed:
        return []

    delays = []
    retry_after = retry_after if retry_after is not None else []
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or status not in (429, 503):
            break

        default = 100 * (len(delays) + 1)
        delay = default
        try:
            value = retry_after[index]
        except (IndexError, TypeError):
            value = None
        if isinstance(value, numbers.Real) and math.isfinite(value) and value >= 0:
            delay = max(default, min(1000, math.ceil(value * 1000)))
        delays.append(delay)
    return delays
