def sort_records(records, keys):
    if not keys:
        return list(records)
    return sorted(records, key=lambda row: row.get(keys[0]))
