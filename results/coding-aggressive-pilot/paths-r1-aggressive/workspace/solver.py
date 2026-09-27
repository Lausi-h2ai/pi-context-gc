import re


def normalize_members(paths):
    normalized = []
    seen = set()

    for path in paths:
        if "\0" in path:
            raise ValueError("path contains a NUL character")

        path = path.replace("\\", "/")
        if path.startswith("/") or re.match(r"[A-Za-z]:", path):
            raise ValueError("absolute paths and drive prefixes are not allowed")

        parts = []
        for segment in path.split("/"):
            if segment == "" or segment == ".":
                continue
            if segment == "..":
                if not parts:
                    raise ValueError("path escapes archive root")
                parts.pop()
            else:
                parts.append(segment)

        result = "/".join(parts)
        if not result:
            raise ValueError("path normalizes to empty")
        if result not in seen:
            seen.add(result)
            normalized.append(result)

    return normalized
