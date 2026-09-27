import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    text = text.strip(" \t\n\r\v\f")
    if not text:
        raise ValueError("duration must contain at least one term")

    term = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(ms|[smhd])")
    factors = {
        "ms": Decimal(1),
        "s": Decimal(1000),
        "m": Decimal(60000),
        "h": Decimal(3600000),
        "d": Decimal(86400000),
    }
    total = Decimal(0)
    position = 0
    while position < len(text):
        match = term.match(text, position)
        if match is None:
            raise ValueError("malformed duration")
        number_start = position
        number_end = match.start(1)
        try:
            value = Decimal(text[number_start:number_end])
        except InvalidOperation as exc:
            raise ValueError("malformed duration") from exc
        total += value * factors[match.group(1)]
        position = match.end()

        if position < len(text) and text[position] in " \t\n\r\v\f":
            while position < len(text) and text[position] in " \t\n\r\v\f":
                position += 1
            if position == len(text):
                break

    return int(total.to_integral_value(rounding=ROUND_CEILING))
