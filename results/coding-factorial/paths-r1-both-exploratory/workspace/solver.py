def normalize_members(paths):
    normalized = []
    seen = set()

    for path in paths:
        path = path.replace("\\", "/")
        if "\0" in path or path.startswith("/"):
            raise ValueError("invalid archive member path")
        if len(path) >= 2 and path[0].isascii() and path[0].isalpha() and path[1] == ":":
            raise ValueError("drive-prefixed archive member path")

        parts = []
        for segment in path.split("/"):
            if segment == "" or segment == ".":
                continue
            if segment == "..":
                if not parts:
                    raise ValueError("archive member path escapes root")
                parts.pop()
            else:
                parts.append(segment)

        member = "/".join(parts)
        if not member:
            raise ValueError("archive member path normalizes to empty")
        if member not in seen:
            seen.add(member)
            normalized.append(member)

    return normalized
