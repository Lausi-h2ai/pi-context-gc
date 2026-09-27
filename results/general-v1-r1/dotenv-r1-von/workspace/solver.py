import re


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")
    result = {} if defaults is None else dict(defaults)
    escapes = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t", "#": "#"}

    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export") and len(stripped) > 6 and stripped[6].isspace():
            stripped = stripped[6:].lstrip()

        match = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
        if not match:
            raise ValueError("malformed environment definition")
        key = match.group(1)
        rest = stripped[match.end():]
        rest = rest.lstrip()

        if rest.startswith("'"):
            end = rest.find("'", 1)
            if end < 0:
                raise ValueError("unterminated single-quoted value")
            value = rest[1:end]
            tail = rest[end + 1:].lstrip()
            if tail and not tail.startswith("#"):
                raise ValueError("unexpected text after quoted value")
        elif rest.startswith('"'):
            chars = []
            i = 1
            while i < len(rest) and rest[i] != '"':
                if rest[i] == "\\":
                    i += 1
                    if i >= len(rest) or rest[i] not in escapes:
                        raise ValueError("invalid escape in quoted value")
                    chars.append(escapes[rest[i]])
                else:
                    chars.append(rest[i])
                i += 1
            if i >= len(rest):
                raise ValueError("unterminated double-quoted value")
            value = "".join(chars)
            tail = rest[i + 1:].lstrip()
            if tail and not tail.startswith("#"):
                raise ValueError("unexpected text after quoted value")
        else:
            comment = re.search(r"(?<!\S)#", rest)
            value = (rest[:comment.start()] if comment else rest).strip()

        result[key] = value
    return result
