from copy import deepcopy


def merge_settings(base, overlays):
    result = deepcopy(base)

    def apply_overlay(target, overlay):
        for key, value in overlay.items():
            if value is None:
                target.pop(key, None)
            elif isinstance(target.get(key), dict) and isinstance(value, dict):
                apply_overlay(target[key], value)
            else:
                target[key] = deepcopy(value)

    for overlay in overlays:
        apply_overlay(result, overlay)

    return result
