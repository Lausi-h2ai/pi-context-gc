def normalize_members(paths):
    """Normalize archive member paths and reject unsafe or empty members."""
    normalized = []
    seen = set()

    for path in paths:
        if "\x00" in path:
            raise ValueError("NUL character in archive member path")

        # Normalize separators before checking absolute and drive-prefixed forms.
        path = path.replace("\\", "/")
        if path.startswith("/"):
            raise ValueError("absolute archive member path")
        if len(path) >= 2 and path[0].isascii() and path[0].isalpha() and path[1] == ":":
            raise ValueError("drive-prefixed archive member path")

        parts = []
        for part in path.split("/"):
            if part == "" or part == ".":
                continue
            if part == "..":
                if not parts:
                    raise ValueError("archive member path escapes root")
                parts.pop()
            else:
                parts.append(part)

        member = "/".join(parts)
        if not member:
            raise ValueError("archive member path normalizes to empty")
        if member not in seen:
            seen.add(member)
            normalized.append(member)

    return normalized
