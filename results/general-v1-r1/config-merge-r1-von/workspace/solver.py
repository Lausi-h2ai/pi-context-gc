from copy import deepcopy


def merge_settings(base, overlays):
    result = deepcopy(base)

    for overlay in overlays:
        for key, value in overlay.items():
            if value is None:
                result.pop(key, None)
            elif isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = merge_settings(result[key], [value])
            else:
                result[key] = deepcopy(value)

    return result
