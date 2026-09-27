def normalize_members(paths):
    return [p.replace("\\", "/").lstrip("/") for p in paths]
