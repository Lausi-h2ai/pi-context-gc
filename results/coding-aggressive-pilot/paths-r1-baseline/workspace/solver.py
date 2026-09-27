def normalize_members(paths):
    normalized = []
    seen = set()

    for path in paths:
        if "\x00" in path:
            raise ValueError("path contains a NUL character")

        path = path.replace("\\", "/")
        if path.startswith("/"):
            raise ValueError("absolute paths are not allowed")
        if len(path) >= 2 and path[0].isascii() and path[0].isalpha() and path[1] == ":":
            raise ValueError("drive-prefixed paths are not allowed")

        segments = []
        for segment in path.split("/"):
            if segment == "" or segment == ".":
                continue
            if segment == "..":
                if not segments:
                    raise ValueError("path escapes the relative root")
                segments.pop()
            else:
                segments.append(segment)

        result = "/".join(segments)
        if not result:
            raise ValueError("path normalizes to empty")
        if result not in seen:
            seen.add(result)
            normalized.append(result)

    return normalized
