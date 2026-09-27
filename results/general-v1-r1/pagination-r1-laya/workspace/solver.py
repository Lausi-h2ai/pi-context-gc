def paginate_records(records, after=None, limit=20):
    if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer from 1 through 100")

    if not isinstance(records, list):
        raise ValueError("records must be a list")

    seen = set()
    cursor_index = None
    for index, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError("each record must be a dictionary")
        record_id = record.get('id')
        if not isinstance(record_id, str) or not record_id:
            raise ValueError("each record must have a nonempty string id")
        if record_id in seen:
            raise ValueError("record ids must be unique")
        seen.add(record_id)
        if record_id == after:
            cursor_index = index

    if after is not None and (not isinstance(after, str) or cursor_index is None):
        raise ValueError("after must be None or an id present in records")

    start = 0 if after is None else cursor_index + 1
    items = records[start:start + limit]
    next_after = items[-1]['id'] if start + len(items) < len(records) else None
    return {'items': items, 'next_after': next_after}
