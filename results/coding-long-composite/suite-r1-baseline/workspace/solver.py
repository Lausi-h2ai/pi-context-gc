import csv
import math
import re
from numbers import Real


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("invoice input must contain a header")

    try:
        rows = csv.reader(text.splitlines(), delimiter=";", skipinitialspace=True)
        header = next(rows)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid invoice CSV") from exc

    if [field.strip() for field in header] != ["id", "amount"]:
        raise ValueError("expected id;amount header")

    result = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    for row in rows:
        if not row or (len(row) == 1 and row[0] == ""):
            continue
        if len(row) != 2:
            raise ValueError("each invoice must have exactly two fields")
        identifier, amount = (field.strip() for field in row)
        if not identifier or not amount or not amount_pattern.fullmatch(amount):
            raise ValueError("invalid invoice field")
        result.append({"id": identifier, "amount": amount.replace(",", ".")})
    return result


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    method_name = method.upper() if isinstance(method, str) else ""
    allowed = {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
    can_retry = method_name in allowed or (
        method_name == "POST" and isinstance(idempotency_key, str) and bool(idempotency_key.strip())
    )
    if not can_retry:
        return []

    delays = []
    for index, status in enumerate(statuses):
        if len(delays) >= 2:
            break
        if status not in (429, 503):
            break
        default = 100 if len(delays) == 0 else 200
        delay = default
        try:
            value = retry_after[index]
        except (TypeError, IndexError, KeyError):
            value = None
        if isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
            override = min(1000, math.ceil(value * 1000))
            if override > delay:
                delay = override
        delays.append(delay)
    return delays


def normalize_members(paths):
    normalized = []
    seen = set()
    for path in paths:
        if not isinstance(path, str) or "\x00" in path:
            raise ValueError("invalid archive member")
        if path.startswith(("/", "\\")):
            raise ValueError("absolute archive member")
        if len(path) >= 2 and path[0].isascii() and path[0].isalpha() and path[1] == ":":
            raise ValueError("drive-prefixed archive member")

        stack = []
        for segment in path.replace("\\", "/").split("/"):
            if segment in ("", "."):
                continue
            if segment == "..":
                if not stack:
                    raise ValueError("archive member escapes root")
                stack.pop()
            else:
                stack.append(segment)
        if not stack:
            raise ValueError("empty archive member")
        member = "/".join(stack)
        if member not in seen:
            seen.add(member)
            normalized.append(member)
    return normalized
