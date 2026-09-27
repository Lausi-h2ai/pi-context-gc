import re
from decimal import Decimal, ROUND_CEILING


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    units = {
        "ms": 1,
        "s": 1000,
        "m": 60000,
        "h": 3600000,
        "d": 86400000,
    }
    term = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(ms|s|m|h|d)")
    whitespace = " \t\n\v\f\r"
    index = 0
    length = len(text)
    while index < length and text[index] in whitespace:
        index += 1
    if index == length:
        raise ValueError("empty duration")

    total = Decimal(0)
    while index < length:
        match = term.match(text, index)
        if match is None:
            raise ValueError("invalid duration")
        unit = match.group(1)
        number = text[index:match.start(1)]
        total += Decimal(number) * units[unit]
        index = match.end()
        start = index
        while index < length and text[index] in whitespace:
            index += 1
        if index == length:
            break
        if index == start:
            continue

    return int(total.to_integral_value(rounding=ROUND_CEILING))
