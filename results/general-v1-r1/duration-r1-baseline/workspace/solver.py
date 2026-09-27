import re
from decimal import Decimal, InvalidOperation, ROUND_CEILING, localcontext


def parse_duration(text):
    if not isinstance(text, str):
        raise ValueError("duration must be a string")

    term_pattern = re.compile(r"(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+)(?:ms|s|m|h|d)")
    multipliers = {
        "ms": Decimal(1),
        "s": Decimal(1000),
        "m": Decimal(60000),
        "h": Decimal(3600000),
        "d": Decimal(86400000),
    }

    position = 0
    terms = []
    found_term = False
    length = len(text)

    while position < length:
        while position < length and text[position] in " \t\n\r\f\v":
            position += 1
        if position == length:
            break

        match = term_pattern.match(text, position)
        if match is None:
            raise ValueError("invalid duration")

        term = match.group(0)
        unit = next(unit for unit in ("ms", "s", "m", "h", "d") if term.endswith(unit))
        number = term[:-len(unit)]
        try:
            value = Decimal(number)
        except InvalidOperation as exc:
            raise ValueError("invalid duration") from exc
        terms.append((value, multipliers[unit]))
        position = match.end()

        if position < length and text[position] not in " \t\n\r\f\v" and term_pattern.match(text, position) is None:
            raise ValueError("invalid duration")

    if not terms:
        raise ValueError("invalid duration")

    # Decimal arithmetic uses a bounded default precision; size it to the input
    # so large values and tiny fractions are still summed and rounded exactly.
    precision = max(28, sum(len(value.as_tuple().digits) for value, _ in terms) + len(terms) + 20)
    try:
        with localcontext() as context:
            context.prec = precision
            total = sum((value * multiplier for value, multiplier in terms), Decimal(0))
            return int(total.to_integral_value(rounding=ROUND_CEILING))
    except (InvalidOperation, OverflowError, ValueError) as exc:
        raise ValueError("invalid duration") from exc
