import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING


_TERM = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:ms|s|m|h|d)")
_FACTORS = {
    "ms": Decimal(1),
    "s": Decimal(1000),
    "m": Decimal(60000),
    "h": Decimal(3600000),
    "d": Decimal(86400000),
}


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    stripped = text.strip()
    if not stripped:
        raise ValueError("duration must not be empty")

    total = Decimal(0)
    position = 0
    length = len(stripped)
    while position < length:
        match = _TERM.match(stripped, position)
        if match is None:
            raise ValueError("invalid duration")

        term = match.group()
        unit_match = re.search(r"(?:ms|s|m|h|d)$", term)
        unit = unit_match.group()
        number = term[:-len(unit)]
        try:
            total += Decimal(number) * _FACTORS[unit]
        except InvalidOperation as exc:
            raise ValueError("invalid duration") from exc

        position = match.end()
        if position == length:
            break
        if stripped[position] in " \t\n\r\v\f":
            while position < length and stripped[position] in " \t\n\r\v\f":
                position += 1
            if position == length:
                break
        # Otherwise the next term must begin immediately.

    return int(total.to_integral_value(rounding=ROUND_CEILING))
