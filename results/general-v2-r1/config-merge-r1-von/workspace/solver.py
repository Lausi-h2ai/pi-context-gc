def merge_settings(base, overlays):
    def copy_value(value):
        if isinstance(value, dict):
            return {key: copy_value(item) for key, item in value.items()}
        if isinstance(value, list):
            return [copy_value(item) for item in value]
        return value

    def merge_dict(current, overlay):
        result = {key: copy_value(value) for key, value in current.items()}
        for key, value in overlay.items():
            if value is None:
                result.pop(key, None)
            elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge_dict(result[key], value)
            else:
                result[key] = copy_value(value)
        return result

    result = copy_value(base)
    for overlay in overlays:
        result = merge_dict(result, overlay)
    return result
