def decode_records(text):
    records = []
    key = []
    value = []
    in_value = False
    record_nonempty = False
    i = 0

    def finish_record():
        if not record_nonempty:
            return
        if not in_value:
            raise ValueError("record is missing '='")
        decoded_key = "".join(key)
        if not decoded_key:
            raise ValueError("record key must not be empty")
        records.append([decoded_key, "".join(value)])

    while i < len(text):
        char = text[i]
        if char == "\\":
            if i + 1 >= len(text) or text[i + 1] not in "\\;=":
                raise ValueError("invalid escape")
            (value if in_value else key).append(text[i + 1])
            record_nonempty = True
            i += 2
            continue
        if char == ";":
            finish_record()
            key, value = [], []
            in_value = False
            record_nonempty = False
        elif char == "=" and not in_value:
            in_value = True
            record_nonempty = True
        else:
            (value if in_value else key).append(char)
            record_nonempty = True
        i += 1

    finish_record()
    return records
