import math
import numbers


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    statuses = list(statuses)
    if not statuses:
        return []

    method = method.upper() if isinstance(method, str) else ""
    if method in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}:
        can_retry = True
    elif method == "POST":
        can_retry = idempotency_key is not None and bool(str(idempotency_key).strip())
    else:
        can_retry = False

    overrides = retry_after if isinstance(retry_after, (list, tuple)) else []
    delays = []
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or not can_retry or status not in (429, 503):
            break

        delay = 100 * (2 ** len(delays))
        if index < len(overrides):
            value = overrides[index]
            if isinstance(value, numbers.Real) and not isinstance(value, bool):
                if math.isfinite(value) and value >= 0:
                    delay = min(1000, max(delay, math.ceil(value * 1000)))
        delays.append(delay)

    return delays
