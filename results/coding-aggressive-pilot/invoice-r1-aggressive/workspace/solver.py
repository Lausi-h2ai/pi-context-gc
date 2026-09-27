import csv
import re


def parse_invoices(text):
    if not text:
        raise ValueError("input is empty")

    reader = csv.reader(text.splitlines(), delimiter=";", skipinitialspace=True)
    try:
        header = next(reader)
    except StopIteration:
        raise ValueError("input is empty") from None

    if header != ["id", "amount"]:
        raise ValueError("invalid header")

    invoices = []
    amount_pattern = re.compile(r"[+-]?\d+(?:[.,]\d+)?\Z")
    for row in reader:
        # A physically blank line is represented as an empty row by csv.reader.
        if not row:
            continue
        if len(row) != 2:
            raise ValueError("record must contain exactly two fields")

        identifier, amount = (field.strip() for field in row)
        if not identifier or not amount:
            raise ValueError("fields must not be empty")
        if not amount_pattern.fullmatch(amount):
            raise ValueError("invalid amount")

        invoices.append({"id": identifier, "amount": amount.replace(",", ".")})

    return invoices
