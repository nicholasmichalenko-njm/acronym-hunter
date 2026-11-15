"""The template builder (4.43.0; ST39 to ST44 of 2026-11-15): one screen that makes a new template and changes which
pieces an existing one uses. New template... opens it empty; a double-click on a template's card opens it filled.

It picks; it never changes a piece. Each component is a tile that says what is picked and what the pick holds; a click
lists the saved ones to pick from, and Go to its page leaves for the page where that piece itself is changed. Beside
the tiles: a strip of sample pages drawn from the picks (labelled Approximate: the app's drawing, not Word's), one line
saying whether the picks fit each other, and, once the file is exported, a tick for each pick the file was checked for.
namedtemplates, templatesets, pagelayouts, templateparts, templatesample and templateproof hold the rules."""
import copy, os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QDialog, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QMenu, QScrollArea,
                               QVBoxLayout, QWidget)

import diag
import namedtemplates as NT
import pagelayouts as PGL
import stylelib as SL
import templatelib as TL
import templateparts as TP
import templateproof as TPF
import templatesample as TSM
import templatesets as TS
from . import design as D
from .tplsample import SampleStrip

# key, tile title, group, the page that changes the piece
TILES = (("layout", "Page Setup", "Page Layout", "layouts"), ("numbering", "Numbering", "Page Layout", "layouts"),
         ("style_sets", "Style sets", "Styles", "styles"), ("setup_set", "Setup styles", "Styles", "styles"),
         ("part_set", "Quick Part set", "Quick Parts", "designs"), ("starts", "Starting pages", "Quick Parts", "designs"))
LATER = "Headers, footers, lists, captions and the Table of Contents come from the Global Standards until each gets its own pick."
SKETCH = "Approximate: drawn by Stationkeeper from the picks. Word's own pages come in a later release."


class Tile(QFrame):
    def __init__(self, dlg, key, title):
        super().__init__()
        self.dlg, self.key = dlg, key
        self.setObjectName("tpltile"); self.setCursor(Qt.PointingHandCursor); self.setMinimumWidth(220)
        v = QVBoxLayout(self); v.setContentsMargins(10, 8, 10, 8); v.setSpacing(2)
        self.head = D.label(title, "label"); v.addWidget(self.head)
        self.pick = QLabel(""); self.pick.setWordWrap(True); self.pick.setObjectName("tplpick"); v.addWidget(self.pick)
        self.holds = D.label("", "muted"); self.holds.setWordWrap(True); v.addWidget(self.holds)
        self.setToolTip("Click to pick from what is saved")

    def show_pick(self, name, holds, picked):
        t = D.tokens()
        self.pick.setText(name); self.holds.setText(holds)
        self.setStyleSheet(f"QFrame#tpltile{{background:{t['surface']};border:1px {'solid' if picked else 'dashed'} {t['border']};"
                           f"border-radius:{D.RADIUS['card']}px;}} QFrame#tpltile QLabel{{background:transparent;}} "
                           f"QLabel#tplpick{{font-weight:600;color:{t['text'] if picked else t['muted']};}}")

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            m = self.dlg.tile_menu(self.key)
            m.exec(self.mapToGlobal(e.position().toPoint()))


