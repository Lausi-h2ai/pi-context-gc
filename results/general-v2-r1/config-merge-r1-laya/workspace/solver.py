def merge_settings(base, overlays):
    def copy_value(value):
        if isinstance(value, dict):
            return {key: copy_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [copy_value(item) for item in value]
        return value

    result = copy_value(base)
    for overlay in overlays:
        for key, value in overlay.items():
            if value is None:
                result.pop(key, None)
            elif isinstance(result.get(key), dict) and isinstance(value, dict):
                result[key] = merge_settings(result[key], [value])
            else:
                result[key] = copy_value(value)
    return result
