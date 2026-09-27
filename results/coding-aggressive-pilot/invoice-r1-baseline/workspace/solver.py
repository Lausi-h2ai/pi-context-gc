import csv
import re
from io import StringIO


def parse_invoices(text):
    if not text:
        raise ValueError("input must include a header")

    try:
        rows = csv.reader(StringIO(text, newline=""), delimiter=";", strict=True)
        header = next(rows)
        if header != ["id", "amount"]:
            raise ValueError("expected header id;amount")

        invoices = []
        for row in rows:
            if not row or (len(row) == 1 and not row[0].strip()):
                continue
            if len(row) != 2:
                raise ValueError("records must contain exactly two fields")
            identifier, amount = (field.strip() for field in row)
            if not identifier or not amount:
                raise ValueError("id and amount must not be empty")
            if not re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", amount):
                raise ValueError("invalid amount")
            invoices.append({"id": identifier, "amount": amount.replace(",", ".")})
        return invoices
    except csv.Error as exc:
        raise ValueError("invalid CSV input") from exc
