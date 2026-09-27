import math
import numbers


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    statuses = list(statuses)
    if not statuses:
        return []

    method = method.upper() if isinstance(method, str) else ""
    retryable_method = method in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
    if method == "POST" and isinstance(idempotency_key, str) and idempotency_key:
        retryable_method = True
    if not retryable_method:
        return []

    delays = []
    after_values = retry_after if retry_after is not None else []
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or status not in (429, 503):
            break

        delay = 100 if not delays else 200
        try:
            value = after_values[index]
        except (IndexError, TypeError, KeyError):
            value = None

        if isinstance(value, numbers.Real) and not isinstance(value, bool):
            if math.isfinite(value) and value >= 0:
                override = min(1000, math.ceil(value * 1000))
                delay = max(delay, override)
        delays.append(delay)

    return delays
