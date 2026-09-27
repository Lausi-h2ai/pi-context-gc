import re
from fractions import Fraction


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    # ASCII whitespace is permitted between terms and around the whole input.
    term = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(ms|[smhd])")
    factors = {
        "ms": 1,
        "s": 1000,
        "m": 60000,
        "h": 3600000,
        "d": 86400000,
    }
    whitespace = " \t\n\r\v\f"
    pos = 0
    total = Fraction(0)
    found = False

    while pos < len(text):
        while pos < len(text) and text[pos] in whitespace:
            pos += 1
        if pos == len(text):
            break
        match = term.match(text, pos)
        if match is None:
            raise ValueError("invalid duration")
        number, unit = match.group(0)[:-len(match.group(1))], match.group(1)
        try:
            total += Fraction(number) * factors[unit]
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError("invalid duration") from exc
        found = True
        pos = match.end()

    if not found:
        raise ValueError("duration must contain at least one term")
    return (total.numerator + total.denominator - 1) // total.denominator
