from functools import cmp_to_key


def sort_records(records, keys):
    """Return records in stable lexicographic order without modifying the input."""
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
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("records must contain dictionaries")

    # Validate values across all rows before sorting, including values masked by
    # earlier sort keys.
    for field, _ in parsed_keys:
        observed_type = None
        for row in rows:
            value = row.get(field)
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ValueError("field values must be JSON scalars")
            value_type = type(value)
            if observed_type is None:
                observed_type = value_type
            elif value_type is not observed_type:
                raise ValueError("field values must have a common type")

    def compare(left, right):
        for field, descending in parsed_keys:
            a = left.get(field)
            b = right.get(field)
            a_missing = a is None
            b_missing = b is None
            if a_missing or b_missing:
                if a_missing != b_missing:
                    return 1 if a_missing else -1
                continue
            if a == b:
                continue
            result = -1 if a < b else 1
            if descending:
                result = -result
            return result
        return 0

    return sorted(rows, key=cmp_to_key(compare))
