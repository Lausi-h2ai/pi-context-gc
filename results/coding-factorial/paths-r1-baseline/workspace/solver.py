import re


def normalize_members(paths):
    normalized = []
    seen = set()

    for path in paths:
        path = path.replace("\\", "/")
        if "\0" in path or path.startswith("/") or re.match(r"^[A-Za-z]:", path):
            raise ValueError(f"invalid archive member path: {path!r}")

        parts = []
        for segment in path.split("/"):
            if segment in ("", "."):
                continue
            if segment == "..":
                if not parts:
                    raise ValueError(f"archive member path escapes root: {path!r}")
                parts.pop()
            else:
                parts.append(segment)

        result = "/".join(parts)
        if not result:
            raise ValueError(f"archive member path normalizes to empty: {path!r}")
        if result not in seen:
            seen.add(result)
            normalized.append(result)

    return normalized
