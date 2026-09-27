def paginate_records(records, after=None, limit=20):
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100")

    ids = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise ValueError("each record must be a dictionary")
        record_id = record.get("id")
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("each record must have a nonempty string id")
        if record_id in seen:
            raise ValueError("record ids must be unique")
        seen.add(record_id)
        ids.append(record_id)

    if after is not None:
        if not isinstance(after, str) or after not in seen:
            raise ValueError("after must be None or an id present in records")
        start = ids.index(after) + 1
    else:
        start = 0

    page = records[start:start + limit]
    has_more = start + len(page) < len(records)
    next_after = page[-1]["id"] if has_more else None
    return {"items": page, "next_after": next_after}
