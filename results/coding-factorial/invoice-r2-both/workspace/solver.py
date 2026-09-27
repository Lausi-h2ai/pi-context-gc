import csv
import re
from io import StringIO


def parse_invoices(text):
    reader = csv.reader(StringIO(text), delimiter=";", skipinitialspace=True, strict=True)
    try:
        header = next(reader)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("missing or invalid header") from exc

    if header != ["id", "amount"]:
        raise ValueError("expected header id;amount")

    invoices = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    try:
        for row in reader:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 2:
                raise ValueError("each record must contain exactly two fields")
            invoice_id, amount = (field.strip() for field in row)
            if not invoice_id or not amount or not amount_pattern.fullmatch(amount):
                raise ValueError("invalid invoice fields")
            invoices.append({"id": invoice_id, "amount": amount.replace(",", ".")})
    except csv.Error as exc:
        raise ValueError("invalid CSV") from exc

    return invoices
