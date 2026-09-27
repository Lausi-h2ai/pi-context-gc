def decode_records(text):
    records = []
    key_chars = []
    value_chars = []
    in_value = False
    record_started = False
    escaped = False

    def finish_record():
        nonlocal key_chars, value_chars, in_value, record_started
        if record_started:
            if not in_value:
                raise ValueError("record has no unescaped equals sign")
            key = "".join(key_chars)
            if not key:
                raise ValueError("record key must be nonempty")
            records.append([key, "".join(value_chars)])
        key_chars = []
        value_chars = []
        in_value = False
        record_started = False

    for char in text:
        if escaped:
            if char not in "\\;=":
                raise ValueError("invalid escape")
            (value_chars if in_value else key_chars).append(char)
            record_started = True
            escaped = False
        elif char == "\\":
            escaped = True
            record_started = True
        elif char == ";":
            finish_record()
        elif char == "=" and not in_value:
            in_value = True
            record_started = True
        else:
            (value_chars if in_value else key_chars).append(char)
            record_started = True

    if escaped:
        raise ValueError("trailing backslash")
    finish_record()
    return records
