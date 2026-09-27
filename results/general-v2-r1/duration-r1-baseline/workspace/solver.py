import re
from fractions import Fraction


_DURATION_TERM = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:ms|[smhd])")
_DURATION_UNITS = {
    "ms": 1,
    "s": 1000,
    "m": 60000,
    "h": 3600000,
    "d": 86400000,
}


def parse_duration(text):
    if not isinstance(text, str) or not text.strip():
        raise ValueError("duration must be a non-empty string")

    total = Fraction(0)
    position = 0
    length = len(text)

    while position < length:
        while position < length and text[position] in " \t\n\r\v\f":
            position += 1
        if position == length:
            break

        match = _DURATION_TERM.match(text, position)
        if match is None:
            raise ValueError("invalid duration")

        term = match.group(0)
        unit = "ms" if term.endswith("ms") else term[-1]
        number = term[:-len(unit)]
        total += Fraction(number) * _DURATION_UNITS[unit]
        position = match.end()

        if position < length and text[position] not in " \t\n\r\v\f" and not _DURATION_TERM.match(text, position):
            raise ValueError("invalid duration")

    return (total.numerator + total.denominator - 1) // total.denominator
