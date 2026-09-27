import re


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")

    result = {} if defaults is None else defaults.copy()
    key_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    escapes = {"\\\\": "\\", '\\"': '"', "\\n": "\n", "\\r": "\r", "\\t": "\t", "\\#": "#"}

    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("export") and len(stripped) > 6 and stripped[6].isspace():
            stripped = stripped[6:].lstrip()

        match = key_pattern.match(stripped)
        if not match:
            raise ValueError("malformed environment definition")
        key = match.group(0)
        pos = match.end()
        while pos < len(stripped) and stripped[pos].isspace():
            pos += 1
        if pos >= len(stripped) or stripped[pos] != "=":
            raise ValueError("malformed environment definition")
        pos += 1
        while pos < len(stripped) and stripped[pos].isspace():
            pos += 1

        if pos == len(stripped) or stripped[pos] == "#":
            value = ""
        elif stripped[pos] in ("'", '\"'):
            quote = stripped[pos]
            pos += 1
            chars = []
            while pos < len(stripped) and stripped[pos] != quote:
                char = stripped[pos]
                if quote == '\"' and char == "\\":
                    escape = stripped[pos:pos + 2]
                    if escape not in escapes:
                        raise ValueError("unknown escape sequence")
                    chars.append(escapes[escape])
                    pos += 2
                else:
                    chars.append(char)
                    pos += 1
            if pos >= len(stripped):
                raise ValueError("unterminated quoted value")
            pos += 1
            value = "".join(chars)
            remainder = stripped[pos:].lstrip()
            if remainder and not remainder.startswith("#"):
                raise ValueError("junk after quoted value")
        else:
            end = len(stripped)
            for i, char in enumerate(stripped[pos:], pos):
                if char == "#" and (i == pos or stripped[i - 1].isspace()):
                    end = i
                    break
            value = stripped[pos:end].strip()

        result[key] = value
    return result
