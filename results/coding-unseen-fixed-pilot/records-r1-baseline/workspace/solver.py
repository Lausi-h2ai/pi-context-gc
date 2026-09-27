def decode_records(text):
    records = []
    key = []
    value = []
    in_value = False
    record_started = False

    def finish_record():
        nonlocal key, value, in_value, record_started
        if record_started:
            if not in_value:
                raise ValueError("record is missing an unescaped '='")
            decoded_key = "".join(key)
            if not decoded_key:
                raise ValueError("record key must not be empty")
            records.append([decoded_key, "".join(value)])
        key = []
        value = []
        in_value = False
        record_started = False

    i = 0
    while i < len(text):
        char = text[i]
        if char == "\\\\":
            if i + 1 >= len(text):
                raise ValueError("trailing backslash")
            escaped = text[i + 1]
            if escaped not in "\\\\;=":
                raise ValueError(f"invalid escape: \\\\{escaped}")
            (value if in_value else key).append(escaped)
            record_started = True
            i += 2
            continue
        if char == ";":
            finish_record()
        elif char == "=" and not in_value:
            in_value = True
            record_started = True
        else:
            (value if in_value else key).append(char)
            record_started = True
        i += 1

    finish_record()
    return records
