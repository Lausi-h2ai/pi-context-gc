import re
from fractions import Fraction


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    units = {"ms": 1, "s": 1000, "m": 60000, "h": 3600000, "d": 86400000}
    number = r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)"
    term = re.compile(r"(" + number + r")(ms|s|m|h|d)")
    whitespace = " \t\n\r\v\f"

    index = 0
    length = len(text)
    while index < length and text[index] in whitespace:
        index += 1
    if index == length:
        raise ValueError("duration must contain at least one term")

    total = Fraction(0)
    terms = 0
    while index < length:
        match = term.match(text, index)
        if match is None:
            raise ValueError("invalid duration term")
        total += Fraction(match.group(1)) * units[match.group(2)]
        terms += 1
        index = match.end()
        start = index
        while index < length and text[index] in whitespace:
            index += 1
        if index == length:
            break
        # Whitespace is optional between terms, but never part of a term.
        if index > start and term.match(text, index) is None:
            raise ValueError("invalid duration term")

    if not terms:
        raise ValueError("duration must contain at least one term")
    return (total.numerator + total.denominator - 1) // total.denominator
