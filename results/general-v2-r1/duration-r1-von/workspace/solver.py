import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    term = re.compile(r"(\d+(?:\.\d+)?|\.\d+)(ms|[smhd])")
    multipliers = {
        "ms": Decimal(1),
        "s": Decimal(1000),
        "m": Decimal(60000),
        "h": Decimal(3600000),
        "d": Decimal(86400000),
    }
    whitespace = " \t\n\r\v\f"
    pos = 0
    total = Decimal(0)
    count = 0

    while pos < len(text):
        while pos < len(text) and text[pos] in whitespace:
            pos += 1
        if pos == len(text):
            break
        match = term.match(text, pos)
        if match is None:
            raise ValueError("invalid duration")
        try:
            value = Decimal(match.group(1)) * multipliers[match.group(2)]
        except InvalidOperation as exc:
            raise ValueError("invalid duration") from exc
        total += value
        count += 1
        pos = match.end()

    if count == 0:
        raise ValueError("invalid duration")
    return int(total.to_integral_value(rounding=ROUND_CEILING))
