"""Effort Settings rows added in 4.79.0 (step E2, claude/stationkeeper-effort-settings-direction-2026-11-25.md).

Effort type and Response type describe the effort, so they sit in the Effort group (UX decision 70: they left the
formatting page). Files and sources gains Template (what the effort's volumes are written on, changed in Setup's
Templates for the volumes) and Acronym sources (what an effort's acronyms are read against). Every change is kept
when it is made and written to Effort Activity. The values are where they always were (the effort's prod_std and its
template picks), so nothing the macros read changes. Rules only (No AI); nothing leaves the PC."""
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QSizePolicy, QVBoxLayout, QWidget

import diag
import prodrules as PRL
from . import design as D

NO_TYPE = "Not set"
NO_TEMPLATE = "No template: the effort's own formatting"
OWN = "the effort's own formatting"
NO_VOLUMES = "No volumes yet: the Outline sets them"
DB_LINE = "Acronym database, read for every effort"
NO_PROGRAM_LISTS = "No program has its own acronym list yet."


# ---------------------------------------------------------------- the values (shared with Effort Formatting)
def set_type(host, eid):
    """The effort's type; its volume profile follows when the old one is not the new type's. Returns True if changed."""
    if host.ws is None:
        return False
    import effortformat as EFM
    data = PRL.load(host.config_dir)
    eff = EFM.eff_of(host.ws)
    eid = eid or ""
    if (eff.get("effort_type") or "") == eid:
        return False
    eff["effort_type"] = eid
    et = PRL.effort_type_of(data, eid)
    if et and eff.get("type") not in et["profiles"]:
        eff["type"] = et["default_profile"]
    host.ws.set("prod_std", eff)
    return True


def set_response(host, rt):
    """The effort's response type ('' follows the effort type). Returns True if changed."""
    if host.ws is None:
        return False
    import effortformat as EFM
    eff = EFM.eff_of(host.ws)
    rt = rt or ""
    if (eff.get("response_type") or "") == rt:
        return False
    if rt:
        eff["response_type"] = rt
    else:
        eff.pop("response_type", None)
    host.ws.set("prod_std", eff)
    return True


def type_choices(config_dir, current=""):
    """[(name, id)]: Not set, then the team's effort types. Program deliverables is not offered (decision 57) unless it
    is this effort's type already, so an older effort's value is shown, never changed by the page."""
    import programs as PG
    out = [(NO_TYPE, "")]
    for e in PRL.load(config_dir).get("effort_types", []):
        if e["id"] != PG.TYPE or e["id"] == current:
            out.append((e["name"], e["id"]))
    return out


def response_choices(config_dir, eid):
    """[(name, value)]: what the effort type gives ('' value), then every response type."""
    import rulebook as RB
    et = PRL.effort_type_of(PRL.load(config_dir), eid)
    from_type = (et or {}).get("response_type") or PRL.STARTER_RESPONSE.get((et or {}).get("id"), "")
    return [(f"From the effort type ({from_type})" if from_type else NO_TYPE, "")] + [(rt, rt) for rt in RB.response_types()]


