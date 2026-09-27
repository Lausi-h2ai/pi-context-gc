def decode_records(text):
    """Decode semicolon-separated key/value records with backslash escapes."""
    records = []
    key_chars = []
    value_chars = []
    in_value = False
    record_nonempty = False
    escaped = False

    def finish_record():
        nonlocal key_chars, value_chars, in_value, record_nonempty
        if record_nonempty:
            if not in_value:
                raise ValueError("record is missing an unescaped equals sign")
            key = "".join(key_chars)
            if not key:
                raise ValueError("record key must not be empty")
            records.append([key, "".join(value_chars)])
        key_chars = []
        value_chars = []
        in_value = False
        record_nonempty = False

    for char in text:
        if escaped:
            if char not in "\\;=":
                raise ValueError("invalid escape sequence")
            (value_chars if in_value else key_chars).append(char)
            record_nonempty = True
            escaped = False
        elif char == "\\":
            escaped = True
            record_nonempty = True
        elif char == ";":
            finish_record()
        elif char == "=" and not in_value:
            in_value = True
            record_nonempty = True
        else:
            (value_chars if in_value else key_chars).append(char)
            record_nonempty = True

    if escaped:
        raise ValueError("trailing backslash")
    finish_record()
    return records
