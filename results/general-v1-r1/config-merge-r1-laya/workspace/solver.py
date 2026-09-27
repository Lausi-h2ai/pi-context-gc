from copy import deepcopy


def merge_settings(base, overlays):
    result = deepcopy(base)

    def apply(target, overlay):
        for key, value in overlay.items():
            if value is None:
                target.pop(key, None)
            elif key in target and isinstance(target[key], dict) and isinstance(value, dict):
                apply(target[key], value)
            else:
                target[key] = deepcopy(value)

    for overlay in overlays:
        apply(result, overlay)
    return result
