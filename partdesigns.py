"""Part designs (3.26.0): one part of the document (cover, front matter, response, appendices, back cover) kept as a
design: where it starts and how its pages are numbered, its header and footer layout, a kept header or footer design,
its caption rules and its cover or back cover page. Kept in the template library (Part designs) and used on any part
of any standard. Rules only; nothing leaves the PC."""
import copy


def part_of(work, key):
    return next((p for p in ((work.get("pagination") or {}).get("parts") or []) if p.get("key") == key), None)


def design_of(work, key):
    """What a part design keeps: its numbering, header and footer layout, kept designs, captions and page."""
    part = copy.deepcopy(part_of(work, key) or {})
    return {"part": key, "pagination": {k: v for k, v in part.items() if k not in ("key", "name")},
            "hf_layout": copy.deepcopy((work.get("hf_layouts") or {}).get(key) or {}),
            "hf_design": copy.deepcopy((work.get("hf_designs") or {}).get(key) or {}),
            "captions": [copy.deepcopy(c) for c in work.get("captions") or [] if c.get("part") == key],
            "page_file": (work.get("page_parts") or {}).get(key, ""),
            "contents": copy.deepcopy(((work.get("section_contents") or {}).get(key)) or [])}        # 3.45.0


def apply_design(work, v, key, page_file=None):
    """A part design into a standard, on the part key (the part it was saved from or another)."""
    part = part_of(work, key)
    if part is not None:
        keep = {"key": part["key"], "name": part.get("name", key)}
        part.clear(); part.update(keep); part.update(copy.deepcopy(v.get("pagination") or {}))
    if v.get("hf_layout"):
        work.setdefault("hf_layouts", {})[key] = copy.deepcopy(v["hf_layout"])
    if v.get("hf_design"):
        work.setdefault("hf_designs", {})[key] = copy.deepcopy(v["hf_design"])
    else:
        (work.get("hf_designs") or {}).pop(key, None)
    if key in ("body", "appendix") and v.get("captions"):
        work["captions"] = [c for c in work.get("captions") or [] if c.get("part") != key] + \
                           [dict(c, part=key) for c in v["captions"]]
    if "contents" in v:                                  # 3.45.0: the section's components come with it
        import sectioncontents as SC
        SC.set_items(work, key, copy.deepcopy(v.get("contents") or []))
    if key in ("cover", "backer") and page_file:
        work.setdefault("page_parts", {})[key] = page_file
    return f"the {key} section design"


