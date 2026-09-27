import csv
import re
from io import StringIO


_AMOUNT_RE = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")


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
            # csv.reader returns [] for a physically blank line; whitespace-only
            # lines are records and will fail the required two-field check.
            if not row:
                continue
            if len(row) != 2:
                raise ValueError("each record must contain exactly two fields")

            invoice_id, amount = (field.strip() for field in row)
            if not invoice_id or not amount or not _AMOUNT_RE.fullmatch(amount):
                raise ValueError("invalid invoice id or amount")
            invoices.append({"id": invoice_id, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid CSV record") from exc

    return invoices
