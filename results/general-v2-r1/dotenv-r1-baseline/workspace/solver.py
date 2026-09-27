import re


_KEY_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")
    result = {} if defaults is None else dict(defaults)

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export") and len(line) > 6 and line[6].isspace():
            line = line[6:].lstrip()

        match = _KEY_RE.match(line)
        if match is None:
            raise ValueError("invalid environment definition")
        key = match.group()
        pos = match.end()
        while pos < len(line) and line[pos].isspace():
            pos += 1
        if pos >= len(line) or line[pos] != "=":
            raise ValueError("invalid environment definition")
        pos += 1
        while pos < len(line) and line[pos].isspace():
            pos += 1

        if pos == len(line):
            value = ""
        elif line[pos] in "'\"":
            quote = line[pos]
            pos += 1
            chars = []
            while pos < len(line) and line[pos] != quote:
                char = line[pos]
                if quote == '"' and char == "\\":
                    pos += 1
                    if pos >= len(line):
                        raise ValueError("invalid escape in quoted value")
                    escaped = line[pos]
                    escapes = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t", "#": "#"}
                    if escaped not in escapes:
                        raise ValueError("unknown escape in quoted value")
                    chars.append(escapes[escaped])
                else:
                    chars.append(char)
                pos += 1
            if pos >= len(line):
                raise ValueError("unterminated quoted value")
            value = "".join(chars)
            pos += 1
            remainder = line[pos:].strip()
            if remainder and not remainder.startswith("#"):
                raise ValueError("junk after quoted value")
        else:
            end = len(line)
            for i, char in enumerate(line[pos:], start=pos):
                if char == "#" and (i == pos or line[i - 1].isspace()):
                    end = i
                    break
            value = line[pos:end].strip()
        result[key] = value
    return result
