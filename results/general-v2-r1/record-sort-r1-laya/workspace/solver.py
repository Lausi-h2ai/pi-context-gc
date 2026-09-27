def sort_records(records, keys):
    """Return records sorted stably by the requested fields."""
    if not isinstance(keys, list) or not keys or any(
        not isinstance(key, str)
        or not key
        or (key.startswith("-") and len(key) == 1)
        for key in keys
    ):
        raise ValueError("keys must be a nonempty list of nonempty field names")

    parsed_keys = [
        (key[1:] if key.startswith("-") else key, key.startswith("-"))
        for key in keys
    ]

    # Validate values per field before sorting so invalid data raises ValueError,
    # rather than leaking a comparison TypeError from the sorting operation.
    for field, _descending in parsed_keys:
        non_missing = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError("records must contain dictionaries")
            value = record.get(field)
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                    raise ValueError("field values must be JSON scalars")
                non_missing.append(value)
        if non_missing:
            first = non_missing[0]
            if any(
                (isinstance(first, str) != isinstance(value, str))
                for value in non_missing
            ):
                raise ValueError("field values must have a common comparable type")

    def compare(left, right):
        for field, descending in parsed_keys:
            a, b = left.get(field), right.get(field)
            # Missing and None share a bucket, always after concrete values.
            a_missing, b_missing = a is None, b is None
            if a_missing or b_missing:
                if a_missing != b_missing:
                    return 1 if a_missing else -1
                continue
            if a != b:
                result = -1 if a < b else 1
                return -result if descending else result
        return 0

    from functools import cmp_to_key
    try:
        return sorted(records, key=cmp_to_key(compare))
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("field values must be mutually comparable") from exc
