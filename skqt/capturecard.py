"""Shred's capture card (4.12.0; claude/stationkeeper-capture-cards-plan-4.12.md, part A).

Capture > Contact, Key date or Effort detail on Shred opens a card at the top of the piece pane instead of a dialog. It
stays open while the person reads on: pick words anywhere, on any page, then Take on a field. Phone, e-mail and address
hold several values, each with a label (Office, Mobile, Fax, Main, Other or a word of your own) and the page it came
from. A contact can be one already filed: the card shows what is filed and every value can be fixed in place. Save files
the card and marks every piece it took words from; Cancel drops it. One card at a time.

A guess from the first selection fills blank fields only; Take and typing replace what a field holds."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QComboBox, QFrame, QGridLayout, QHBoxLayout, QLineEdit, QMessageBox, QScrollArea, QVBoxLayout,
                               QWidget)

import captures as CP
import contactcard as CC
import diag
from . import design as D

TITLES = {"contact": "Contact", "keydate": "Key date", "detail": "Effort detail"}
KINDS = tuple(TITLES)


def fields_of(kind):
    """[(key, label, how)]: how is 'text', 'multi' or a tuple of choices."""
    if kind == "contact":
        return [(f, CC.NAMES[f], "multi" if f in CC.MULTI else "text") for f in CC.SINGLE + CC.MULTI]
    if kind == "keydate":
        from .captureview import KEY_KINDS
        return [("kind", "Kind", tuple(KEY_KINDS)), ("title", "What", "text"), ("date", "Date (YYYY-MM-DD)", "text"),
                ("start", "Time (HH:MM)", "text"), ("zone", "Time zone", "zone")]
    import custfocus as F
    return [("label", "Detail", tuple(F.DETAIL_LABELS)), ("value", "Value", "text")]


def guess(kind, text):
    """What the words say for each field ('' where they say nothing)."""
    if kind == "contact":
        return CP.contact_guess(text)
    if kind == "keydate":
        return CP.key_date_guess(text) or {}
    import custfocus as F
    label, value = F.detail_guess(text)
    return {"label": label, "value": value}


def where(src):
    bits = [x for x in ((src or {}).get("doc"), ("page " + src["page"]) if (src or {}).get("page") else "", (src or {}).get("sid")) if x]
    return ", ".join(bits)


class CaptureCard(QFrame):
    def __init__(self, page, kind, cid=None):
        super().__init__()
        self.page, self.host, self.kind = page, page.host, kind
        self.setObjectName("captureCard")
        self.setStyleSheet(f"QFrame#captureCard{{border:2px solid {D.tokens()['accent']};border-radius:8px;}}")
        self.picks = []                         # [{"sid", "parts", "src"}]: every piece the card took words from
        self.sources = {}                       # single field: [src]
        self.multi = {}                         # list field: [{"label", "value", "source"}]
        self.edits = {}
        self.dirty = False
        v = QVBoxLayout(self); v.setContentsMargins(D.SPACE["s"], D.SPACE["s"], D.SPACE["s"], D.SPACE["s"]); v.setSpacing(D.SPACE["xs"])
        top = QHBoxLayout(); top.setSpacing(D.SPACE["xs"]); v.addLayout(top)
        top.addWidget(D.label(f"<b>{TITLES[kind]}</b>", None, wrap=False))
        self.to = None
        if kind == "contact":
            self.to = QComboBox(); self.to.addItem("New contact", None)
            for c in self.rec().contacts():
                self.to.addItem("Filed: " + CC.summary(c), c["id"])
            if cid:
                self.to.setCurrentIndex(max(0, self.to.findData(cid)))
            self.to.activated.connect(lambda _i: self.load())
            top.addWidget(self.to, 1)
        else:
            top.addStretch(1)
        v.addWidget(D.label("Pick words on any page, then Take on the field they belong in. The card stays open while you read.",
                            "muted"))
        self.grid_w = QWidget(); self.grid = QGridLayout(self.grid_w); self.grid.setContentsMargins(0, 0, 0, 0)
        self.grid.setHorizontalSpacing(D.SPACE["xs"]); self.grid.setVerticalSpacing(D.SPACE["xs"])
        v.addWidget(self.grid_w)
        bar = QHBoxLayout(); v.addLayout(bar)
        self.picked = D.label("", "muted", wrap=False); bar.addWidget(self.picked)
        bar.addStretch(1)
        self.save_btn = D.button("Save", "primary", lambda: self.save(), "File the card")
        bar.addWidget(self.save_btn)
        bar.addWidget(D.button("Cancel", "ghost", lambda: self.cancel(), "Close the card without filing it"))
        self.load(first=cid is None)

    # ------------------------------------------------------------ data
    def rec(self):
        import effortrec as R
        return R.Record(self.host.ws.root)

    def cid(self):
        return self.to.currentData() if self.to is not None else None

    def load(self, first=False):
        """Show the filed contact (or a blank card), then fill blank fields from the selection's words."""
        self.sources, self.multi = {}, {}
        vals = {}
        if self.kind == "contact":
            card = CC.card_of(self.rec().contact(self.cid())) if self.cid() else CC.blank()
            vals = {f: card[f] for f in CC.SINGLE}
            self.multi = {f: [dict(x) for x in card[f]] for f in CC.MULTI}
            self.sources = {f: list(card["sources"].get(f, [])) for f in CC.SINGLE}
        text, src = self.page.capture_source() if first else ("", {})
        if text:
            g = guess(self.kind, text)
            pick = self._pick(text, src)
            for key, _lab, how in fields_of(self.kind):
                gv = (g.get(key) or "").strip()
                if not gv:
                    continue
                if how == "multi":
                    if not self.multi.get(key):
                        self.multi[key] = [{"label": "Main", "value": gv, "source": pick}]
                elif not vals.get(key):
                    vals[key] = gv
                    self.sources[key] = [pick]
        self.build(vals)
        self.dirty = bool(text)

    def _pick(self, text, src):
        """Remember the piece the words came from (to mark it on Save); the value's source."""
        s = {k: src.get(k, "") for k in ("doc", "loc", "page", "sid")}
        s["text"] = " ".join((text or "").split())[:400]
        if src.get("sid") and not any(p["sid"] == src["sid"] for p in self.picks):
            try:
                parts = self.page.excerpt_parts()
            except Exception:
                diag.swallowed()
                parts = []
            self.picks.append({"sid": src["sid"], "parts": parts, "src": s})
        self.picked.setText(f"Picked from {len(self.picks)} piece{'' if len(self.picks) == 1 else 's'}" if self.picks else "")
        return s

    # ------------------------------------------------------------ the fields
    def build(self, vals):
        while self.grid.count():
            w = self.grid.takeAt(0).widget()
            if w is not None:
                w.hide(); w.setParent(None); w.deleteLater()
        self.edits, self.rows = {}, {}
        r = 0
        for key, lab, how in fields_of(self.kind):
            self.grid.addWidget(D.label(lab, "label", wrap=False), r, 0, Qt.AlignTop)
            if how == "multi":
                box = QWidget(); bv = QVBoxLayout(box); bv.setContentsMargins(0, 0, 0, 0); bv.setSpacing(2)
                self.rows[key] = []
                for i, x in enumerate(self.multi.get(key, [])):
                    bv.addWidget(self._value_row(key, i, x))
                if not self.multi.get(key):
                    bv.addWidget(D.label("None yet", "muted", wrap=False))
                self.grid.addWidget(box, r, 1)
                tb = D.button("Take", None, lambda _=False, k=key: self.take(k), "Add the picked words as another value")
            else:
                w = self._editor(how, vals.get(key, ""))
                self.edits[key] = w
                self.grid.addWidget(w, r, 1)
                if self.sources.get(key):
                    w.setToolTip("From " + "; ".join(where(s) for s in self.sources[key]))
                tb = D.button("Take", None, lambda _=False, k=key: self.take(k), "Put the picked words in this field")
            tb.setObjectName(f"take_{key}")
            self.grid.addWidget(tb, r, 2, Qt.AlignTop)
            r += 1
        self.grid.setColumnStretch(1, 1)

    def _editor(self, how, value):
        if how == "text":
            e = QLineEdit(value)
            e.textEdited.connect(lambda _t: self._touch())
            return e
        c = QComboBox()
        if how == "zone":
            import tzones as TZ
            c.addItem("(not stated)", "")
            for k, n in TZ.choices():
                c.addItem(n, k)
            c.setCurrentIndex(max(0, c.findData(value)))
        else:
            c.setEditable(True); c.addItems(list(how))
            if value:
                c.setCurrentText(value)
        c.currentIndexChanged.connect(lambda _i: self._touch())
        return c

    def _value_row(self, key, i, x):
        w = QWidget(); h = QHBoxLayout(w); h.setContentsMargins(0, 0, 0, 0); h.setSpacing(2)
        lab = QComboBox(); lab.setEditable(True); lab.addItems(list(CC.LABELS)); lab.setCurrentText(x.get("label") or "Main")
        lab.setMaximumWidth(110)
        val = QLineEdit(x.get("value", ""))
        if x.get("source"):
            val.setToolTip("From " + where(x["source"]))
        lab.currentTextChanged.connect(lambda t, k=key, j=i: self._set(k, j, label=t))
        val.textEdited.connect(lambda t, k=key, j=i: self._set(k, j, value=t))
        h.addWidget(lab); h.addWidget(val, 1)
        h.addWidget(D.button("Take out", "ghost", lambda _=False, k=key, j=i: self.drop_value(k, j), "Take this value off the card"))
        self.rows[key].append((lab, val))
        return w

    def _touch(self):
        self.dirty = True

    def _set(self, key, i, label=None, value=None):
        if 0 <= i < len(self.multi.get(key, [])):
            if label is not None:
                self.multi[key][i]["label"] = label
            if value is not None:
                self.multi[key][i]["value"] = value
            self.dirty = True

    def values(self):
        out = {}
        for key, _lab, how in fields_of(self.kind):
            if how == "multi":
                out[key] = [dict(x) for x in self.multi.get(key, [])]
            else:
                w = self.edits[key]
                out[key] = w.text().strip() if isinstance(w, QLineEdit) else (w.currentData() if how == "zone" else w.currentText().strip())
        return out

    def take(self, key, text=None, src=None):
        """Put the picked words in a field (text, src: tests). A whole sentence picked gives the field's guess from it."""
        if text is None:
            text, src = self.page.capture_source()
        if not text:
            self.host.status("Pick words on the page first (drag across them), then Take.")
            return False
        src = src or {}
        how = dict((k, h) for k, _l, h in fields_of(self.kind))[key]
        picked_words = bool(getattr(self.page, "grab", None)) or bool(getattr(self.page, "grab_multi", None))
        value = " ".join(text.split())
        if not picked_words or len(value) > 80:
            g = (guess(self.kind, text).get(key) or "").strip()
            value = g or value
        s = self._pick(text, src)
        vals = self.values()
        if how == "multi":
            self.multi.setdefault(key, []).append({"label": "Main" if not self.multi.get(key) else "Other", "value": value, "source": s})
        else:
            vals[key] = value
            self.sources[key] = [s]
        self.build(vals)
        self.dirty = True
        return True

    def drop_value(self, key, i):
        vals = self.values()
        if 0 <= i < len(self.multi.get(key, [])):
            self.multi[key].pop(i)
            self.build(vals)
            self.dirty = True
            return True
        return False

    # ------------------------------------------------------------ save and close
    def save(self):
        vals = self.values()
        rec = self.rec()
        got = None
        src = self.picks[0]["src"] if self.picks else {}
        if self.kind == "contact":
            card = dict(vals, sources=self.sources)
            cid = self.cid()
            if cid:
                CC.set_card(rec, cid, card)
                got = cid
            else:
                got = CC.save_card(rec, card)
            if not got:
                self.host.status("The card is empty: take or type at least one value.")
                return None
            diag.activity("capture_contact_card")
            self.host.toast("Contact filed in Customer information")
        else:
            from . import captureview as CV
            got = (CV.file_key_date if self.kind == "keydate" else CV.file_detail)(self.host, vals, src)
            if not got:
                return None
        self.mark(got)
        self.close_card()
        self.host.changed()
        return got

    def mark(self, got):
        """Every piece the card took words from carries the capture (its excerpt and its mark on the page)."""
        import excerpts as EX
        rec = self.rec()
        ref = got if isinstance(got, str) and got not in ("due",) else ""
        sids = []
        for p in self.picks:
            have = [x for x in EX.of_sentence(rec, p["sid"]) if x["bin"] == self.kind and (not ref or ref in x.get("refs", []))]
            if not have and p["parts"]:
                EX.add(rec, self.kind, p["parts"], ref=ref)
            sids.append(p["sid"])
        if sids:
            try:
                self.page.mark_rows(self.kind, sids)
                __import__("skqt.shredbar", fromlist=["x"]).capture_types(self.page, self.kind, sids)
                self.page.load_marks(); self.page.restyle()
            except Exception:
                diag.swallowed()
        return sids

    def cancel(self):
        self.close_card()
        return True

    def close_card(self):
        holder = getattr(self.page, "capture_holder", None)
        self.page.capture_card = None
        if holder is not None:
            holder.hide(); holder.setParent(None); holder.deleteLater()
        self.page.capture_holder = None
        try:
            self.page.show_card(self.page.selected())
        except Exception:
            diag.swallowed()


