import re
from fractions import Fraction


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    text = text.strip(" \t\n\r\v\f")
    if not text:
        raise ValueError("duration must not be empty")

    pattern = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:ms|s|m|h|d)")
    scales = {"ms": 1, "s": 1000, "m": 60000, "h": 3600000, "d": 86400000}
    total = Fraction(0)
    position = 0
    while position < len(text):
        match = pattern.match(text, position)
        if match is None:
            raise ValueError("invalid duration")
        token = match.group()
        unit = next(unit for unit in ("ms", "s", "m", "h", "d") if token.endswith(unit))
        number = token[:-len(unit)]
        total += Fraction(number) * scales[unit]
        position = match.end()
        if position == len(text):
            break
        whitespace_start = position
        while position < len(text) and text[position] in " \t\n\r\v\f":
            position += 1
        if position == whitespace_start:
            continue
        if position == len(text):
            break
        # After optional whitespace, the next loop must parse another term.

    return (total.numerator + total.denominator - 1) // total.denominator
