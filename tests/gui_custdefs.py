"""Customer documents outrank the database; conflicts ask for a choice; Add to effort list keeps the customer wording."""
import os, sys, tempfile, shutil
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["AH_OCR_ENGINE"] = "tesseract"
import app_gui as A, effort as E
from openpyxl import Workbook
from tkinter import simpledialog, messagebox
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "choices.json")
cust = os.path.join(tmp, "customer"); os.makedirs(cust)
shutil.copy(os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Program_Manual.pdf"), cust)
wb = Workbook(); ws = wb.active; ws.title = "Acronym List"
for r in (["SOW", "Scope of Work"], ["TRL", "Technology Readiness Level"], ["SAFETY", "not a term"]):
    ws.append(r)
wb.save(os.path.join(cust, "RFP_Attachment_J2.xlsx"))
wb2 = Workbook(); ws2 = wb2.active; ws2.title = "Glossary"; ws2.append(["SOW", "Statement of Work"]); ws2.append(["CDRL", "Contract Data Requirements List"])
wb2.save(os.path.join(cust, "RFP_Section_J.xlsx"))
LIST = os.path.join(tmp, "Kestrel_Effort_List.xlsx")
app = A.AcronymAppGUI()
def go():
    w = app.new_effort_dialog(); api = w._api
    api["name"].insert(0, "Kestrel"); api["path"].delete(0, "end"); api["path"].insert(0, LIST)
    api["dirs"]["customer_dir"].insert(0, cust); api["ok"]()
    app.start_batch([os.path.join(A.BASE_DIR, "test_samples", "Kestrel_Technical_Volume.docx")]); app.after(500, wait)
def wait():
    if app.btn_cancel.winfo_ismapped():
        app.after(500, wait); return
    print("cust files:", app.customer_files(), app.efforts.get("Kestrel")); import traceback
    try: print("defs:", sorted(app.customer_definitions())[:12])
    except Exception: traceback.print_exc()
    for t in ("SOW", "TRL", "SE&I", "LEO", "SRR", "KES"):
        d = app.results.get(t)
        if d: print(f"{t:5} {d['status'][:40]:42} | {d['selected_definition'][:45]}")
    print("needs-choice filter count:", sum(1 for d in app.results.values() if d['status'].startswith('⚠️')))
    app.tree.selection_set("SOW"); app.update()
    print("combo:", app.combo.cget("values"))
    app.combo.set("Statement of Work"); app.apply_choice()
    print("after choice:", app.results["SOW"]["status"], "|", app.results["SOW"]["selected_definition"])
    app.add_to_effort(["SOW", "TRL"])
    L = E.EffortList(LIST).load()
    for t in ("SOW", "TRL"):
        r = L.rows[t]; print(t, "|", r["Definition"], "|", r["Source"], "|", r["Customer document"][:40], "|", r["Customer wording"][:50], "| other:", r["Other definitions"])
    app.preview.show("SOW"); app.update(); print("preview info:", app.preview.lbl_math.cget("text")[:120].replace("\n", " / "))
    app.destroy()
app.after(1500, go); app.mainloop()
