import re
from decimal import Decimal, ROUND_CEILING


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    text = text.strip(" \t\n\r\f\v")
    if not text:
        raise ValueError("duration must not be empty")

    term = re.compile(r"(\d+(?:\.\d+)?)(ms|s|m|h|d)")
    factors = {"ms": 1, "s": 1000, "m": 60_000, "h": 3_600_000, "d": 86_400_000}
    position = 0
    terms = []

    while position < len(text):
        match = term.match(text, position)
        if match is None:
            raise ValueError("invalid duration")
        terms.append((match.group(1), factors[match.group(2)]))
        position = match.end()

        if position < len(text) and text[position] in " \t\n\r\f\v":
            while position < len(text) and text[position] in " \t\n\r\f\v":
                position += 1
            if position == len(text):
                break

    # Decimal arithmetic avoids floating-point rounding errors at millisecond
    # boundaries, including for very large duration values.
    total = sum((Decimal(value) * factor for value, factor in terms), Decimal(0))
    return int(total.to_integral_value(rounding=ROUND_CEILING))
