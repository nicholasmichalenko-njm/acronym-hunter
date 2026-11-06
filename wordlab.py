"""Apply in Word lab (3.67.0, Template Studio decision 4; production suite decisions 1, 2 and the spine): the team's
banned phrases put into a draft as tracked changes the author accepts or rejects in Word.

Two tiers. A person reviews every change first: each found phrase with its replacement, ticked when the list gives a
plain replacement (a few words, not advice), edited or unticked as they like.
  On a copy (the default): a dated copy of the draft beside it with the ticked changes as tracked changes, each with a
      comment naming the rule (Technical Edit's writer). No Word needed; the draft is only read. A fixed copy from Fix a
      Copy can also be compared with its draft in Word (wordcompare), so the author gets the formatting fixes as
      tracked changes too.
  Live in Word (opt-in, this session only): the ticked changes go into the document already open in Word, through
      Word's own window: tracked changes are switched on for the changes and set back after, each change gets a
      comment, and every change is logged in the effort record. Stationkeeper never saves, closes or writes the file;
      the author saves in Word. A place whose words changed since they were read is skipped and logged as skipped.

find(paragraphs, items) -> [change]      a change: {para, start, end, hit, fix, on, rule, why, level, sentence}
to_copy(src, changes, out) -> counts     open_documents() / read_open(full) / apply_open(full, text, changes)
log(rec, file, changes, results)         every live change in rec.data["word_live"]. Rules only; nothing leaves the PC."""
import datetime, json, os, re, subprocess, sys, tempfile

ADVICE = ("say ", "name ", "describe ", "state ", "commit ", "a ", "an ", "the ", "measured", "proof", "rewrite", "split",
          "fill ", "check ", "use spacing")
MAX_FIX_WORDS = 3


def plain_fix(use):
    """True when the list's 'Use instead' is replacement words, not advice: a few words that do not tell you what to do."""
    u = " ".join((use or "").split())
    if not u or len(u.split()) > MAX_FIX_WORDS or "," in u or "(" in u:
        return False
    return not any(u.lower().startswith(a) or a.strip() == u.lower() for a in ADVICE)


def _case_like(hit, new):
    """The replacement in the found words' case: Capitalized stays Capitalized, CAPITALS stay CAPITALS."""
    if hit.isupper() and len(hit) > 1:
        return new.upper()
    if hit[:1].isupper():
        return new[:1].upper() + new[1:]
    return new


def _sentence(text, a):
    s = max(text.rfind(". ", 0, a), text.rfind("\n", 0, a))
    e = text.find(". ", a)
    return " ".join(text[s + 1:(e + 1 if e != -1 else len(text))].split())[:240]


def find(paragraphs, items=None):
    """Every banned or avoided phrase in the paragraphs, in reading order. Ticked (on) when the list gives a plain
    replacement; a phrase inside a longer one already found is left out."""
    import banned as BN
    items = BN.load() if items is None else items
    pats = [(it, BN.pattern(it["Phrase"])) for it in items if it.get("Phrase")]
    out = []
    for i, text in enumerate(paragraphs):
        taken = []
        for it, rx in pats:
            for m in rx.finditer(text or ""):
                if any(a <= m.start() and m.end() <= b for a, b in taken):
                    continue
                taken.append((m.start(), m.end()))
                use = it.get("Use instead", "")
                ok = plain_fix(use)
                out.append({"para": i, "start": m.start(), "end": m.end(), "hit": m.group(0),
                            "fix": _case_like(m.group(0), use) if ok else "", "advice": "" if ok else use, "on": ok,
                            "rule": it["Phrase"], "why": it.get("Why", ""), "level": it.get("Level", "Avoid"),
                            "sentence": _sentence(text, m.start())})
    out.sort(key=lambda c: (c["para"], c["start"]))
    return out


# ---------------------------------------------------------------- tier 2: a copy
def docx_paragraphs(path):
    """The draft's body paragraphs as Technical Edit's writer counts them (deleted text left out)."""
    import zipfile
    from lxml import etree
    import techeditdocx as TD
    with zipfile.ZipFile(path) as z:
        root = etree.fromstring(z.read("word/document.xml"), parser=TD._parser())
    W = TD.W
    return ["".join(x.text or "" for x in p.iter(W + "t") if not any(a.tag == W + "del" for a in x.iterancestors()))
            for p in root.iter(W + "p")]


def copy_path(src, when=None):
    when = when or datetime.datetime.now()
    stem = os.path.splitext(os.path.basename(src))[0]
    return os.path.join(os.path.dirname(src), f"{stem} - banned phrases {when.strftime('%Y-%m-%d %H%M')}.docx")


