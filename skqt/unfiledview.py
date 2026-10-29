"""Unfiled work in Qt (2.91.0): the reminder strip across every page while Unfiled is open and holds work, Make it an
effort (by an effort package, so every path follows, then Unfiled starts empty with a copy kept in the new effort's
backups), and Clear Unfiled (a copy kept in the app's own folder). The rules are unfiled's. Nothing leaves the PC."""
import datetime, os
from PySide6.QtWidgets import QHBoxLayout, QInputDialog, QLabel, QMessageBox, QWidget
import diag
import unfiled as UF
from . import design as D


class UnfiledStrip(QWidget):
    def __init__(self, host):
        super().__init__()
        self.host = host
        self.setObjectName("unfiledStrip")
        h = QHBoxLayout(self); h.setContentsMargins(D.SPACE["xl"], 6, D.SPACE["xl"], 6); h.setSpacing(D.SPACE["s"])
        self.text = QLabel(""); self.text.setWordWrap(True); h.addWidget(self.text, 1)
        self.mk = D.button("Make it an effort...", "primary", lambda: host.make_unfiled_effort())
        self.add = D.button("Add to an effort...", None, lambda: (host.go("efforts"), host.efforts_page.add_unfiled_to()))
        h.addWidget(self.mk); h.addWidget(self.add)
        self.setVisible(False)

    def refresh(self):
        h = self.host
        on = h.ws is not None and UF.is_unfiled(h.efforts, h.effort_name)
        c = UF.counts(h.efforts) if on else {}
        t = D.tokens()
        self.setStyleSheet(f"QWidget#unfiledStrip{{background:{t['warn_soft']};}} QWidget#unfiledStrip QLabel{{color:{t['text']};}}")
        if on:
            self.text.setText("<b>Working unfiled.</b> " + ("Holds " + UF.summary_text(c) + ". File it into an effort when you know "
                              "where it belongs." if not UF.empty(c) else "Use any tool; file the work into an effort when you know "
                              "where it belongs."))
        self.mk.setEnabled(on and not UF.empty(c))
        self.add.setEnabled(on and not UF.empty(c) and any(not (h.efforts.get(n) or {}).get("unfiled") for n in h.efforts.names()))
        self.setVisible(on)
        return on


def make_effort(host, name=None):
    """Unfiled becomes the effort named name: packaged, unpacked into Efforts\\<name> under that name, opened; Unfiled is
    then emptied (its old folder zipped into the new effort's backups first). Returns the new name, or None."""
    import app_gui
    import datahome
    import effort as E
    import effortfolders as EF
    import effortpkg as P
    import effortrec as RR
    import re
    import workspace as W
    h = host
    if name is None:
        name, ok = QInputDialog.getText(h, "Make it an effort", "Name of the effort (the Unfiled work becomes it):")
        if not ok:
            return None
    name = " ".join((name or "").split())
    if not name or name == UF.NAME:
        h.status("Give the effort a name.")
        return None
    if name in h.efforts.names():
        h.status("An effort with that name already exists. Use Add to an effort instead.")
        return None
    stem = re.sub(r"[^A-Za-z0-9 _.-]+", "", name).strip().replace(" ", "_") or "Effort"
    dest = os.path.join(datahome.efforts_dir(app_gui.DATA_DIR), stem)
    if os.path.exists(dest) and os.listdir(dest):
        h.status(f"A folder named {stem} is already in Efforts. Pick another name.")
        return None
    if h.effort_name != UF.NAME and not h.open_effort(UF.NAME):
        return None
    h.save_now()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    pkg = os.path.join(app_gui.SANDBOX_TEMP, f"unfiled-{stamp}{P.EXT}")
    try:
        man = h.record_page.save_package(pkg, library="all")
        if not man:
            return None
        old_folder = os.path.dirname(h.effort_path)
        h.close_effort()
        got = P.unpack(man["path"], dest, W.data_dir_for, list_name=f"{stem}_Effort_List.xlsx")
        P.repoint(got["data"], got["customer_dir"], got["matrix"], got.get("moved"))
    except Exception as e:
        diag.swallowed()
        h.status(f"Unfiled could not become an effort ({type(e).__name__}). Nothing changed in Unfiled.")
        h.open_effort(UF.NAME)
        return None
    finally:
        try:
            os.remove(pkg)
        except OSError:
            pass
    info = h.efforts.get(UF.NAME) or {}
    EF.create_all(got["list"])
    h.efforts.put(name, path=got["list"], customer_dir=got["customer_dir"] or EF.folder(got["list"], "customer"),
                  volumes_dir=got["volumes_dir"] or EF.folder(got["list"], "volumes"),
                  first_use=info.get("first_use", "volume"))
    try:
        L = E.EffortList(got["list"]).load()
        L.name = name; L.pending = True; L.save()
    except Exception:
        diag.swallowed()
    keep = os.path.join(got["data"], "backups", f"Unfiled before it became {stem} {stamp}.zip")
    UF.clear(h.efforts, app_gui.DATA_DIR, keep_zip=keep)
    h.fill_efforts()
    if not h.open_effort(name):
        return None
    RR.Record(h.ws.root).log("effort", f"Made from Unfiled work ({len(man.get('files', {}))} files)", save=True)
    h.effort_box.setCurrentText(name)
    diag.activity("qt_unfiled_made_effort", files=len(man.get("files", {})))
    h.go("home")
    h.toast(f"{name} is an effort now. Unfiled is empty again.")
    return name


def clear_unfiled(host, confirm=None):
    """Empty Unfiled (a copy kept in Stationkeeper Data\\config\\unfiled_cleared). confirm (tests): True."""
    import app_gui
    h = host
    if confirm is None:
        if QMessageBox.question(h, "Clear Unfiled", "Empty Unfiled? A copy is kept (Stationkeeper Data\\config\\unfiled_cleared)."
                                ) != QMessageBox.Yes:
            return False
    if h.effort_name == UF.NAME:
        h.close_effort()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    ok = UF.clear(h.efforts, app_gui.DATA_DIR, keep_zip=os.path.join(app_gui.CONFIG_DIR, "unfiled_cleared", f"Unfiled {stamp}.zip"))
    h.fill_efforts()
    diag.activity("qt_unfiled_cleared")
    h.toast("Unfiled is empty. A copy is kept.")
    return ok
