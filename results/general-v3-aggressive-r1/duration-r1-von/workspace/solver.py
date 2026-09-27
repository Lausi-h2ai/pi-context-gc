from decimal import Decimal, InvalidOperation, ROUND_CEILING
import re


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    term = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:ms|s|m|h|d)")
    units = {"ms": 1, "s": 1000, "m": 60000, "h": 3600000, "d": 86400000}
    position = 0
    total = Decimal(0)
    found = False

    while position < len(text):
        while position < len(text) and text[position] in " \t\n\r\f\v":
            position += 1
        if position == len(text):
            break

        match = term.match(text, position)
        if match is None:
            raise ValueError("invalid duration")

        value, unit = re.fullmatch(
            r"([0-9]+(?:\.[0-9]+)?|\.[0-9]+)(ms|s|m|h|d)", match.group()
        ).groups()
        try:
            total += Decimal(value) * units[unit]
        except InvalidOperation as exc:
            raise ValueError("invalid duration") from exc
        found = True
        position = match.end()

        if position < len(text) and text[position] not in " \t\n\r\f\v" and not text[position].isdigit() and text[position] != ".":
            raise ValueError("invalid duration")

    if not found:
        raise ValueError("invalid duration")
    return int(total.to_integral_value(rounding=ROUND_CEILING))
