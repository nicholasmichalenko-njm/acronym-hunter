"""What a document is used for (4.25.2, split from docversions): the words a person reads for a document's saved role, the
ways it goes back to the customer, and whose it is. Standard library only."""

# 4.25.2 (Documents board 2026-11-12, step B; answer 4): what a person reads is Used for. The saved words stay (matrix,
# context, reference, not_needed), so every effort reads as before; context and reference both read Reference.
ROLES = (("matrix", "For the shred"), ("context", "Reference"), ("reference", "Reference"), ("not_needed", "No mark"))
ROLE_NAMES = dict(ROLES)
USES = (("matrix", "For the shred"), ("reference", "Reference"), ("not_needed", "No mark"))        # the choices offered
RETURNS = (("redline", "Redlined Deliverable"), ("fill", "Filled-in Deliverable"))    # a document may carry these as well
RETURN_NAMES = dict(RETURNS)
SOURCE_NAMES = {"customer": "Customer", "bidders": "Customer (bidders library)", "qa": "Customer (Q&A)", "ours": "Internal",
                "graphics": "Internal (graphics)"}


def use_key(role):
    """The choice a saved role shows as: context is Reference."""
    return "reference" if role == "context" else role


def source_name(lib, category):
    """Customer or Internal, with what kind when the folder said so (folders took the place of Category)."""
    if category in SOURCE_NAMES:
        return SOURCE_NAMES[category]
    return "Internal (" + (lib.category_name(category) if lib is not None else str(category)) + ")"


class MarksMixin:
    def returns_of(self, d):
        """4.25.2: the ways the document goes back to the customer: [] or some of "redline", "fill"."""
        return [k for k, _n in RETURNS if k in (d.get("returns") or [])]

    def marks_of(self, d):
        """What the document is used for, in words: For the shred or Reference (none when left out), then how it is
        returned."""
        r = use_key(self.role_of(d))
        return ([ROLE_NAMES[r]] if r != "not_needed" else []) + [RETURN_NAMES[k] for k in self.returns_of(d)]

    def set_returns(self, doc_id, marks):
        d = self.doc(doc_id)
        if d is None:
            return False
        keep = [k for k, _n in RETURNS if k in (marks or [])]
        if keep:
            d["returns"] = keep
        else:
            d.pop("returns", None)
        self.save()
        return True
