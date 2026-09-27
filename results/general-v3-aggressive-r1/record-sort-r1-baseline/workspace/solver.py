def sort_records(records, keys):
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a nonempty list")

    parsed_keys = []
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("each key must be a nonempty string")
        descending = key.startswith("-")
        field = key[1:] if descending else key
        if not field:
            raise ValueError("field name must be nonempty")
        parsed_keys.append((field, descending))

    rows = list(records)
    # Validate scalar values and comparable types for each requested field.
    for field, _ in parsed_keys:
        observed_type = None
        for row in rows:
            value = row.get(field)
            if value is None:
                continue
            if isinstance(value, (dict, list, tuple, set)):
                raise ValueError("field values must be JSON scalars")
            if isinstance(value, bool):
                value_type = bool
            elif isinstance(value, (int, float)):
                value_type = (int, float)
            elif isinstance(value, str):
                value_type = str
            else:
                raise ValueError("field values must be JSON scalars")
            if observed_type is None:
                observed_type = value_type
            elif value_type is not observed_type:
                raise ValueError("field values must have a common type")

    # Sort from the least significant key to the most significant. Sorting
    # non-missing values separately keeps None/missing last in either direction.
    for field, descending in reversed(parsed_keys):
        present = [row for row in rows if row.get(field) is not None]
        absent = [row for row in rows if row.get(field) is None]
        present.sort(key=lambda row: row[field], reverse=descending)
        rows = present + absent
    return rows
