def parse_env(text, defaults=None):
    result = {} if defaults is None else dict(defaults)
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith('#'):
            key, value = line.split('=', 1)
            result[key.strip()] = value.strip().strip('"\'')
    return result
