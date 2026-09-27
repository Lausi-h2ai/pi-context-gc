import csv
import math
import numbers
import re
import string


def parse_invoices(text):
    if not isinstance(text, str) or text == "":
        raise ValueError("input must contain a header")

    rows = csv.reader(text.splitlines(), delimiter=";", strict=True)
    try:
        header = next(rows)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid CSV header") from exc
    if header != ["id", "amount"]:
        raise ValueError("invalid CSV header")

    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    result = []
    try:
        for row in rows:
            # csv.reader yields [] for physically blank lines.
            if not row:
                continue
            if len(row) != 2:
                raise ValueError("each record must have two fields")
            identifier, amount = (field.strip() for field in row)
            if not identifier or not amount or not amount_pattern.fullmatch(amount):
                raise ValueError("invalid invoice record")
            result.append({"id": identifier, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid CSV record") from exc
    return result


def retry_delays(statuses, method="GET", idempotency_key=None, retry_after=None):
    method = method.upper() if isinstance(method, str) else ""
    if method not in {"GET", "HEAD", "PUT", "DELETE", "OPTIONS"} and not (
        method == "POST" and isinstance(idempotency_key, str) and idempotency_key.strip()
    ):
        return []

    result = []
    headers = retry_after if retry_after is not None else []
    for index, status in enumerate(statuses):
        if len(result) >= 2 or status not in (429, 503):
            break
        default = 100 if len(result) == 0 else 200
        delay = default
        try:
            value = headers[index]
            if isinstance(value, numbers.Real) and not isinstance(value, bool):
                seconds = float(value)
                if math.isfinite(seconds) and seconds >= 0:
                    delay = max(delay, min(1000, math.ceil(seconds * 1000)))
        except (IndexError, TypeError, KeyError, OverflowError, ValueError):
            pass
        result.append(delay)
    return result


def normalize_members(paths):
    result = []
    seen = set()
    for path in paths:
        if not isinstance(path, str) or "\x00" in path:
            raise ValueError("invalid archive path")
        if path.startswith(("/", "\\")):
            raise ValueError("absolute archive path")
        normalized_input = path.replace("\\", "/")
        if len(normalized_input) >= 2 and normalized_input[0] in string.ascii_letters and normalized_input[1] == ":":
            raise ValueError("drive-prefixed archive path")

        components = []
        for part in normalized_input.split("/"):
            if part in ("", "."):
                continue
            if part == "..":
                if not components:
                    raise ValueError("archive path escapes root")
                components.pop()
            else:
                components.append(part)
        if not components:
            raise ValueError("empty archive path")
        normalized = "/".join(components)
        if normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result
