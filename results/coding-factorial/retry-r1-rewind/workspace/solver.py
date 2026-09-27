def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    return [100 for status in statuses if status >= 400]
