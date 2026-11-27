"""What a document is for, its Purpose (4.25.2, split from docversions; 4.83.0 in decision 216's words): the words a person reads for a document's saved role, the
ways it goes back to the customer, and whose it is. Standard library only."""

# 4.25.2 (Documents board 2026-11-12, step B; answer 4): what a person read was Used for. The saved words stay (matrix,
# context, reference, not_needed), so every effort reads as before; context and reference both read Reference.
# 4.83.0 (step D3; UX decisions 183, 215, 216, 251): what a person reads is Purpose, in decision 216's words. The saved
# keys stay (matrix, context, reference, not_needed; returns redline, fill), so every effort reads as before; "submit"
# (File to submit) is new. Effort outline and Effort template are not offered yet: no page reads them from Documents.
ROLES = (("matrix", "Customer document"), ("context", "Reference"), ("reference", "Reference"), ("not_needed", "No mark"))
ROLE_NAMES = dict(ROLES)
USES = (("matrix", "Customer document"), ("reference", "Reference"), ("not_needed", "No mark"))    # the choices offered
RETURNS = (("fill", "Form to fill in"), ("submit", "File to submit"), ("redline", "Redline to return"))   # a document may carry these as well
RETURN_NAMES = dict(RETURNS)
ADD_USES = USES[:2] + RETURNS                # 4.83.0: the Purpose list of Documents > Add (every file has a purpose, 256)
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
        """4.25.2: the ways the document goes back to the customer: [] or some of "fill", "submit", "redline"."""
        return [k for k, _n in RETURNS if k in (d.get("returns") or [])]

    def marks_of(self, d):
        """What the document is used for, in words: For the shred or Reference (none when left out), then how it is
        returned."""
        r = use_key(self.role_of(d))
        back = [RETURN_NAMES[k] for k in self.returns_of(d)]
        if back and r == "reference":                 # 4.83.0: a file that goes back is kept as Reference underneath (4.61.0);
            return back                               # its purpose reads as what was given, not "Reference, Form to fill in"
        return ([ROLE_NAMES[r]] if r != "not_needed" else []) + back

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
