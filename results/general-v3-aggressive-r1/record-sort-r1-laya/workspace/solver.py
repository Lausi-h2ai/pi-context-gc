def sort_records(records, keys):
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a nonempty list of nonempty strings")

    parsed_keys = []
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("keys must be a nonempty list of nonempty strings")
        descending = key.startswith("-")
        field = key[1:] if descending else key
        if not field:
            raise ValueError("field name must not be empty")
        parsed_keys.append((field, descending))

    rows = list(records)

    # Validate each field's values before sorting, so incomparable or nested
    # values reliably raise ValueError regardless of which rows compare first.
    for field, _ in parsed_keys:
        values = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("records must contain dictionaries")
            value = row.get(field)
            if value is None:
                continue
            if isinstance(value, bool):
                value_type = bool
            elif isinstance(value, (int, float)):
                value_type = (int, float)
            elif isinstance(value, str):
                value_type = str
            else:
                raise ValueError("field values must be JSON scalars")
            values.append((value, value_type))

        categories = {value_type for _, value_type in values}
        if len(categories) > 1:
            raise ValueError("field values must have a common comparable type")

    # Stable sorts from least- to most-significant key allow each key to have
    # its own direction while keeping None and missing values last.
    for field, descending in reversed(parsed_keys):
        present = [row for row in rows if row.get(field) is not None]
        absent = [row for row in rows if row.get(field) is None]
        present.sort(key=lambda row: row[field], reverse=descending)
        rows = present + absent

    return rows
