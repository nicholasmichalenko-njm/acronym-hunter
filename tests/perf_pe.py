"""Scale check: a volume of about 1,000 pages (20 chapters, 240 tables of 25 rows, 480 captions with fields,
1,200 cross-references, 9,600 body paragraphs). Times the read map, the audit and the table classification."""
import os, sys, tempfile, time
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("SK_SANDBOX_TEMP", "temp_pe")
from prodengine.engine.pkg import Package, NS
from prodengine.engine.ordered import q
from prodengine.pe import rules as R, docmap as D, tables as T
from tests.pefix import fixtures_doc as F

b = F.Builder()
b.p("Contents", "TOC Heading")
b.field_span('TOC \\t "Heading 1,1,Heading 2,2,Heading 3,3,Heading 7,1,Heading 8,2" \\h \\z', [f"{i} Chapter\t{i}" for i in range(1, 21)], "TOC 1")
refs = 0
for ch in range(1, 21):
    b.p(f"Chapter {ch}", "Heading 1")
    for t in range(1, 13):
        for _ in range(40):
            b.p("The contractor will provide the service with a proven and traceable approach. " * 3)
        tb = b.table_with_caption(25, 4, "Table", str(ch), t, f"Data {ch}.{t}", bookmark=f"_Ref{ch:03d}{t:06d}")
        x = b.p("As shown in ")
        for k in range(5):
            b.field(x, f"REF _Ref{ch:03d}{t:06d} \\h \\* CHARFORMAT", f"Table {ch}-{t}"); refs += 1
            x.add_run(", ")
path = os.path.join(tempfile.mkdtemp(prefix="pe_perf_"), "big.docx")
t0 = time.perf_counter(); b.doc.save(path); print(f"built in {time.perf_counter() - t0:.1f}s, {os.path.getsize(path) / 1e6:.1f} MB")
std = R.resolve(R.COMPANY)
t0 = time.perf_counter(); pkg = Package(path); t_load = time.perf_counter() - t0
t0 = time.perf_counter(); dm = D.build(pkg, std); t_map = time.perf_counter() - t0
t0 = time.perf_counter(); fs = D.audit(dm, std); t_audit = time.perf_counter() - t0
root = pkg.tree(pkg.main)
names = T.style_name_map(pkg.tree(pkg.word_part("/styles")))
tbls = [t for t in root.iter(q("tbl")) if not any(True for _ in t.iterancestors(q("tbl")))]
t0 = time.perf_counter(); n_rows = sum(len(T.classify(t, std, "std", names)) for t in tbls); t_cls = time.perf_counter() - t0
print(dm.stats)
print(f"load {t_load:.1f}s | map {t_map:.1f}s | audit {t_audit:.2f}s ({len(fs)} findings) | classify {len(tbls)} tables, {n_rows} rows {t_cls:.1f}s")
# round 3: sections, lists and terms on the same volume
from prodengine.pe import sections as S, lists as L, terms as W
t0 = time.perf_counter(); sm = S.map_sections(pkg, std); sf = S.audit(sm, std); t_sec = time.perf_counter() - t0
t0 = time.perf_counter(); lm = L.scan(pkg, std); lf = L.audit(lm, std); t_lst = time.perf_counter() - t0
t0 = time.perf_counter(); hits = W.scan(pkg, std); t_trm = time.perf_counter() - t0
print(f"sections {t_sec:.2f}s ({len(sm.sections)} sections) | lists {t_lst:.1f}s ({len(lm.items)} items) | terms {t_trm:.1f}s ({len(hits)} hits)")
# round 4: font compliance on the same volume (rules set so every run is examined)
from prodengine.pe import fonts as Fo
std_f = R.resolve(R.COMPANY, effort={"fonts": {"body": {"min_size": 11, "fonts": ["Times New Roman"]}, "table": {"min_size": 9, "fonts": ["Arial"]}}})
t0 = time.perf_counter(); fr = Fo.scan(pkg, std_f); ff = Fo.audit(fr, std_f); t_f = time.perf_counter() - t0
print(f"fonts {t_f:.1f}s ({len(fr)} runs, {len(ff)} groups)")
