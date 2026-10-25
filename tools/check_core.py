"""Build gate for the Core edition: no generative AI, no language-model runtime, no model weights beyond the listed OCR models.

Usage:
    python tools\\check_core.py dist\\AcronymHunter          check a built folder
    python tools\\check_core.py --source                      check the app's own source imports
Exit code 0 = pass, 1 = fail.

Core may contain: Tesseract (eng.traineddata) and, unless built Classic, the two docTR ONNX files (non-generative
OCR models: they output characters and boxes). Everything generative ships only as a separate add-on
(math_addon, compliance assist), never inside Core.
"""
import ast, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FORBIDDEN_NAMES = re.compile(r"(^|[\\/_.\-])(torch|transformers|tokenizers|safetensors|accelerate|llama|ggml|gguf|"
                             r"onnxruntime[_-]genai|vllm|sentencepiece|bitsandbytes|huggingface|granite|math_addon|"
                             r"compliance_assist)([\\/_.\-]|$)", re.I)
FORBIDDEN_EXT = {".safetensors", ".gguf", ".pt", ".pth", ".ckpt", ".pkl"}
BIG_BIN = 10 * 1024 * 1024
FORBIDDEN_IMPORTS = {"torch", "transformers", "tokenizers", "safetensors", "accelerate", "llama_cpp", "onnxruntime_genai",
                     "vllm", "sentencepiece", "huggingface_hub"}
CORE_SOURCES = ["app_gui.py", "preview_pane.py", "trainer_gui.py", "symbol_picker.py", "help_guide.py", "doctr_engine.py",
                "equations.py", "sandbox.py", "tess_train.py", "feedback.py", "diag.py", "effort.py", "effort_ui.py", "custdefs.py", "volcheck.py", "volcheck_ui.py", "compliance.py", "compliance_ui.py", "complearn.py", "docxw.py", "workspace.py", "workspace_ui.py", "ai_stack.py", "ai_ui.py", "setupdoc.py", "setup_ui.py", "context.py", "effort_wizard.py", "effort_home.py"]


def check_folder(folder):
    problems = []
    for dp, _dn, fns in os.walk(folder):
        for fn in fns:
            p = os.path.join(dp, fn)
            rel = os.path.relpath(p, folder)
            ext = os.path.splitext(fn)[1].lower()
            if FORBIDDEN_NAMES.search(rel):
                problems.append(f"generative-AI component: {rel}")
            elif ext in FORBIDDEN_EXT:
                problems.append(f"model weights: {rel}")
            elif ext == ".bin" and os.path.getsize(p) > BIG_BIN:
                problems.append(f"large binary (possible model weights): {rel}")
    return problems


def check_source():
    problems = []
    for f in CORE_SOURCES:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        for node in ast.walk(ast.parse(open(p, encoding="utf-8").read())):
            names = []
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module:
                names = [node.module]
            for n in names:
                if n.split(".")[0] in FORBIDDEN_IMPORTS:
                    problems.append(f"{f}:{node.lineno}: imports {n}")
    return problems


def main(argv):
    if not argv:
        print(__doc__); return 2
    problems = check_source() if argv[0] == "--source" else check_folder(argv[0]) + check_source()
    for p in problems:
        print("  " + p)
    print("Core check passed: no generative AI runtime or model weights in Core." if not problems
          else f"CORE CHECK FAILED: {len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