def to_copy(src, changes, out_path=None, author="Stationkeeper", when=None):
    """The ticked changes as tracked changes in a new copy; the unticked ones as comments only when they have advice.
    Returns {"path", "changes", "comments", "skipped"}."""
    import techeditdocx as TD
    out_path = out_path or copy_path(src, when)
    fs = []
    for c in changes:
        if c.get("on") and c.get("fix"):
            fix = c["fix"]
        elif c.get("advice"):
            fix = c["advice"]                         # advice: a comment on the words, nothing changed
        else:
            continue
        fs.append({"para": c["para"], "start": c["start"], "end": c["end"] if c.get("on") else c["start"], "hit": c["hit"],
                   "fix": fix if c.get("on") else "", "rule": "banned", "title": f"Banned phrase: {c['rule']}",
                   "why": (c.get("why") or "") + (f" Use instead: {c['advice']}." if c.get("advice") and not c.get("on") else "")})
    res = TD.write(src, fs, out_path, author=author, when=when)
    res["path"] = out_path
    return res


# ---------------------------------------------------------------- tier 3: live, in Word's open window
_ATTACH = r"""
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$out = @{ ok = $false }
try {
  $app = [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
} catch { $out.why = 'not running'; $out | ConvertTo-Json -Compress; exit }
"""

_LIST = _ATTACH + r"""
$docs = @()
foreach ($d in $app.Documents) { $docs += @{ name = $d.Name; full = $d.FullName; saved = $d.Saved; track = $d.TrackRevisions; ro = $d.ReadOnly } }
$out.docs = $docs; $out.ok = $true
$out | ConvertTo-Json -Compress -Depth 4
"""

_READ = _ATTACH + r"""
$d = $null
foreach ($x in $app.Documents) { if ($x.FullName -eq $env:SK_DOC) { $d = $x } }
if ($d -eq $null) { $out.why = 'not open' } else {
  $out.text = $d.Content.Text; $out.track = $d.TrackRevisions; $out.ok = $true }
$out | ConvertTo-Json -Compress -Depth 4
"""

# each change: { old, new, k (which match of old in the main text, from 0), ctx (the words before it and old), note };
# applied last to first so earlier places stay where they were. Never Save, Close or Quit.
_APPLY = _ATTACH + r"""
$d = $null
foreach ($x in $app.Documents) { if ($x.FullName -eq $env:SK_DOC) { $d = $x } }
if ($d -eq $null) { $out.why = 'not open'; $out | ConvertTo-Json -Compress; exit }
if ($d.ReadOnly) { $out.why = 'read only'; $out | ConvertTo-Json -Compress; exit }
$plan = Get-Content -Raw -Encoding UTF8 -Path $env:SK_PLAN | ConvertFrom-Json
$was = $d.TrackRevisions
$res = @()
try {
  $d.TrackRevisions = $true
  foreach ($c in $plan) {
    $r = $d.Content
    $f = $r.Find; $f.ClearFormatting()
    $f.Text = ($c.old -replace '\^', '^^'); $f.MatchCase = $true; $f.Forward = $true; $f.Wrap = 0; $f.MatchWildcards = $false
    $f.MatchWholeWord = (-not $c.old.Contains(' '))
    $hit = $false
    for ($i = 0; $i -le [int]$c.k; $i++) { $hit = $f.Execute(); if (-not $hit) { break } }
    if (-not $hit) { $res += @{ id = $c.id; done = $false; why = 'not found' }; continue }
    $pt = $d.Range($r.Paragraphs(1).Range.Start, $r.End).Text
    if (-not $pt.EndsWith($c.ctx)) { $res += @{ id = $c.id; done = $false; why = 'moved' }; continue }
    $r.Text = $c.new
    try { [void]$d.Comments.Add($r, $c.note) } catch {}
    $res += @{ id = $c.id; done = $true }
  }
  $out.ok = $true
} catch {
  $out.why = "$($_.Exception.HResult)"
} finally {
  try { $d.TrackRevisions = $was } catch {}
}
$out.results = $res; $out.track_was = $was
$out | ConvertTo-Json -Compress -Depth 4
"""

WHY = {"not running": "Word is not open. Open the document in Word first.",
       "not open": "That document is no longer open in Word.",
       "read only": "Word has the document open read-only; open it for editing first."}


def available():
    return sys.platform.startswith("win")


