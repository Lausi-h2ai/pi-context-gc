import re


_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_DOUBLE_ESCAPES = {
    "\\": "\\",
    '"': '"',
    "n": "\n",
    "r": "\r",
    "t": "\t",
    "#": "#",
}


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")
    result = {} if defaults is None else defaults.copy()

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export") and len(line) > 6 and line[6].isspace():
            line = line[6:].lstrip()

        if "=" not in line:
            raise ValueError(f"invalid assignment at line {line_number}")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _KEY.fullmatch(key):
            raise ValueError(f"invalid key at line {line_number}")

        value_text = raw_value.lstrip()
        if value_text.startswith("'"):
            closing = value_text.find("'", 1)
            if closing < 0:
                raise ValueError(f"unterminated quote at line {line_number}")
            value = value_text[1:closing]
            remainder = value_text[closing + 1:]
            trailing = remainder.strip()
            if trailing and (not remainder[:1].isspace() or not trailing.startswith("#")):
                raise ValueError(f"junk after quoted value at line {line_number}")
        elif value_text.startswith('"'):
            parts = []
            index = 1
            while index < len(value_text):
                char = value_text[index]
                if char == '"':
                    break
                if char == "\\":
                    index += 1
                    if index >= len(value_text) or value_text[index] not in _DOUBLE_ESCAPES:
                        raise ValueError(f"invalid escape at line {line_number}")
                    parts.append(_DOUBLE_ESCAPES[value_text[index]])
                else:
                    parts.append(char)
                index += 1
            if index >= len(value_text) or value_text[index] != '"':
                raise ValueError(f"unterminated quote at line {line_number}")
            value = "".join(parts)
            remainder = value_text[index + 1:]
            trailing = remainder.strip()
            if trailing and (not remainder[:1].isspace() or not trailing.startswith("#")):
                raise ValueError(f"junk after quoted value at line {line_number}")
        else:
            value = re.split(r"\s+#|^#", value_text, maxsplit=1)[0].strip()

        result[key] = value

    return result