class BuilderDialog(QDialog):
    def __init__(self, page, tid=None):
        super().__init__(page)
        self.page, self.host, self.tid = page, page.host, tid
        self.cfg = self.host.config_dir
        self.lib = TL.Library(self.cfg)
        t = NT.get(self.cfg, tid) if tid else None
        self.rec = TS.recipe({TS.KEY: copy.deepcopy((t or {}).get("sets") or {})})
        self.setWindowTitle(f"Template: {t['name']}" if t else "New template")
        self.resize(1180, 760)
        v = QVBoxLayout(self)
        h = QHBoxLayout(); h.addWidget(D.label("Name", "label"))
        self.name = QLineEdit(t["name"] if t else ""); self.name.setPlaceholderText("Where or how it is used: Page-limited RFP, Volume I")
        h.addWidget(self.name, 1); v.addLayout(h)
        body = QHBoxLayout(); v.addLayout(body, 1)
        left = QVBoxLayout(); body.addLayout(left, 2)
        left.addWidget(D.label("What goes in. A tile picks one of what is saved; it changes nothing in the piece itself.", "muted"))
        self.tiles = {}
        group = None
        for key, title, grp, _step in TILES:
            if grp != group:
                left.addWidget(D.label(grp, "title")); g = QGridLayout(); g.setSpacing(D.SPACE["s"]); left.addLayout(g); group, n = grp, 0
            tile = Tile(self, key, title); self.tiles[key] = tile
            g.addWidget(tile, n // 2, n % 2); n += 1
        later = D.label(LATER, "muted"); later.setWordWrap(True); left.addWidget(later)
        left.addStretch(1)
        right = QVBoxLayout(); body.addLayout(right, 3)
        self.kind = QLabel(SKETCH); self.kind.setObjectName("sampleKind"); self.kind.setWordWrap(True); right.addWidget(self.kind)
        self.strip = SampleStrip()
        sc = QScrollArea(); sc.setWidgetResizable(True); sc.setWidget(self.strip); right.addWidget(sc, 1)
        self.line = QLabel(""); self.line.setObjectName("tpLine"); self.line.setWordWrap(True); right.addWidget(self.line)
        self.ticks = QLabel(""); self.ticks.setWordWrap(True); self.ticks.setTextFormat(Qt.RichText); right.addWidget(self.ticks)
        self.said = D.label("", "muted"); self.said.setWordWrap(True); v.addWidget(self.said)
        b = QHBoxLayout(); b.addStretch(1)
        self.b_close = D.button("Close", None, lambda: self.reject()); b.addWidget(self.b_close)
        self.b_export = D.button("Export", None, lambda: self.export(), "Save, write the .dotx and check it against the picks"); b.addWidget(self.b_export)
        self.b_save = D.button("Save", "primary", lambda: self.save(), "Keep the name and the picks"); b.addWidget(self.b_save)
        v.addLayout(b)
        self.can = page.can_change() if hasattr(page, "can_change") else True     # 4.43.1 (ST48): look inside, never change
        if not self.can:
            self.name.setReadOnly(True); self.b_save.setVisible(False)
            self.said.setText("Proposal managers and production leads build and change templates. You can look inside this one and export it.")
        self.fill()

    # ------------------------------------------------------------ what is shown
    def working(self):
        """The template as it would be saved now."""
        t = NT.get(self.cfg, self.tid) if self.tid else {}
        return dict(t or {}, name=self.name.text().strip() or "New template", sets=copy.deepcopy(self.rec))

    def _starts(self):
        return [n for _k, _p, _g, n in TS.start_files(self.cfg, self.rec)]

    def tile_words(self, key):
        """(what is picked, what it holds, True when something is picked)."""
        r = self.rec
        if key in ("layout", "numbering"):
            it = PGL.get(self.cfg, key, r[key])
            import prodrules as PRL
            std = NT.std_of(self.cfg, self.working())
            return (it["name"] if it else "From the Global Standards", PGL.words(key, PGL.extract(std, key)), bool(it))
        if key == "style_sets":
            ks = [k for k in (SL.get_set(self.lib, s) for s in r["style_sets"]) if k]
            chosen, wins = TS.styles(self.lib, r)
            return (", then ".join(k["name"] for k in ks) or "None: the Global Standards' formatting",
                    (f"{len(chosen)} style{'' if len(chosen) == 1 else 's'}" + (f"; {len(wins)} taken from the later set" if wins else "")) if ks else "", bool(ks))
        if key in ("setup_set", "part_set"):
            k = SL.get_set(self.lib, r[key]) if r[key] else None
            n = len((k or {}).get("items") or [])
            word = "style" if key == "setup_set" else "Quick Part"
            return (k["name"] if k else "None", f"{n} {word}{'' if n == 1 else 's'}" if k else "", bool(k))
        names = self._starts()
        return (", ".join(names) or "None: the document starts with its first heading",
                f"{len(names)} page{'' if len(names) == 1 else 's'}, in this order" if names else "", bool(names))

    def fill(self):
        self.lib.fresh()
        for key, tile in self.tiles.items():
            tile.show_pick(*self.tile_words(key))
        t = self.working()
        std = NT.std_of(self.cfg, t)
        self.strip.show_pages(TSM.pages(std, self.cfg, self._starts()))
        self.rows = TP.rows(self.cfg, t, self.lib)
        ok, said = TP.ready(self.rows)
        tok = D.tokens()
        self.line.setText(said)
        self.line.setStyleSheet(f"QLabel#tpLine{{color:{tok['ok' if ok else 'warn']};font-weight:600}}")
        self.kind.setStyleSheet(f"QLabel#sampleKind{{color:{tok['warn']};}}")
        self.show_ticks()
        return self.rows

    def show_ticks(self):
        """The ticks for the exported file, when the picks are the saved ones; '' otherwise."""
        t = NT.get(self.cfg, self.tid) if self.tid else None
        self.proof = TPF.check(self.cfg, t, lib=self.lib) if t and TS.recipe({TS.KEY: t.get("sets") or {}}) == self.rec else []
        tok = D.tokens()
        mark = {TPF.OK: (tok["ok"], "In the file"), TPF.BAD: (tok["warn"], "Differs"), TPF.SKIP: (tok["muted"], "Not checked")}
        self.ticks.setText("<br>".join(f"<span style='color:{mark[x['state']][0]}'><b>{mark[x['state']][1]}</b></span> "
                                       f"{x['name']}: {x['says']}" for x in self.proof))
        self.ticks.setVisible(bool(self.proof))
        return self.proof

    # ------------------------------------------------------------ picking
    def set_pick(self, key, value):
        if not self.can:
            return self.rec[key]
        self.rec[key] = value
        self.rec = TS.recipe({TS.KEY: self.rec})
        self.said.setText("")
        self.fill()
        return self.rec[key]

    def toggle_style_set(self, sid):
        """A style set joins at the end or leaves. Where two sets hold a style, the later one wins."""
        ids = list(self.rec["style_sets"])
        ids.remove(sid) if sid in ids else ids.append(sid)
        return self.set_pick("style_sets", ids)

    def page_choices(self, kind):
        import partlib as PT
        import sectiondesigns as SDZ
        return [(x["id"], PT.shown_name(self.cfg, x)) for x in SDZ.designs(self.cfg, kind)]

    def add_start(self, kind, part):
        return self.set_pick("starts", self.rec["starts"] + [{"kind": kind, "part": part, "gallery": True}])

    def drop_start(self, i):
        s = list(self.rec["starts"])
        if 0 <= i < len(s):
            del s[i]
        return self.set_pick("starts", s)

    def tile_menu(self, key):
        m = QMenu(self)
        r = self.rec
        if not self.can:
            m.addAction("Proposal managers and production leads change what goes in").setEnabled(False)
            return m

        def one(text, value, cur):
            a = m.addAction(text); a.setCheckable(True); a.setChecked(value == cur)
            a.triggered.connect(lambda *_x, v=value: self.set_pick(key, v))

        if key in ("layout", "numbering"):
            one("From the Global Standards", "", r[key])
            for it in PGL.every(self.cfg, key):
                one(f"{it['name']}    {PGL.words(key, it['values']).split(';')[0]}", it["id"], r[key])
        elif key == "style_sets":
            for k in SL.sets(self.lib, "style"):
                a = m.addAction(f"{k['name']}    {len(k['items'])} style{'' if len(k['items']) == 1 else 's'}")
                a.setCheckable(True); a.setChecked(k["id"] in r["style_sets"])
                a.triggered.connect(lambda *_x, s=k["id"]: self.toggle_style_set(s))
        elif key in ("setup_set", "part_set"):
            one("None", "", r[key])
            for k in SL.sets(self.lib, "style" if key == "setup_set" else "part"):
                one(f"{k['name']}    {len(k['items'])}", k["id"], r[key])
        else:
            add = m.addMenu("Add a page")
            for kind, title in TS.SLOT_KINDS:
                sub = add.addMenu(title)
                for pid, name in self.page_choices(kind):
                    sub.addAction(name).triggered.connect(lambda *_x, k=kind, p=pid: self.add_start(k, p))
                sub.setEnabled(bool(sub.actions()))
            out = m.addMenu("Take a page out")
            for i, name in enumerate(self._starts()):
                out.addAction(f"{i + 1}. {name}").triggered.connect(lambda *_x, n=i: self.drop_start(n))
            out.setEnabled(bool(out.actions()))
        if not [a for a in m.actions() if not a.menu()] and key != "starts":
            a = m.addAction("Nothing is saved to pick from yet"); a.setEnabled(False)
        m.addSeparator()
        m.addAction("Go to its page").triggered.connect(lambda *_x: self.go_to(key))
        return m

    def go_to(self, key):
        """Leaves the builder for the page where this piece is changed. The picks are saved first when they can be."""
        step = dict((k, s) for k, _t, _g, s in TILES)[key]
        if self.name.text().strip():
            self.save(close=False)
        self.reject()
        if step == "layouts":
            self.page.layouts(kind=key)
        else:
            self.host.go(step)
        return step

    # ------------------------------------------------------------ keeping it
    def save(self, close=True):
        """Keeps the name and the picks. A new template is made on the first save. Returns its id, or None."""
        if not self.can:
            return None
        name = self.name.text().strip()
        if self.tid is None:
            t = NT.new(self.cfg, name)
            if t is None:
                self.said.setText("Give it a name that no other template has.")
                return None
            self.tid = t["id"]
            diag.activity("named_template_new")
        elif name != NT.get(self.cfg, self.tid)["name"] and not NT.rename(self.cfg, self.tid, name):
            self.said.setText("Give it a name that no other template has.")
            return None
        NT.set_recipe(self.cfg, self.tid, self.rec)
        self.setWindowTitle(f"Template: {NT.get(self.cfg, self.tid)['name']}")
        self.said.setText("Saved.")
        self.page.fill(); self.page.select(self.tid)
        if close and not os.environ.get("AH_TEST"):
            self.accept()
        return self.tid

    def export(self):
        """Saves, writes the .dotx and checks it against the picks. Returns the job, or None."""
        if self.can and self.save(close=False) is None:
            return None
        job = self.page.make(self.tid)
        if job is None:
            self.said.setText("The file was not written. " + (self.said.text() if self.said.text() != "Saved." else ""))
            return None
        self.fill()
        self.said.setText(f"Exported {os.path.basename(job.copy)}. " + TPF.words(self.proof))
        return job


def builder(page, tid=None, modal=True):
    dlg = BuilderDialog(page, tid)
    page.builder_dialog = dlg
    if modal and not os.environ.get("AH_TEST"):
        dlg.exec()
    return dlg
