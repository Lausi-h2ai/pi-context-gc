import re


_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def parse_env(text, defaults=None):
    """Parse dotenv-style assignments, returning defaults overlaid by parsed values."""
    if defaults is not None and not isinstance(defaults, dict):
        raise TypeError("defaults must be a dictionary")
    result = {} if defaults is None else dict(defaults)

    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("export") and len(stripped) > 6 and stripped[6].isspace():
            stripped = stripped[6:].lstrip()

        match = _KEY.match(stripped)
        if match is None:
            raise ValueError("malformed environment definition")
        key = match.group()
        pos = match.end()
        while pos < len(stripped) and stripped[pos].isspace():
            pos += 1
        if pos >= len(stripped) or stripped[pos] != "=":
            raise ValueError("malformed environment definition")
        pos += 1
        while pos < len(stripped) and stripped[pos].isspace():
            pos += 1

        if pos < len(stripped) and stripped[pos] in "'\"":
            quote = stripped[pos]
            pos += 1
            value_chars = []
            while pos < len(stripped) and stripped[pos] != quote:
                char = stripped[pos]
                if quote == '"' and char == "\\":
                    pos += 1
                    if pos >= len(stripped):
                        raise ValueError("unknown escape")
                    escaped = stripped[pos]
                    escapes = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t", "#": "#"}
                    if escaped not in escapes:
                        raise ValueError("unknown escape")
                    value_chars.append(escapes[escaped])
                else:
                    value_chars.append(char)
                pos += 1
            if pos >= len(stripped):
                raise ValueError("unterminated quoted value")
            pos += 1
            remainder = stripped[pos:].lstrip()
            if remainder and not remainder.startswith("#"):
                raise ValueError("junk after quoted value")
            value = "".join(value_chars)
        else:
            raw = stripped[pos:]
            comment_at = None
            for i, char in enumerate(raw):
                if char == "#" and (i == 0 or raw[i - 1].isspace()):
                    comment_at = i
                    break
            if comment_at is not None:
                raw = raw[:comment_at]
            value = raw.strip()

        result[key] = value
    return result
