"""A small JSON Schema check for the tests (type, enum, minimum, required, properties, items): enough for the effort data's
schema, with no package to ship (4.9.0). Not a test: the runner leaves files starting with _ alone."""
_T = {"string": str, "boolean": bool, "object": dict, "array": list, "null": type(None)}


def _is(v, t):
    if t == "integer":
        return isinstance(v, int) and not isinstance(v, bool)
    if t == "number":
        return isinstance(v, (int, float)) and not isinstance(v, bool)
    return isinstance(v, _T[t])


def errors(v, s, at="$"):
    out = []
    t = s.get("type")
    if t is not None and not any(_is(v, x) for x in (t if isinstance(t, list) else [t])):
        return [f"{at}: {type(v).__name__} is not {t}"]
    if "enum" in s and v not in s["enum"]:
        out.append(f"{at}: {v!r} not in {s['enum']}")
    if "minimum" in s and isinstance(v, (int, float)) and v < s["minimum"]:
        out.append(f"{at}: {v} below {s['minimum']}")
    if isinstance(v, dict):
        for k in s.get("required", []):
            if k not in v:
                out.append(f"{at}: {k} missing")
        for k, sub in (s.get("properties") or {}).items():
            if k in v:
                out += errors(v[k], sub, f"{at}.{k}")
    if isinstance(v, list) and "items" in s:
        for i, x in enumerate(v):
            out += errors(x, s["items"], f"{at}[{i}]")
    return out
