import re


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise ValueError("defaults must be a dictionary")

    result = {} if defaults is None else defaults.copy()
    key_pattern = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    escapes = {"\\\\": "\\", '\\"': '\"', "\\n": "\n", "\\r": "\r", "\\t": "\t", "\\#": "#"}

    for line_number, raw_line in enumerate(text.splitlines(), 1):
        line = raw_line.lstrip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export") and len(line) > 6 and line[6].isspace():
            line = line[6:].lstrip()

        match = key_pattern.match(line)
        if match is None:
            raise ValueError(f"malformed line {line_number}")
        key = match.group(0)
        pos = match.end()
        while pos < len(line) and line[pos].isspace():
            pos += 1
        if pos >= len(line) or line[pos] != "=":
            raise ValueError(f"malformed line {line_number}")
        pos += 1
        while pos < len(line) and line[pos].isspace():
            pos += 1

        if pos < len(line) and line[pos] in "'\"":
            quote = line[pos]
            pos += 1
            value_chars = []
            if quote == "'":
                end = line.find("'", pos)
                if end == -1:
                    raise ValueError(f"malformed line {line_number}")
                value = line[pos:end]
                pos = end + 1
            else:
                while pos < len(line) and line[pos] != '"':
                    if line[pos] == "\\":
                        if pos + 1 >= len(line):
                            raise ValueError(f"malformed line {line_number}")
                        escape = line[pos:pos + 2]
                        if escape not in escapes:
                            raise ValueError(f"malformed line {line_number}")
                        value_chars.append(escapes[escape])
                        pos += 2
                    else:
                        value_chars.append(line[pos])
                        pos += 1
                if pos >= len(line):
                    raise ValueError(f"malformed line {line_number}")
                value = "".join(value_chars)
                pos += 1
            while pos < len(line) and line[pos].isspace():
                pos += 1
            if pos < len(line) and line[pos] != "#":
                raise ValueError(f"malformed line {line_number}")
        else:
            value_text = line[pos:]
            if value_text.startswith("#"):
                value_text = ""
            else:
                comment = re.search(r"\s+#", value_text)
                if comment:
                    value_text = value_text[:comment.start()]
            value = value_text.strip()

        result[key] = value
    return result
