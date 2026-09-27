import csv
import re


def parse_invoices(text):
    """Parse semicolon-separated invoice records, preserving amount precision."""
    if not text:
        raise ValueError("input must include a header")

    try:
        rows = csv.reader(text.splitlines(), delimiter=";", strict=True)
        header = next(rows)
    except (StopIteration, csv.Error) as exc:
        raise ValueError("invalid CSV or missing header") from exc

    if header != ["id", "amount"]:
        raise ValueError("expected header id;amount")

    result = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    for row in rows:
        if not row or (len(row) == 1 and not row[0].strip()):
            continue
        if len(row) != 2:
            raise ValueError("each record must have exactly two fields")

        identifier, amount = (field.strip() for field in row)
        if not identifier or not amount:
            raise ValueError("id and amount must not be empty")
        if not amount_pattern.fullmatch(amount):
            raise ValueError("invalid amount")

        result.append({"id": identifier, "amount": amount.replace(",", ".")})
    return result
