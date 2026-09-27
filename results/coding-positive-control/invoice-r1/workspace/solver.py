import csv
import re
from io import StringIO


_AMOUNT_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")


def parse_invoices(text):
    if not text:
        raise ValueError("input must include a header")

    reader = csv.reader(StringIO(text), delimiter=";", strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid CSV header") from exc

    if header != ["id", "amount"]:
        raise ValueError("expected header 'id;amount'")

    invoices = []
    try:
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 2:
                raise ValueError("each record must have exactly two fields")

            identifier, amount = (field.strip() for field in row)
            if not identifier or not amount or not _AMOUNT_RE.fullmatch(amount):
                raise ValueError("invalid id or amount")
            invoices.append({"id": identifier, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid CSV record") from exc

    return invoices
