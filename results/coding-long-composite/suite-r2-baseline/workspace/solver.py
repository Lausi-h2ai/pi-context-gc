import csv
import math
import re
from numbers import Real


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("invoice input must include a header")

    try:
        rows = csv.reader(text.splitlines(), delimiter=";", strict=True)
        header = next(rows, None)
        if header != ["id", "amount"]:
            raise ValueError("expected header id;amount")

        result = []
        amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
        for row in rows:
            # csv.reader yields [] for physically blank lines.
            if not row:
                continue
            if len(row) != 2:
                raise ValueError("each invoice must contain exactly two fields")
            identifier, amount = (field.strip() for field in row)
            if not identifier or not amount or not amount_pattern.fullmatch(amount):
                raise ValueError("invalid invoice field")
            result.append({"id": identifier, "amount": amount.replace(",", ".")})
        return result
    except (csv.Error, StopIteration) as exc:
        raise ValueError("invalid invoice CSV") from exc


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    statuses = list(statuses)
    if not statuses:
        return []

    method_name = method.upper() if isinstance(method, str) else ""
    eligible = method_name in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"}
    if method_name == "POST" and isinstance(idempotency_key, str) and idempotency_key.strip():
        eligible = True
    if not eligible:
        return []

    delays = []
    after_values = retry_after if isinstance(retry_after, (list, tuple)) else []
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or status not in (429, 503):
            break
        default_ms = 100 if len(delays) == 0 else 200
        delay_ms = default_ms
        if index < len(after_values):
            value = after_values[index]
            if isinstance(value, Real) and not isinstance(value, bool) and math.isfinite(value) and value >= 0:
                override = min(1000, math.ceil(value * 1000))
                delay_ms = max(default_ms, override)
        delays.append(delay_ms)
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

        components = []
        for component in path.replace("\\", "/").split("/"):
            if component in ("", "."):
                continue
            if component == "..":
                if not components:
                    raise ValueError("archive member escapes root")
                components.pop()
            else:
                components.append(component)
        if not components:
            raise ValueError("archive member normalizes to empty")
        member = "/".join(components)
        if member not in seen:
            seen.add(member)
            normalized.append(member)
    return normalized
