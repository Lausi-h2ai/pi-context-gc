import csv
import re
from io import StringIO


_AMOUNT_PATTERN = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")


def parse_invoices(text):
    if not text:
        raise ValueError("input must include a header")

    reader = csv.reader(StringIO(text, newline=""), delimiter=";", strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid or missing header") from exc

    if header != ["id", "amount"]:
        raise ValueError("header must be exactly 'id;amount'")

    invoices = []
    try:
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 2:
                raise ValueError("each record must contain exactly two fields")

            invoice_id, amount = (field.strip() for field in row)
            if not invoice_id or not amount:
                raise ValueError("id and amount must not be empty")
            if not _AMOUNT_PATTERN.fullmatch(amount):
                raise ValueError("invalid amount")

            invoices.append({"id": invoice_id, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid CSV") from exc

    return invoices
