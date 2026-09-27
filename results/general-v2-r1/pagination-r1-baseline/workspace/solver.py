def paginate_records(records, after=None, limit=20):
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100")

    ids = set()
    start = 0
    cursor_found = after is None
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("each record must be a dictionary")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("each record must have a nonempty string id")
        if record_id in ids:
            raise ValueError("record ids must be unique")
        ids.add(record_id)
        if after is not None and record_id == after:
            start = index + 1
            cursor_found = True

    if after is not None and (not isinstance(after, str) or not cursor_found):
        raise ValueError("after must be None or an id present in records")

    page = records[start:start + limit]
    next_after = page[-1]["id"] if start + len(page) < len(records) else None
    return {"items": page, "next_after": next_after}
