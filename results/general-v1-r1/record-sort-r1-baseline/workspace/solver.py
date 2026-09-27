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
            raise ValueError("field name must not be empty")
        parsed_keys.append((field, descending))

    rows = list(records)
    # Validate each field globally before sorting so comparison errors do not
    # depend on which comparisons Python's sorting algorithm happens to make.
    for field, _ in parsed_keys:
        value_type = None
        for row in rows:
            if field not in row:
                continue
            value = row[field]
            if value is None:
                continue
            if not isinstance(value, (str, int, float)) or isinstance(value, bool):
                raise ValueError("field values must be JSON scalars")
            # int and float can be compared directly; strings cannot be mixed
            # with numeric values.
            current_type = str if isinstance(value, str) else (int, float)
            if value_type is None:
                value_type = current_type
            elif value_type != current_type:
                raise ValueError("field values must have a common type")

    # Stable sorts from least to most significant key implement lexicographic
    # multi-key ordering while keeping null/missing values last in both orders.
    result = rows
    for field, descending in reversed(parsed_keys):
        present = [row for row in result if field in row and row[field] is not None]
        absent = [row for row in result if field not in row or row[field] is None]
        present.sort(key=lambda row: row[field], reverse=descending)
        result = present + absent
    return result
