import re


def normalize_members(paths):
    normalized = []
    seen = set()

    for path in paths:
        if "\x00" in path:
            raise ValueError("path contains NUL")

        path = path.replace("\\", "/")
        if path.startswith("/") or re.match(r"^[A-Za-z]:", path):
            raise ValueError("absolute paths are not allowed")

        components = []
        for component in path.split("/"):
            if component in ("", "."):
                continue
            if component == "..":
                if not components:
                    raise ValueError("path escapes root")
                components.pop()
            else:
                components.append(component)

        if not components:
            raise ValueError("path normalizes to empty")

        member = "/".join(components)
        if member not in seen:
            seen.add(member)
            normalized.append(member)

    return normalized
