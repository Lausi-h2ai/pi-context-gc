import csv
import io
import math
import re
from numbers import Real


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("invoice input must include a header")
    try:
        rows = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
        header = next(rows)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid invoice CSV header") from exc
    if header != ["id", "amount"]:
        raise ValueError("expected header id;amount")

    invoices = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    for row in rows:
        # csv.reader returns [] for a physically blank line.
        if not row:
            continue
        if len(row) != 2:
            raise ValueError("each invoice must have exactly two fields")
        identifier, amount = (field.strip() for field in row)
        if not identifier or not amount or not amount_pattern.fullmatch(amount):
            raise ValueError("invalid invoice field")
        invoices.append({"id": identifier, "amount": amount.replace(",", ".")})
    return invoices


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    method = method.upper() if isinstance(method, str) else ""
    if method in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}:
        allowed = True
    elif method == "POST":
        allowed = isinstance(idempotency_key, str) and bool(idempotency_key.strip())
    else:
        allowed = False
    if not allowed:
        return []

    delays = []
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or status not in (429, 503):
            break
        default_ms = 100 if len(delays) == 0 else 200
        delay = default_ms
        try:
            candidate = retry_after[index]
        except (TypeError, IndexError, KeyError):
            candidate = None
        if isinstance(candidate, Real) and not isinstance(candidate, bool):
            seconds = float(candidate)
            if math.isfinite(seconds) and seconds >= 0:
                override = min(1000, math.ceil(seconds * 1000))
                if override > delay:
                    delay = override
        delays.append(delay)
    return delays


def normalize_members(paths):
    result = []
    seen = set()
    for path in paths:
        if not isinstance(path, str) or "\x00" in path:
            raise ValueError("invalid archive member path")
        if path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path):
            raise ValueError("absolute archive member path")
        components = []
        for part in re.split(r"[/\\]+", path):
            if part in ("", "."):
                continue
            if part == "..":
                if not components:
                    raise ValueError("archive path escapes root")
                components.pop()
            else:
                components.append(part)
        if not components:
            raise ValueError("archive member path normalizes to empty")
        normalized = "/".join(components)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
