"""Unfiled work in Qt (2.91.0): the reminder strip across every page while Unfiled is open, Make it an effort (by an
effort package, so every path follows, then Unfiled starts empty with a copy kept in the new effort's backups), and
Clear Unfiled (a copy kept in the app's own folder). 4.51.0: Unfiled takes no new work and reads "Unfiled, from before";
Name it... (name_it) makes what it holds an effort or a program, and the app offers it once at start (offer_at_start).
Nothing moves until the person presses Name it. The rules are unfiled's and homes'. Nothing leaves the PC."""
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
        self.mk = D.button("Name it...", "primary", lambda: host.make_unfiled_effort())
        self.add = D.button("Add to an effort...", None, lambda: (host.go("efforts"), host.efforts_page.add_unfiled_to()))
        h.addWidget(self.mk); h.addWidget(self.add)
        self.setVisible(False)

    def refresh(self):
        h = self.host
        on = h.ws is not None and UF.is_unfiled(h.efforts, h.effort_name)
        c = UF.counts(h.efforts) if on else {}
        t = D.tokens()
        D.themed(self, lambda t: f"QWidget#unfiledStrip{{background:{t['warn_soft']};}} QWidget#unfiledStrip QLabel{{color:{t['text']};}}")
        if on:
            import homes as HM
            self.text.setText(f"<b>{HM.SHOWN}.</b> " + ("Holds " + UF.summary_text(c) + "." if not UF.empty(c) else "Nothing in it."))
        self.mk.setEnabled(on and not UF.empty(c))
        self.add.setEnabled(on and not UF.empty(c) and any(not (h.efforts.get(n) or {}).get("unfiled") for n in h.efforts.names()))
        self.setVisible(on)
        return on


def make_effort(host, name=None, program=False):
    """Unfiled becomes the effort named name: packaged, unpacked into Efforts\\<name> under that name, opened; Unfiled is
    then emptied (its old folder zipped into the new effort's backups first). Returns the new name, or None. program
    (4.51.0): the same made a program, in Programs\\<name>: its Customer Documents folder becomes Program Documents, no
    proposal folder tree is made, and it is registered program."""
    import app_gui
    import datahome
    import effort as E
    import effortfolders as EF
    import effortpkg as P
    import effortrec as RR
    import programs as PG
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
    dest = os.path.join(PG.programs_dir(app_gui.DATA_DIR) if program else datahome.efforts_dir(app_gui.DATA_DIR), stem)
    if os.path.exists(dest) and os.listdir(dest):
        h.status(f"A folder named {stem} is already in {'Programs' if program else 'Efforts'}. Pick another name.")
        return None
    if (h.ws is None or h.effort_name != UF.NAME) and not h.open_effort(UF.NAME):   # 4.51.0: a closed effort keeps its name
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
        got = P.unpack(man["path"], dest, W.data_dir_for, list_name=stem + (PG.LIST_TAIL if program else "_Effort_List.xlsx"))
        if program:                                   # 4.51.0: the customer's documents are the program documents
            docs = os.path.join(dest, PG.DOCS)
            if got["customer_dir"] and os.path.isdir(got["customer_dir"]):
                os.replace(got["customer_dir"], docs)
                got["moved"] = {k: os.path.join(docs, os.path.relpath(v, got["customer_dir"])) if v.startswith(got["customer_dir"] + os.sep) else v
                                for k, v in (got.get("moved") or {}).items()}
            os.makedirs(docs, exist_ok=True)
            got["customer_dir"] = got["volumes_dir"] = docs
        P.repoint(got["data"], got["customer_dir"], got["matrix"], got.get("moved"))
    except Exception as e:
        diag.swallowed()
        h.status(f"It could not be named ({type(e).__name__}). Nothing changed in Unfiled, from before.")
        h.open_effort(UF.NAME)
        return None
    finally:
        try:
            os.remove(pkg)
        except OSError:
            pass
    info = h.efforts.get(UF.NAME) or {}
    if program:
        h.efforts.put(name, path=got["list"], program=True, customer_dir=got["customer_dir"], volumes_dir=got["volumes_dir"],
                      first_use=info.get("first_use", "volume"))
    else:
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
    h.go("overview" if program else "home")
    h.toast(f"{name} is {'a program' if program else 'an effort'} now. It holds what Unfiled held.")
    return name


def _first_doc_name(host):
    docs = UF.documents(host.efforts)
    return docs[0][1] if docs else ""


def name_it(host, kind=None, name=None, sentence=""):
    """4.51.0: name what Unfiled holds, from before, as an effort or a program (one small dialog). kind ("effort" or
    "program") and name (tests): the answers. Returns the new home's name, or None (Not now, or a name refused)."""
    import homes as HM
    h = host
    if kind is None or name is None:
        first = _first_doc_name(h)
        guess = HM.free_name(h.efforts, HM.suggest_name([first]) if first else "From Unfiled") or "From Unfiled"
        from .homeask import NameItDialog
        d = NameItDialog(h, guess, sentence, h.efforts)
        if d.exec() != NameItDialog.Accepted:
            return None
        kind, name = d.values()
    name = " ".join((name or "").split())
    why = HM.check_new(h.efforts, name, kind)
    if why:
        h.status(why)
        return None
    got = make_effort(h, name, program=(kind == "program"))
    if got:
        HM.set_offer_state(h.efforts, HM.NAMED)
        h.fill_efforts()
    return got


def offer_at_start(host, answer=None):
    """4.51.0: once, at start, while Unfiled holds work from before and was never offered: the Name it dialog with one
    sentence. answer (tests): ("effort" or "program", name) to name it, or False for Not now. Not now is kept ("later") and
    the offer never shows by itself again. Returns the new name, "later", or None when nothing was due."""
    import homes as HM
    h = host
    try:
        due = HM.start_offer_due(h.efforts)
    except Exception:  # noqa: BLE001  an Unfiled that cannot be read is not offered; the start goes on
        diag.swallowed()
        return None
    if not due:
        return None
    if answer is None:
        sentence = (f"Unfiled holds work from before: {UF.summary_text(UF.counts(h.efforts))}. Work now always has a named "
                    "home. Name it as an effort or a program, or leave it where it is.")
        got = name_it(h, sentence=sentence)
    elif answer:
        got = name_it(h, kind=answer[0], name=answer[1])
    else:
        got = None
    if not got:
        HM.set_offer_state(h.efforts, HM.LATER)
        diag.activity("unfiled_offer_later")
        return HM.LATER
    return got


def clear_unfiled(host, confirm=None):
    """Empty Unfiled (a copy kept in Stationkeeper Data\\config\\unfiled_cleared). confirm (tests): True."""
    import app_gui
    h = host
    if confirm is None:
        if QMessageBox.question(h, "Clear it", "Empty Unfiled, from before? A copy is kept (Stationkeeper Data\\config\\unfiled_cleared)."
                                ) != QMessageBox.Yes:
            return False
    if h.effort_name == UF.NAME:
        h.close_effort()
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    ok = UF.clear(h.efforts, app_gui.DATA_DIR, keep_zip=os.path.join(app_gui.CONFIG_DIR, "unfiled_cleared", f"Unfiled {stamp}.zip"))
    h.fill_efforts()
    diag.activity("qt_unfiled_cleared")
    h.toast("Unfiled, from before is empty now. A copy is kept.")
    return ok