def open_card(page, kind, cid=None, ask=None):
    """Open the card at the top of the piece pane. With a card already open and changed, ask to save or drop it first
    (ask: tests, 'save', 'drop' or 'cancel'). Returns the card, or None."""
    cur = getattr(page, "capture_card", None)
    if cur is not None:
        if cur.dirty:
            if ask is None:
                b = QMessageBox.question(page, "A card is open", f"The {TITLES[cur.kind].lower()} card has values not filed. Save it first?",
                                         QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel, QMessageBox.Save)
                ask = {QMessageBox.Save: "save", QMessageBox.Discard: "drop"}.get(b, "cancel")
            if ask == "cancel":
                return None
            if ask == "save" and cur.save() is None:
                return None
        if getattr(page, "capture_card", None) is not None:
            page.capture_card.close_card()
    card = CaptureCard(page, kind, cid)
    holder = QScrollArea(); holder.setWidgetResizable(True); holder.setFrameShape(QFrame.NoFrame)
    holder.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
    holder.setWidget(card)
    holder.setMinimumHeight(220)
    page.right.insertWidget(0, holder)
    sizes = page.right.sizes()
    if len(sizes) == 3:
        total = sum(sizes)
        page.right.setSizes([int(total * 0.45), int(total * 0.3), total - int(total * 0.45) - int(total * 0.3)])
    page.capture_card, page.capture_holder = card, holder
    diag.activity("capture_card_opened")
    return card


def closing(page):
    """Shred is closing (or the effort changes): a card left open is dropped."""
    if getattr(page, "capture_card", None) is not None:
        page.capture_card.close_card()
