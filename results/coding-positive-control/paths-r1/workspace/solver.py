import re


def normalize_members(paths):
    normalized = []
    seen = set()

    for path in paths:
        if "\0" in path:
            raise ValueError("archive member contains a NUL character")

        # Normalize separators before checking rooted paths and components.
        path = path.replace("\\", "/")
        if path.startswith("/"):
            raise ValueError("archive member must be relative")
        if re.match(r"^[A-Za-z]:", path):
            raise ValueError("archive member must not have a drive prefix")

        components = []
        for component in path.split("/"):
            if component in ("", "."):
                continue
            if component == "..":
                if not components:
                    raise ValueError("archive member escapes root")
                components.pop()
            else:
                components.append(component)

        if not components:
            raise ValueError("archive member normalizes to an empty path")

        member = "/".join(components)
        if member not in seen:
            seen.add(member)
            normalized.append(member)

    return normalized
