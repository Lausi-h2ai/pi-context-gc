import csv
import io
import math
import numbers
import re


_AMOUNT_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("invoice input must include a header")

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid invoice CSV") from exc
    if header != ["id", "amount"]:
        raise ValueError("expected id;amount header")

    results = []
    try:
        for row in reader:
            # csv.reader returns [] for a physically blank record.
            if not row:
                continue
            if len(row) != 2:
                raise ValueError("invoice records must have two fields")
            identifier, amount = (field.strip() for field in row)
            if not identifier or not amount or not _AMOUNT_RE.fullmatch(amount):
                raise ValueError("invalid invoice field")
            results.append({"id": identifier, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid invoice CSV") from exc
    return results


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    statuses = list(statuses)
    if not statuses:
        return []
    method_name = method.upper() if isinstance(method, str) else ""
    allowed = method_name in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
    if method_name == "POST":
        allowed = isinstance(idempotency_key, str) and bool(idempotency_key.strip())
    if not allowed:
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
        if isinstance(value, numbers.Real) and not isinstance(value, bool):
            if math.isfinite(value) and value >= 0:
                override = min(1000, math.ceil(value * 1000))
                delay = max(delay, override)
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
        if re.match(r"^[A-Za-z]:", path):
            raise ValueError("drive-prefixed archive member")

        stack = []
        for part in path.replace("\\", "/").split("/"):
            if part == "" or part == ".":
                continue
            if part == "..":
                if not stack:
                    raise ValueError("archive member escapes root")
                stack.pop()
            else:
                stack.append(part)
        if not stack:
            raise ValueError("archive member normalizes to empty")
        result = "/".join(stack)
        if result not in seen:
            seen.add(result)
            normalized.append(result)
    return normalized
