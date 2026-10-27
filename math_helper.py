"""Stationkeeper math reader (optional add-on): reads equation pictures with IBM Granite-Docling-258M.

Runs only inside the app's no-network Windows sandbox (AppContainer with no capabilities); the app refuses to start
it otherwise. Input on stdin, one JSON object:
    {"items": [{"id": "...", "png": "<base64 PNG>"}, ...]}
Output on stdout, one JSON line per item, as soon as it is read:
    {"id": "...", "formulas": ["\\Delta v = ...", ...], "sec": 5.2}
plus a first line {"ready": true, "load_sec": ...} once the model is loaded, or {"error": "..."}.

Safety: the model loads only from models\\granite next to this program, only from safetensors files (no pickle),
after checking every file's SHA-256 against math_models.json. Hugging Face offline mode is forced; nothing is
downloaded, and the sandbox blocks the network regardless."""
import os, sys
for k, v in {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_DATASETS_OFFLINE": "1", "HF_HUB_DISABLE_TELEMETRY": "1",
             "TOKENIZERS_PARALLELISM": "false", "DO_NOT_TRACK": "1"}.items():
    os.environ[k] = v
import base64, hashlib, io, json, re, time

HERE = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, "frozen", False) else __file__))
MODEL_DIR = os.path.join(HERE, "models", "granite")
MANIFEST = os.path.join(HERE, "math_models.json")

def emit(obj):
    sys.stdout.write(json.dumps(obj, ensure_ascii=False) + "\n"); sys.stdout.flush()

def verify():
    man = json.load(open(MANIFEST, encoding="utf-8"))
    for name, want in man["files"].items():
        h = hashlib.sha256()
        with open(os.path.join(MODEL_DIR, name), "rb") as f:
            for chunk in iter(lambda: f.read(1 << 22), b""):
                h.update(chunk)
        if h.hexdigest().upper() != want.upper():
            raise RuntimeError(f"model file {name} does not match math_models.json (SHA-256)")
    extra = set(os.listdir(MODEL_DIR)) - set(man["files"])
    if any(e.endswith((".bin", ".pt", ".pth", ".pkl", ".ckpt")) for e in extra):
        raise RuntimeError("unexpected pickle-format model file in models\\granite")
    return man

def main():
    try:
        req = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
        t0 = time.perf_counter()
        man = verify()
        import torch
        from PIL import Image
        from transformers import AutoProcessor, AutoModelForImageTextToText
        torch.set_num_threads(max(1, int(req.get("threads") or os.cpu_count() or 4)))
        proc = AutoProcessor.from_pretrained(MODEL_DIR, local_files_only=True, use_fast=False)
        model = AutoModelForImageTextToText.from_pretrained(MODEL_DIR, local_files_only=True, use_safetensors=True,
                                                            dtype=torch.float32).eval()
        emit({"ready": True, "load_sec": round(time.perf_counter() - t0, 1), "model": man.get("model", "")})
    except Exception as e:
        emit({"error": f"{type(e).__name__}: {e}"}); return 2
    formula_prompt = proc.apply_chat_template(
        [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Convert formula to LaTeX."}]}],
        add_generation_prompt=True)
    page_prompt = proc.apply_chat_template(
        [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": "Convert this page to docling."}]}],
        add_generation_prompt=True)
    for item in req.get("items", []):
        t1 = time.perf_counter()
        try:
            img = Image.open(io.BytesIO(base64.b64decode(item["png"]))).convert("RGB")
            w, h = img.size
            single = h <= 260 or (w / max(h, 1) >= 2.5 and h <= 500)    # a cropped equation, not a whole figure
            proc.image_processor.do_image_splitting = not single          # splitting only helps whole figures
            prompt = formula_prompt if single else page_prompt
            inputs = proc(text=prompt, images=[img], return_tensors="pt")
            with torch.inference_mode():
                extra = {"stop_strings": ["</formula>"], "tokenizer": proc.tokenizer} if single else {}
                ids = model.generate(**inputs, max_new_tokens=300 if single else 1200, do_sample=False, **extra)
            txt = proc.batch_decode(ids[:, inputs["input_ids"].shape[1]:], skip_special_tokens=False)[0]
            txt = re.sub(r"<loc_\d+>", "", txt)
            found = [" ".join(f.split()) for f in re.findall(r"<formula>(.*?)</formula>", txt, re.S)]
            if single and not found:
                plain = " ".join(re.sub(r"<[^>]+>", " ", txt).split())
                found = [plain] if plain else []
            emit({"id": item.get("id"), "formulas": [f for f in found if f], "sec": round(time.perf_counter() - t1, 1)})
        except Exception as e:
            emit({"id": item.get("id"), "error": f"{type(e).__name__}: {e}", "sec": round(time.perf_counter() - t1, 1)})
    return 0

if __name__ == "__main__":
    sys.exit(main())