def _run(script, env=None, runner=None, timeout=300):
    cmd = ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script]
    env = dict(os.environ, **(env or {}))
    try:
        if runner is not None:
            text = runner(cmd, env, timeout)
        else:
            r = subprocess.run(cmd, env=env, capture_output=True, timeout=timeout,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            text = r.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        return {"ok": False, "why": "Word took too long to answer."}
    except OSError as e:
        return {"ok": False, "why": f"Windows PowerShell could not start ({type(e).__name__})."}
    try:
        res = json.loads(next(x for x in reversed((text or "").strip().splitlines()) if x.startswith("{")))
    except (StopIteration, ValueError):
        return {"ok": False, "why": "Word did not answer."}
    if not res.get("ok"):
        res["why"] = WHY.get(res.get("why"), "Word could not do it" + (f" (code {res.get('why')})." if res.get("why") else "."))
    return res


def open_documents(runner=None):
    """The documents open in the person's Word: [{"name", "full", "saved", "track", "ro"}]."""
    if runner is None and not available():
        return {"ok": False, "why": "Word on Windows is needed to change a document live."}
    res = _run(_LIST, runner=runner, timeout=60)
    if res.get("ok"):
        docs = res.get("docs") or []
        res["docs"] = [docs] if isinstance(docs, dict) else docs
    return res


def read_open(full, runner=None):
    """The open document's main text as Word has it now: {"ok", "text", "paragraphs", "track"}."""
    res = _run(_READ, {"SK_DOC": full}, runner=runner, timeout=120)
    if res.get("ok"):
        res["paragraphs"] = [p.replace("\x07", "") for p in (res.get("text") or "").split("\r")]
    return res


def _count_before(text, hit, pos):
    """How many times Word's Find (case kept; whole words for a single word) meets hit before pos."""
    rx = re.compile((r"(?<![\w])" + re.escape(hit) + r"(?![\w])") if " " not in hit else re.escape(hit))
    return sum(1 for m in rx.finditer(text[:pos + len(hit)]) if m.start() < pos)


def live_plan(text, changes, author_note="Stationkeeper"):
    """The ticked changes as Word will apply them, last to first."""
    paras = text.split("\r")
    offs, o = [], 0
    for p in paras:
        offs.append(o); o += len(p) + 1
    plan = []
    for n, c in enumerate(changes):
        if not (c.get("on") and c.get("fix")) or c["para"] >= len(paras):
            continue
        pos = offs[c["para"]] + c["start"]
        if text[pos:pos + len(c["hit"])] != c["hit"]:
            continue
        before = paras[c["para"]][max(0, c["start"] - 30):c["start"]].replace("\x07", "")
        plan.append({"id": n, "old": c["hit"], "new": c["fix"], "k": _count_before(text, c["hit"], pos), "ctx": before + c["hit"],
                     "note": f"Banned phrase: {c['rule']}. {c.get('why', '')}".strip() + f" ({author_note})", "pos": pos})
    plan.sort(key=lambda x: -x["pos"])
    return plan


def apply_open(full, text, changes, runner=None):
    """Puts the ticked changes into the open document as tracked changes with comments. Never saves it. Returns
    {"ok", "applied", "skipped", "results": [{id, done, why}], "track_was"}."""
    plan = live_plan(text, changes)
    if not plan:
        return {"ok": False, "why": "No ticked change with replacement words to make."}
    fd, path = tempfile.mkstemp(prefix="sk_live_", suffix=".json")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump([{k: v for k, v in p.items() if k != "pos"} for p in plan], f)
        res = _run(_APPLY, {"SK_DOC": full, "SK_PLAN": path}, runner=runner, timeout=900)
    finally:
        try:
            os.remove(path)
        except OSError:
            pass
    rs = res.get("results") or []
    rs = [rs] if isinstance(rs, dict) else rs
    res["results"] = rs
    res["applied"] = sum(1 for r in rs if r.get("done"))
    res["skipped"] = sum(1 for r in rs if not r.get("done"))
    return res


def log(rec, file, changes, res, who=None, when=None):
    """Every live change kept in the effort record: when, file, old, new, rule, done or why not."""
    when = (when or datetime.datetime.now()).strftime("%Y-%m-%d %H:%M")
    done = {r.get("id"): r for r in res.get("results") or []}
    book = rec.data.setdefault("word_live", [])
    for n, c in enumerate(changes):
        if n in done:
            r = done[n]
            book.append({"when": when, "file": os.path.basename(file), "old": c["hit"], "new": c["fix"], "rule": c["rule"],
                         "done": bool(r.get("done")), "why": r.get("why", "")})
    rec.log("effort", f"Apply in Word: {res.get('applied', 0)} change(s) as tracked changes in {os.path.basename(file)}"
            + (f", {res.get('skipped')} skipped" if res.get("skipped") else ""), who=who)
    rec.save()
    return book
