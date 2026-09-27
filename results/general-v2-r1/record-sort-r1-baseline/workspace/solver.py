from functools import cmp_to_key
import math


def sort_records(records, keys):
    if not isinstance(keys, list) or not keys:
        raise ValueError("keys must be a nonempty list of nonempty strings")

    parsed_keys = []
    for key in keys:
        if not isinstance(key, str) or not key:
            raise ValueError("keys must be a nonempty list of nonempty strings")
        descending = key.startswith("-")
        field = key[1:] if descending else key
        if not field:
            raise ValueError("field name must not be empty")
        parsed_keys.append((field, descending))

    rows = list(records)
    # Validate all values for each field before comparing rows.
    for field, _ in parsed_keys:
        kind = None
        for row in rows:
            value = row.get(field)
            if field not in row or value is None:
                continue
            if isinstance(value, bool):
                value_kind = bool
            elif type(value) in (int, float):
                value_kind = (int, float)
            elif type(value) is str:
                value_kind = str
                value_kind = str
            else:
                raise ValueError("field values must be JSON scalars")
            if kind is None:
                kind = value_kind
            elif kind != value_kind:
                raise ValueError("non-None values for a field must have a common type")

    def compare(left, right):
        for field, descending in parsed_keys:
            a = left.get(field)
            b = right.get(field)
            a_missing = field not in left or a is None
            b_missing = field not in right or b is None
            if a_missing or b_missing:
                if a_missing != b_missing:
                    return 1 if a_missing else -1
                continue
            if (isinstance(a, float) and math.isnan(a)) or (isinstance(b, float) and math.isnan(b)):
                # NaN is a JSON-number edge case; treat equal NaNs as ties and
                # place NaN consistently relative to other numbers.
                if math.isnan(a) and math.isnan(b):
                    result = 0
                else:
                    result = 1 if math.isnan(a) else -1
            else:
                result = (a > b) - (a < b)
            if result:
                return -result if descending else result
        return 0

    return sorted(rows, key=cmp_to_key(compare))
