import csv
import math
import re
from io import StringIO


_AMOUNT_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
_DRIVE_RE = re.compile(r"^[A-Za-z]:")


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("empty input")

    try:
        rows = list(csv.reader(StringIO(text, newline=""), delimiter=";", strict=True))
    except csv.Error as exc:
        raise ValueError("invalid CSV") from exc

    # csv.reader returns [] for truly empty input, and [] rows for blank lines.
    header_index = next((i for i, row in enumerate(rows) if row), None)
    if header_index is None or rows[header_index] != ["id", "amount"]:
        raise ValueError("expected id;amount header")

    result = []
    for row in rows[header_index + 1:]:
        if not row or (len(row) == 1 and row[0] == ""):
            continue
        if len(row) != 2:
            raise ValueError("record must contain exactly two fields")
        identifier, amount = (field.strip() for field in row)
        if not identifier or not amount or not _AMOUNT_RE.fullmatch(amount):
            raise ValueError("invalid invoice record")
        result.append({"id": identifier, "amount": amount.replace(",", ".")})
    return result


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    method = method.upper() if isinstance(method, str) else ""
    if method not in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"} and not (
        method == "POST" and isinstance(idempotency_key, str) and idempotency_key.strip()
    ):
        return []

    delays = []
    retry_after = retry_after if retry_after is not None else []
    for index, status in enumerate(statuses):
        if len(delays) >= 2 or status not in (429, 503):
            break
        default = 100 * (len(delays) + 1)
        delay = default
        try:
            value = retry_after[index]
        except (IndexError, TypeError, KeyError):
            value = None
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if math.isfinite(value) and value >= 0:
                override = min(1000, math.ceil(value * 1000))
                if override > delay:
                    delay = override
        delays.append(delay)
    return delays


def normalize_members(paths):
    result = []
    seen = set()
    for path in paths:
        if not isinstance(path, str) or "\x00" in path:
            raise ValueError("invalid archive member")
        if path.startswith(("/", "\\")) or _DRIVE_RE.match(path):
            raise ValueError("absolute archive member")
        components = []
        for part in path.replace("\\", "/").split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if not components:
                    raise ValueError("archive member escapes root")
                components.pop()
            else:
                components.append(part)
        normalized = "/".join(components)
        if not normalized:
            raise ValueError("empty archive member")
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
