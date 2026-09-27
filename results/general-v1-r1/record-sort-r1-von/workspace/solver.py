def sort_records(records, keys):
    """Return records stably sorted by the requested fields."""
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a nonempty list of field names")

    parsed_keys = []
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("each key must be a nonempty string")
        descending = key.startswith("-")
        field = key[1:] if descending else key
        if not field:
            raise ValueError("a descending key must name a field")
        parsed_keys.append((field, descending))

    result = list(records)
    for field, descending in reversed(parsed_keys):
        present = []
        missing = []
        value_types = set()
        for record in result:
            value = record.get(field)
            if value is None:
                missing.append(record)
                continue
            if isinstance(value, bool) or not isinstance(value, (str, int, float)):
                raise ValueError("field values must be JSON strings or numbers")
            value_types.add("number" if isinstance(value, (int, float)) else str)
            present.append(record)

        if len(value_types) > 1:
            raise ValueError("mixed field value types are not supported")
        try:
            present.sort(key=lambda record: record.get(field), reverse=descending)
        except (TypeError, ValueError) as exc:
            raise ValueError("field values must be mutually comparable") from exc
        result = present + missing

    return result
