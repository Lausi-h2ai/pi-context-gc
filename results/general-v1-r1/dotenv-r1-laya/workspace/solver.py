import re


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")

    result = {} if defaults is None else defaults.copy()
    key_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    escapes = {"\\": "\\", '"': '"', "n": "\n", "r": "\r", "t": "\t", "#": "#"}

    for line in text.splitlines():
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue

        if stripped.startswith("export") and len(stripped) > 6 and stripped[6].isspace():
            stripped = stripped[6:].lstrip()

        match = key_pattern.match(stripped)
        if match is None:
            raise ValueError("malformed environment definition")
        key = match.group(0)
        rest = stripped[match.end():].lstrip()
        if not rest.startswith("="):
            raise ValueError("malformed environment definition")
        value_text = rest[1:].lstrip()

        if value_text.startswith("'"):
            end = value_text.find("'", 1)
            if end == -1:
                raise ValueError("unterminated quoted value")
            value = value_text[1:end]
            tail = value_text[end + 1:].lstrip()
            if tail and not tail.startswith("#"):
                raise ValueError("junk after quoted value")
            if tail.startswith("#") and len(tail) > 1 and not tail[1].isspace():
                raise ValueError("invalid inline comment")
        elif value_text.startswith('"'):
            chars = []
            i = 1
            while i < len(value_text) and value_text[i] != '"':
                char = value_text[i]
                if char == "\\":
                    i += 1
                    if i >= len(value_text) or value_text[i] not in escapes:
                        raise ValueError("invalid escape in quoted value")
                    chars.append(escapes[value_text[i]])
                else:
                    chars.append(char)
                i += 1
            if i >= len(value_text):
                raise ValueError("unterminated quoted value")
            value = "".join(chars)
            tail = value_text[i + 1:].lstrip()
            if tail and not tail.startswith("#"):
                raise ValueError("junk after quoted value")
            if tail.startswith("#") and len(tail) > 1 and not tail[1].isspace():
                raise ValueError("invalid inline comment")
        else:
            value_text = value_text.lstrip()
            if value_text.startswith("#"):
                value_text = ""
            else:
                comment = re.search(r"\s+#", value_text)
                if comment:
                    value_text = value_text[:comment.start()]
            value = value_text.strip()

        result[key] = value

    return result
