"""Documents: packages as groups, and a document's versions under it (4.25.4; the Documents board 2026-11-12, step D).

Once the effort has an amendment, the list is in groups: As issued, each amendment in the order issued, then Internal.
A group's line names it and counts its documents. A document with more than one version shows its earlier versions on
lines under it (newest first); a click on one selects the document. With Find in use the groups are off, so the hits
read as one list. The package is set on the row: right-click > Package. Rules only; nothing leaves the PC."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

import diag
import docpackages as DP


def rows(page, docs):
    """[("group", key, name, n) | ("doc", d) | ("version", d, v)] in the order shown."""
    lib = page.lib
    out = []
    grouping = DP.has_groups(lib) and not page.search.text().strip()
    groups = DP.grouped(lib, docs) if grouping else [("", "", docs)]
    for k, n, mine in groups:
        if grouping:
            out.append(("group", k, n, len(mine)))
        for d in mine:
            out.append(("doc", d))
            vs = d.get("versions") or []
            for v in reversed(vs[:-1]):
                out.append(("version", d, v))
    return out


def fill(page, docs, item):
    from . import design as D
    from . import docfocus as DF
    t = page.table
    rs = rows(page, docs)
    t.clearSpans()
    t.setRowCount(len(rs))
    ncol = len(DF.COLUMNS)
    for r, row in enumerate(rs):
        if row[0] == "group":
            _k, name, n = row[1:]
            it = item(f"{name}   ·   {n} document" + ("" if n == 1 else "s"))
            f = it.font(); f.setWeight(QFont.DemiBold); it.setFont(f)
            it.setFlags(Qt.ItemIsEnabled)
            it.setBackground(D.color("surface2"))
            t.setItem(r, 0, it)
            for c in range(1, ncol):
                t.setItem(r, c, item(""))
                t.item(r, c).setFlags(Qt.ItemIsEnabled)
            t.setSpan(r, 0, 1, ncol)
        elif row[0] == "doc":
            DF.fill_row(page, r, row[1], None, None, item)
        else:
            d, v = row[1], row[2]
            when = (v.get("added") or "")[:10]
            it = item("        earlier: " + (v.get("label") or v.get("file", "")), d["id"], v.get("file", ""))
            it.setForeground(D.color("muted"))
            t.setItem(r, 0, it)
            for c in range(1, ncol):
                ci = item((v.get("label") or "") + (f"  ·  {when}" if when else "") if c == 3 else "")
                ci.setForeground(D.color("muted"))
                t.setItem(r, c, ci)
    return len(rs)


def set_package(page, key, ids=None):
    """Put the selected documents in a package."""
    lib = page.lib
    ids = [i for i in (ids or page.selected_ids()) if i]
    n = DP.set_package(lib, ids, key) if lib is not None else 0
    if n:
        diag.activity("documents_package_set", n=n)
        page.fill()
        page.host.toast(f"{n} document" + ("" if n == 1 else "s") + " in " + dict(DP.packages(lib))[key])
    return n


def menu(page, m, d):
    """Package, on a customer document's right-click menu, once there is an amendment."""
    lib = page.lib
    if lib is None or not DP.has_groups(lib) or not DP.of(lib, d) or DP.is_amendment(d):
        return None
    pm = m.addMenu("Package")
    now = DP.of(lib, d)
    for k, n in DP.packages(lib):
        a = pm.addAction(n, lambda k=k: set_package(page, k)); a.setCheckable(True); a.setChecked(k == now)
    return pm
