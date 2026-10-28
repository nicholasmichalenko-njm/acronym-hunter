"""Makes Narrow_Margins.pdf (2.57.0 test sample): body text close to the top and bottom edges of the page (kept), a
header standing apart, page numbers and a long legend repeated at the foot of each page (headers and footers)."""
import os


def page(lines):
    ops = ["BT /F1 11 Tf"]
    for x, y, t in lines:
        t = t.replace("(", "\\(").replace(")", "\\)")
        ops.append(f"1 0 0 1 {x} {y} Tm ({t}) Tj")
    ops.append("ET")
    return "\n".join(ops).encode()


LEGEND = "Use or disclosure of data contained on this page is subject to the restriction on the title page of this proposal."
p1 = [(40, 762, "L.9 Narrow Margins"), (40, 748, "The Offeror shall describe the approach on a page with")]
body = ["narrow margins so that body text sits close to the top.", "The Offeror shall provide a schedule.",
        "Each volume shall be separately bound."] + [f"Filler sentence number {i + 1} describes the work in plain words." for i in range(41)]
y = 734
for t in body:
    p1.append((40, y, t))
    y -= 15.5
p1 += [(40, y, "The last line of the page sits in the bottom margin and"), (40, 26, LEGEND), (300, 12, "Page 1")]
p2 = [(220, 770, "Company Confidential"), (40, 736, "continues onto the second page past the footer and header."),
      (40, 712, "L.10 Second Page"), (40, 700, "The Offeror shall address the second page requirement."),
      (40, 684, "This line continues the second page text normally."), (40, 60, "The final body sentence sits low on the page."),
      (40, 30, LEGEND), (300, 14, "Page 2")]
streams = [page(p1), page(p2)]
objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R 5 0 R] /Count 2 >>"]
for k, st in enumerate(streams):
    objs.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 7 0 R >> >> /Contents %d 0 R >>" % (4 + 2 * k))
    objs.append(b"<< /Length %d >>\nstream\n" % len(st) + st + b"\nendstream")
objs.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
out, offs = b"%PDF-1.4\n", []
for i, o in enumerate(objs, 1):
    offs.append(len(out))
    out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
x = len(out)
out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "Narrow_Margins.pdf"), "wb") as f:
    f.write(out)
