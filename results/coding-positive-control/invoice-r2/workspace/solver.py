import csv
import re


def parse_invoices(text):
    lines = text.splitlines()
    # Ignore physically blank lines, but retain quoted/whitespace-only CSV rows.
    lines = [line for line in lines if line.strip()]
    if not lines:
        raise ValueError("input is empty")

    reader = csv.reader(lines, delimiter=";", skipinitialspace=True)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("input is empty") from None
    if len(header) != 2 or [field.strip() for field in header] != ["id", "amount"]:
        raise ValueError("expected header id;amount")

    result = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    for row in reader:
        if len(row) != 2:
            raise ValueError("each record must contain exactly two fields")
        identifier, amount = (field.strip() for field in row)
        if not identifier or not amount or not amount_pattern.fullmatch(amount):
            raise ValueError("invalid invoice fields")
        result.append({"id": identifier, "amount": amount.replace(",", ".")})
    return result
