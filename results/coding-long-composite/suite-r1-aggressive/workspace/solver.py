import csv
import io
import math
import re
from numbers import Real


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("invalid invoice input")

    reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", skipinitialspace=True, strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("missing invoice header") from exc
    if len(header) != 2 or [field.strip() for field in header] != ["id", "amount"]:
        raise ValueError("invalid invoice header")

    invoices = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    try:
        for row in reader:
            # csv.reader returns [] for a physically blank line; whitespace-only
            # lines are blank too, but malformed nonblank records remain invalid.
            if not row:
                continue
            if len(row) != 2:
                raise ValueError("invoice record must have two fields")
            identifier, amount = (field.strip() for field in row)
            if not identifier or not amount or not amount_pattern.fullmatch(amount):
                raise ValueError("invalid invoice field")
            invoices.append({"id": identifier, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid CSV") from exc
    return invoices


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    try:
        status_list = list(statuses)
    except TypeError:
        return []
    method_name = method.upper() if isinstance(method, str) else ""
    if method_name not in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"} and not (
        method_name == "POST" and isinstance(idempotency_key, str) and idempotency_key.strip()
    ):
        return []

    hints = retry_after if isinstance(retry_after, (list, tuple)) else ()
    delays = []
    for index, status in enumerate(status_list):
        if len(delays) >= 2 or status not in (429, 503):
            break
        default = 100 if len(delays) == 0 else 200
        delay = default
        if index < len(hints):
            hint = hints[index]
            if isinstance(hint, Real) and not isinstance(hint, bool) and math.isfinite(hint) and hint >= 0:
                override = min(1000, math.ceil(hint * 1000))
                delay = max(default, override)
        delays.append(delay)
    return delays


def normalize_members(paths):
    normalized = []
    seen = set()
    for path in paths:
        if not isinstance(path, str) or "\x00" in path:
            raise ValueError("invalid archive member")
        if path.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", path):
            raise ValueError("absolute archive member")
        parts = []
        for segment in path.replace("\\", "/").split("/"):
            if segment in ("", "."):
                continue
            if segment == "..":
                if not parts:
                    raise ValueError("archive member escapes root")
                parts.pop()
            else:
                parts.append(segment)
        if not parts:
            raise ValueError("empty archive member")
        result = "/".join(parts)
        if result not in seen:
            seen.add(result)
            normalized.append(result)
    return normalized
