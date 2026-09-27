def paginate_records(records, after=None, limit=20):
    return {'items': records[:limit], 'next_after': records[limit - 1]['id'] if len(records) > limit else None}
