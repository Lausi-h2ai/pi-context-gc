import csv
import re
from io import StringIO


_AMOUNT_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")


def parse_invoices(text):
    if not text:
        raise ValueError("input must contain a header")

    reader = csv.reader(StringIO(text, newline=""), delimiter=";", skipinitialspace=True)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("input must contain a header") from None

    if header != ["id", "amount"]:
        raise ValueError("header must be exactly 'id;amount'")

    invoices = []
    for row in reader:
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if len(row) != 2:
            raise ValueError("each record must contain exactly two fields")

        invoice_id, amount = (field.strip() for field in row)
        if not invoice_id or not amount:
            raise ValueError("id and amount must not be empty")
        if not _AMOUNT_RE.fullmatch(amount):
            raise ValueError("invalid amount")

        invoices.append({"id": invoice_id, "amount": amount.replace(",", ".")})

    return invoices
