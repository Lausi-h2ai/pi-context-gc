def parse_env(text, defaults=None):
    import re

    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")

    result = {} if defaults is None else defaults.copy()
    key_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export") and len(stripped) > 6 and stripped[6].isspace():
            stripped = stripped[6:].lstrip()
            if not stripped:
                raise ValueError(f"malformed environment definition on line {line_number}")

        match = key_pattern.match(stripped)
        if match is None:
            raise ValueError(f"malformed environment definition on line {line_number}")
        key = match.group(0)
        position = match.end()
        while position < len(stripped) and stripped[position].isspace():
            position += 1
        if position >= len(stripped) or stripped[position] != "=":
            raise ValueError(f"malformed environment definition on line {line_number}")
        position += 1
        while position < len(stripped) and stripped[position].isspace():
            position += 1

        if position < len(stripped) and stripped[position] in ("'", '"'):
            quote = stripped[position]
            position += 1
            value_chars = []
            closed = False
            while position < len(stripped):
                char = stripped[position]
                if char == quote:
                    closed = True
                    position += 1
                    break
                if quote == '"' and char == "\\":
                    position += 1
                    if position >= len(stripped):
                        raise ValueError(f"invalid escape on line {line_number}")
                    escape = stripped[position]
                    escapes = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t", "#": "#"}
                    if escape not in escapes:
                        raise ValueError(f"invalid escape on line {line_number}")
                    value_chars.append(escapes[escape])
                    position += 1
                else:
                    value_chars.append(char)
                    position += 1
            if not closed:
                raise ValueError(f"unterminated quote on line {line_number}")
            remainder = stripped[position:].lstrip()
            if remainder and not remainder.startswith("#"):
                raise ValueError(f"junk after quoted value on line {line_number}")
            value = "".join(value_chars)
        else:
            remainder = stripped[position:]
            comment = len(remainder)
            for index, char in enumerate(remainder):
                if char == "#" and (index == 0 or remainder[index - 1].isspace()):
                    comment = index
                    break
            value = remainder[:comment].strip()

        result[key] = value
    return result
