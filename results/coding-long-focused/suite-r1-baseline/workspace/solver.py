import csv
import io
import math
import re
from numbers import Real


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("invoice input must contain a header")

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid invoice header") from exc
    if header != ["id", "amount"]:
        raise ValueError("invalid invoice header")

    result = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    try:
        for row in reader:
            # csv.reader returns [] for physically blank lines.
            if not row:
                continue
            if len(row) != 2:
                raise ValueError("invoice record must have exactly two fields")
            identifier = row[0].strip()
            amount = row[1].strip()
            if not identifier or not amount or not amount_pattern.fullmatch(amount):
                raise ValueError("invalid invoice field")
            result.append({"id": identifier, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid invoice CSV") from exc
    return result


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    method_name = method.upper() if isinstance(method, str) else ""
    eligible = method_name in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
    if method_name == "POST" and isinstance(idempotency_key, str) and idempotency_key.strip():
        eligible = True
    if not eligible:
        return []

    delays = []
    after = retry_after if isinstance(retry_after, (list, tuple)) else ()
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or status not in (429, 503):
            break
        default = 100 if not delays else 200
        delay = default
        if index < len(after):
            value = after[index]
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
            raise ValueError("invalid archive member path")
        if path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path):
            raise ValueError("absolute or drive-prefixed path")

        parts = []
        for segment in path.replace("\\", "/").split("/"):
            if segment == "" or segment == ".":
                continue
            if segment == "..":
                if not parts:
                    raise ValueError("path escapes archive root")
                parts.pop()
            else:
                parts.append(segment)
        if not parts:
            raise ValueError("path normalizes to empty")
        member = "/".join(parts)
        if member not in seen:
            seen.add(member)
            normalized.append(member)
    return normalized
