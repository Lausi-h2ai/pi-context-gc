from copy import deepcopy


def merge_settings(base, overlays):
    def merge(current, overlay):
        result = deepcopy(current)
        for key, value in overlay.items():
            if value is None:
                result.pop(key, None)
            elif key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    result = deepcopy(base)
    for overlay in overlays:
        result = merge(result, overlay)
    return result
