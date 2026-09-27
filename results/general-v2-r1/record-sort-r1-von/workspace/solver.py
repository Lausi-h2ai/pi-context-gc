def sort_records(records, keys):
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a nonempty list")

    parsed = []
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("each key must be a nonempty string")
        descending = key.startswith("-")
        field = key[1:] if descending else key
        if not field:
            raise ValueError("field name must not be empty")
        parsed.append((field, descending))

    result = list(records)
    # Python's stable sort permits lexicographic multi-key sorting by sorting
    # from the least significant field to the most significant field.
    for field, descending in reversed(parsed):
        present_values = []
        for row in result:
            value = row.get(field)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ValueError("field values must be JSON scalars")
            present_values.append(value)

        if present_values:
            first_type = type(present_values[0])
            # Integers and floats form one mutually comparable numeric type.
            is_numeric = first_type in (int, float)
            if any(
                not (is_numeric and type(value) in (int, float))
                and type(value) is not first_type
                for value in present_values
            ):
                raise ValueError("field values must have a common comparable type")

        present = [row for row in result if row.get(field) is not None]
        missing = [row for row in result if row.get(field) is None]
        present.sort(key=lambda row: row[field], reverse=descending)
        result = present + missing

    return result
