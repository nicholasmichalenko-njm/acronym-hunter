"""2.48.0 the effort picture on Effort home: Choose a picture copies it into the effort's own folder (made smaller,
PNG), Effort home shows it left of the effort's name, an effort package carries it, Remove takes it away."""
import os, sys, tempfile, zipfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
os.environ["AH_OCR_ENGINE"] = "tesseract"
os.environ["AH_TEST"] = "1"
import app_gui as A, effort as E
from tkinter import messagebox
from PIL import Image
tmp = tempfile.mkdtemp()
A.CONFIG_DIR = os.path.join(tmp, "config"); A.CHOICES_FILE = os.path.join(tmp, "config", "choices.json")
A.SETTINGS_FILE = os.path.join(tmp, "settings.json")
for n in ("showinfo", "showwarning", "showerror"):
    setattr(messagebox, n, lambda *a, **k: None)
messagebox.askyesno = lambda *a, **k: True
LIST = os.path.join(tmp, "Kestrel", "Kestrel_Effort_List.xlsx")
PIC = os.path.join(tmp, "patch.jpg")
Image.new("RGB", (2400, 1600), (30, 60, 140)).save(PIC, "JPEG")
checks = []


def check(name, ok, info=""):
    checks.append(bool(ok)); print("PASS" if ok else "FAIL", name, info)


app = A.AcronymAppGUI()
app.geometry("1400x900+0+0")


def go():
    L = E.EffortList(LIST, "Kestrel"); L.pending = True; L.save()
    app.efforts.put("Kestrel", path=LIST)
    app.open_effort("Kestrel"); app.shell_go("home"); app.update()
    check("Effort home has a picture spot that invites a picture", "picture" in app.ep_label.cget("text").lower())
    dst = app.effort_picture_set(PIC); app.update()
    im = Image.open(dst)
    check("the picture is copied into the effort's folder as a smaller PNG", dst and os.path.dirname(dst) == app.ws.root
          and im.format == "PNG" and max(im.size) == 800, (dst, im.size))
    app.shell_overview_refresh(); app.update()
    check("Effort home shows it", app._ep_img is not None and app.ep_label.cget("text") == "")
    man = app.pkg_save_dialog(path=os.path.join(tmp, "out", "Kestrel"), customer=False, volumes=False)
    with zipfile.ZipFile(man["path"]) as z:
        check("an effort package carries it", any(n.endswith("effort picture.png") for n in z.namelist()))
    app.effort_picture_remove(); app.update()
    check("Remove takes it away", not os.path.exists(dst) and app._ep_img is None)
    n = sum(checks)
    print(f"GUI EFFORTPIC PASS ({n}/{len(checks)})" if n == len(checks) else f"GUI EFFORTPIC FAIL ({n}/{len(checks)})")
    app.after(300, app.destroy)


app.after(400, go)
app.mainloop()
