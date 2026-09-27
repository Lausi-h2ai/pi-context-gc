import csv
import re
from io import StringIO


_AMOUNT_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")


def parse_invoices(text):
    if not text:
        raise ValueError("input must include a header")

    try:
        rows = csv.reader(StringIO(text, newline=""), delimiter=";", strict=True)
        header = next(rows)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid CSV header") from exc

    if header != ["id", "amount"]:
        raise ValueError("header must be exactly 'id;amount'")

    invoices = []
    try:
        for row in rows:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 2:
                raise ValueError("each record must contain exactly two fields")
            identifier, amount = (field.strip() for field in row)
            if not identifier or not amount or not _AMOUNT_RE.fullmatch(amount):
                raise ValueError("invalid invoice field")
            invoices.append({"id": identifier, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid CSV record") from exc

    return invoices
