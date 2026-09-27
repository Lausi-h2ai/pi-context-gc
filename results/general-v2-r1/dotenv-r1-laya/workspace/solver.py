import re


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")

    result = {} if defaults is None else defaults.copy()
    key_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    escapes = {"\\\\": "\\", '\\"': '"', "\\n": "\n", "\\r": "\r", "\\t": "\t", "\\#": "#"}

    for line_number, line in enumerate(text.splitlines(), 1):
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("export") and len(stripped) > 6 and stripped[6].isspace():
            stripped = stripped[6:].lstrip()

        match = key_pattern.match(stripped)
        if match is None:
            raise ValueError(f"malformed line {line_number}")
        key = match.group(0)
        pos = match.end()
        while pos < len(stripped) and stripped[pos].isspace():
            pos += 1
        if pos >= len(stripped) or stripped[pos] != "=":
            raise ValueError(f"malformed line {line_number}")
        pos += 1
        while pos < len(stripped) and stripped[pos].isspace():
            pos += 1

        if pos == len(stripped) or stripped[pos] == "#":
            value = ""
        elif stripped[pos] in ("'", '"'):
            quote = stripped[pos]
            pos += 1
            chars = []
            while pos < len(stripped) and stripped[pos] != quote:
                char = stripped[pos]
                if quote == '"' and char == "\\":
                    pos += 1
                    if pos >= len(stripped):
                        raise ValueError(f"malformed line {line_number}")
                    escape = "\\" + stripped[pos]
                    if escape not in escapes:
                        raise ValueError(f"malformed line {line_number}")
                    chars.append(escapes[escape])
                else:
                    chars.append(char)
                pos += 1
            if pos >= len(stripped):
                raise ValueError(f"malformed line {line_number}")
            pos += 1
            remainder = stripped[pos:].lstrip()
            if remainder and not remainder.startswith("#"):
                raise ValueError(f"malformed line {line_number}")
            value = "".join(chars)
        else:
            raw = stripped[pos:]
            comment = re.search(r"\s+#", raw)
            if raw.startswith("#"):
                value = ""
            else:
                if comment:
                    raw = raw[:comment.start()]
                value = raw.strip()

        result[key] = value
    return result
