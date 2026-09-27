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

        parts = []
        for segment in path.split("/"):
            if segment == "" or segment == ".":
                continue
            if segment == "..":
                if not parts:
                    raise ValueError("path escapes root")
                parts.pop()
            else:
                parts.append(segment)

        member = "/".join(parts)
        if not member:
            raise ValueError("path normalizes to empty")
        if member not in seen:
            seen.add(member)
            normalized.append(member)

    return normalized
