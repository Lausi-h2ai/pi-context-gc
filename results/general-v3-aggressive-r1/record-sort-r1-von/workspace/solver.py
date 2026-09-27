def sort_records(records, keys):
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a nonempty list")

    parsed_keys = []
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("keys must contain nonempty strings")
        descending = key.startswith("-")
        field = key[1:] if descending else key
        if not field:
            raise ValueError("field name must not be empty")
        parsed_keys.append((field, descending))

    rows = list(records)

    # Validate each field independently before sorting so incompatible values
    # raise ValueError consistently, regardless of the input order.
    for field, _ in parsed_keys:
        seen_type = None
        for row in rows:
            value = row.get(field)
            if value is None:
                continue
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                raise ValueError("field values must be JSON scalars")
            value_type = type(value)
            if seen_type is None:
                seen_type = value_type
            elif value_type is not seen_type:
                raise ValueError("field values must have a common type")

    # Stable sorts from least to most significant key allow each direction to
    # be applied independently while keeping None/missing values last.
    for field, descending in reversed(parsed_keys):
        present = [row for row in rows if row.get(field) is not None]
        missing = [row for row in rows if row.get(field) is None]
        present.sort(key=lambda row: row[field], reverse=descending)
        rows = present + missing

    return rows
