import re


def parse_env(text, defaults=None):
    if defaults is not None and not isinstance(defaults, dict):
        raise TypeError('defaults must be a dictionary')
    result = {} if defaults is None else dict(defaults)
    key_pattern = re.compile(r'[A-Za-z_][A-Za-z0-9_]*')
    escapes = {'\\': '\\', '"': '"', 'n': '\n', 'r': '\r', 't': '\t', '#': '#'}

    for line_number, line in enumerate(text.splitlines(), 1):
        source = line.lstrip()
        if not source or source.startswith('#'):
            continue
        if source.startswith('export') and len(source) > 6 and source[6].isspace():
            source = source[6:].lstrip()

        match = key_pattern.match(source)
        if match is None:
            raise ValueError(f'Invalid environment definition on line {line_number}')
        key = match.group()
        index = match.end()
        while index < len(source) and source[index].isspace():
            index += 1
        if index >= len(source) or source[index] != '=':
            raise ValueError(f'Invalid environment definition on line {line_number}')
        index += 1
        while index < len(source) and source[index].isspace():
            index += 1

        if index < len(source) and source[index] in ("'", '"'):
            quote = source[index]
            index += 1
            value_chars = []
            while index < len(source) and source[index] != quote:
                char = source[index]
                if quote == '"' and char == '\\':
                    index += 1
                    if index >= len(source) or source[index] not in escapes:
                        raise ValueError(f'Invalid escape on line {line_number}')
                    value_chars.append(escapes[source[index]])
                else:
                    value_chars.append(char)
                index += 1
            if index >= len(source):
                raise ValueError(f'Unterminated quote on line {line_number}')
            value = ''.join(value_chars)
            index += 1
            remainder = source[index:].lstrip()
            if remainder and not remainder.startswith('#'):
                raise ValueError(f'Unexpected text after quoted value on line {line_number}')
        else:
            raw_value = source[index:]
            if raw_value.startswith('#'):
                value = ''
            else:
                comment = re.search(r'\s+#', raw_value)
                if comment:
                    raw_value = raw_value[:comment.start()]
                value = raw_value.strip()
        result[key] = value
    return result
