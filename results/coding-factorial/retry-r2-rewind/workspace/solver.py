import math
import numbers


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    """Return the delays before retries, in milliseconds."""
    if not statuses:
        return []

    method = method.upper() if isinstance(method, str) else ""
    if method in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}:
        retry_allowed = True
    elif method == "POST":
        retry_allowed = isinstance(idempotency_key, str) and bool(idempotency_key.strip())
    else:
        retry_allowed = False

    if not retry_allowed:
        return []

    delays = []
    retry_after = retry_after if retry_after is not None else []
    for index, status in enumerate(statuses):
        if status not in (429, 503) or len(delays) >= 2:
            break

        delay = (100, 200)[len(delays)]
        try:
            value = retry_after[index]
        except (IndexError, TypeError):
            value = None

        if isinstance(value, numbers.Real) and not isinstance(value, bool):
            try:
                if math.isfinite(value) and value >= 0:
                    delay = min(1000, max(delay, math.ceil(value * 1000)))
            except (OverflowError, TypeError, ValueError):
                pass
        delays.append(delay)

    return delays