# ---------------------------------------------------------------- the rows on the page
class TypeRows:
    """Effort type and Response type in the Effort group, each kept when picked."""

    def __init__(self, page, form, at):
        self.page, self.host = page, page.host
        self.etype = QComboBox(); self.etype.setObjectName("settingsType")
        self.etype.setToolTip("What kind of effort this is. Its formatting and starting templates follow it.")
        self.resp = QComboBox(); self.resp.setObjectName("settingsResponse")
        self.resp.setToolTip("Style names follow it: a style named with RFP is named RFI in an RFI (Rule 4)")
        self.etype.activated.connect(lambda _i: self.type_picked())
        self.resp.activated.connect(lambda _i: self.response_picked())
        for box in (self.etype, self.resp):
            box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.brings = D.label("", "muted"); self.brings.setObjectName("typeBrings"); self.brings.setWordWrap(True)
        form.insertRow(at, "Effort type", self.etype)
        form.insertRow(at + 1, "", self.brings)            # 4.41.0: what the effort type starts with (was on the start form)
        form.insertRow(at + 2, "Response type", self.resp)

    def fill(self):
        h = self.host
        if h.ws is None:
            return
        import effortformat as EFM
        eff = EFM.eff_of(h.ws)
        eid = eff.get("effort_type") or ""
        for box, items, want in ((self.etype, type_choices(h.config_dir, eid), eid),
                                 (self.resp, response_choices(h.config_dir, eid), eff.get("response_type") or "")):
            box.blockSignals(True)
            box.clear()
            for name, val in items:
                box.addItem(name, val)
            box.setCurrentIndex(max(0, box.findData(want)))
            box.blockSignals(False)
        from .efforttplview import start_words
        said = start_words(h.config_dir, eid)
        said = said if said.startswith("It starts with") else ""     # the how-to line names a window that is not on this page
        self.brings.setText(said); self.brings.setVisible(bool(said))

    def _after(self, what, value):
        h = self.host
        self.page.rec.log("effort", f"{what}: {value}", save=True)
        if what == "Effort type":
            diag.activity("qt_effort_type_kept")
        else:
            diag.activity("qt_response_type_kept")
        try:
            h.changed()
        except Exception:  # noqa: BLE001
            diag.swallowed()
        h.status(f"{what} kept.")
        self.fill()

    def type_picked(self, eid=None):
        """eid (tests): the type picked. Returns True when kept."""
        eid = self.etype.currentData() if eid is None else eid
        if not set_type(self.host, eid):
            return False
        self._after("Effort type", self.etype.itemText(max(0, self.etype.findData(eid))) if eid else NO_TYPE)
        return True

    def response_picked(self, rt=None):
        rt = self.resp.currentData() if rt is None else rt
        if not set_response(self.host, rt):
            return False
        self._after("Response type", rt or "from the effort type")
        return True


def _line(text, button=None):
    w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(D.SPACE["s"])
    lab = D.label(text, None); lab.setWordWrap(True); h.addWidget(lab, 1)
    if button is not None:
        h.addWidget(button)
    return w, lab


class SourceRows:
    """Template and Acronym sources in Files and sources."""

    def __init__(self, page, form):
        self.page, self.host = page, page.host
        self.change_tpl = D.button("Change...", "ghost", lambda: self.change_template(),
                                   "Setup's Templates for the volumes: each volume takes a template, or the effort's own formatting")
        row, self.template = _line("", self.change_tpl)
        form.addRow("Template", row)
        self.open_db = D.button("Open", "ghost", lambda: self.host.go("refs"), "Team References: the acronym database")
        w = QWidget(); v = QVBoxLayout(w)
        v.setContentsMargins(0, 0, 0, 0); v.setSpacing(2)
        row2, self.acr = _line(DB_LINE, self.open_db)
        v.addWidget(row2)
        self.acr_note = D.label("", "muted"); v.addWidget(self.acr_note)
        form.addRow("Acronym sources", w)

    def volumes(self):
        try:
            return list(self.host.setups_page.volume_names())
        except Exception:  # noqa: BLE001
            diag.swallowed()
            return []

    def template_text(self):
        """The line: one template's name, By volume with each, the effort's own formatting, or no volumes yet."""
        import namedtemplates as NT
        vols, picks = self.volumes(), NT.picks(self.host.ws)
        if not vols:
            names = sorted({p.get("name") or "" for p in picks.values() if p.get("name")})
            return names[0] if len(names) == 1 else (NO_VOLUMES if not names else "By volume: " + ", ".join(names))
        got = [(v, (picks.get(v) or {}).get("name") or "") for v in vols]
        names = {n for _v, n in got}
        if names == {""}:
            return NO_TEMPLATE
        if len(names) == 1:
            return next(iter(names))
        return "By volume: " + "; ".join(f"{v}, {n or OWN}" for v, n in got)

    def fill(self):
        if self.host.ws is None:
            return
        self.template.setText(self.template_text())
        self.acr.setText(DB_LINE)
        self.acr_note.setText(NO_PROGRAM_LISTS)

    def change_template(self, run=True):
        """Opens Setup's Templates for the volumes; the line is read again after. Returns the window (or None)."""
        try:
            from . import namedtplpage as NP
            dlg = NP.volume_templates(self.host.setups_page) if run else None
        except Exception:  # noqa: BLE001
            diag.swallowed()
            dlg = None
        self.fill()
        return dlg
