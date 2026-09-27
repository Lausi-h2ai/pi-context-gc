def merge_settings(base, overlays):
    """Return an independent recursive merge of base and left-to-right overlays."""

    def copy_value(value):
        if isinstance(value, dict):
            return {key: copy_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [copy_value(item) for item in value]
        return value

    def merge_into(target, source):
        for key, value in source.items():
            if value is None:
                target.pop(key, None)
            elif isinstance(value, dict) and isinstance(target.get(key), dict):
                merge_into(target[key], value)
            else:
                target[key] = copy_value(value)

    result = copy_value(base)
    for overlay in overlays:
        merge_into(result, overlay)
    return result
