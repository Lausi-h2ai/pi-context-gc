def paginate_records(records, after=None, limit=20):
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100")

    if not isinstance(records, list):
        raise ValueError("records must be a list")

    ids = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be a dictionary")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("each record must have a nonempty string id")
        if record_id in ids:
            raise ValueError("record ids must be unique")
        ids.add(record_id)

    if after is not None and (not isinstance(after, str) or after not in ids):
        raise ValueError("after must be None or an id present in records")

    start = 0
    if after is not None:
        start = next(index + 1 for index, record in enumerate(records) if record["id"] == after)

    items = records[start:start + limit]
    next_after = items[-1]["id"] if start + len(items) < len(records) else None
    return {"items": items, "next_after": next_after}
