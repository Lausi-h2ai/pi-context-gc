import math
import numbers


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    statuses = list(statuses)
    if not statuses:
        return []

    method = method.upper() if isinstance(method, str) else ""
    retryable_method = method in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
    if method == "POST":
        retryable_method = isinstance(idempotency_key, str) and bool(idempotency_key.strip())
    if not retryable_method:
        return []

    delays = []
    retry_after = retry_after if retry_after is not None else ()
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or status not in (429, 503):
            break

        delay = 100 * (len(delays) + 1)
        try:
            value = retry_after[index]
        except (IndexError, KeyError, TypeError):
            value = None
        if (isinstance(value, numbers.Real) and not isinstance(value, bool)
                and math.isfinite(value) and value >= 0):
            override = min(1000, math.ceil(value * 1000))
            delay = max(delay, override)
        delays.append(delay)
    return delays
