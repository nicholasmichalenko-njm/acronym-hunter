"""docTR text finder + reader for Stationkeeper, run on ONNX Runtime.

Models: Mindee's docTR db_mobilenet_v3_large (finds text) and crnn_vgg16_bn (reads it), Apache 2.0, exported to
ONNX by this project from Mindee's official weights (see doctr_models.json for weight and file SHA-256).
Dependencies: onnxruntime, numpy, opencv. No downloads, no network code: models load from a local folder only.

Called like the app's other engines:
    eng(img_bgr) -> ([[box, text, confidence 0-1], ...], None)     one entry per text line
Pre- and post-processing follow docTR/OnnxTR (DBNet probability map, box expansion ratio 1.5, CTC best path).
Extra passes the app adds: tiles for large pictures, an inverted pass for dark pictures, and 90/270 degree passes
for vertical labels."""
import json, math, os
import diag
import numpy as np
import cv2

DET_SIZE = 1024
BIN_THRESH, BOX_THRESH, UNCLIP = 0.3, 0.1, 1.5
RECO_H, RECO_W = 32, 128
SPLIT_RATIO, TARGET_RATIO = 8.4, 6.0     # docTR splits very wide word boxes before reading them


class DocTREngine:
    def __init__(self, folder, threads=None):
        import onnxruntime as ort
        try:
            ort.disable_telemetry_events()        # ONNX Runtime's Windows event tracing off
        except Exception:
            diag.swallowed()
            pass
        info = json.load(open(os.path.join(folder, "doctr_models.json"), encoding="utf-8"))
        so = ort.SessionOptions()
        so.intra_op_num_threads = threads or max(1, min(8, (os.cpu_count() or 4)))
        so.log_severity_level = 3
        d, r = info["models"]["doctr_det"], info["models"]["doctr_reco"]
        self.det = ort.InferenceSession(os.path.join(folder, d["onnx"]), so, providers=["CPUExecutionProvider"])
        self.reco = ort.InferenceSession(os.path.join(folder, r["onnx"]), so, providers=["CPUExecutionProvider"])
        self.det_in, self.reco_in = self.det.get_inputs()[0].name, self.reco.get_inputs()[0].name
        self.det_mean, self.det_std = np.array(d["mean"], np.float32), np.array(d["std"], np.float32)
        self.reco_mean, self.reco_std = np.array(r["mean"], np.float32), np.array(r["std"], np.float32)
        self.vocab = r["vocab"]
        self.info = info

    # ---------- finding ----------
    def detect(self, rgb):
        """Straight word boxes (x0, y0, x1, y1, score) in pixel coordinates of rgb."""
        h, w = rgb.shape[:2]
        s = DET_SIZE / max(h, w)
        nh, nw = max(1, round(h * s)), max(1, round(w * s))
        canvas = np.zeros((DET_SIZE, DET_SIZE, 3), np.uint8)
        top, left = (DET_SIZE - nh) // 2, (DET_SIZE - nw) // 2
        canvas[top:top + nh, left:left + nw] = cv2.resize(rgb, (nw, nh), interpolation=cv2.INTER_LINEAR)
        x = ((canvas.astype(np.float32) / 255.0 - self.det_mean) / self.det_std).transpose(2, 0, 1)[None]
        logits = self.det.run(None, {self.det_in: x})[0]
        prob = 1.0 / (1.0 + np.exp(-np.squeeze(logits).astype(np.float32)))
        if prob.ndim == 3:   # (C, H, W) or (H, W, C): take the text channel
            prob = prob[0] if prob.shape[0] < prob.shape[-1] else prob[..., 0]
        bitmap = cv2.morphologyEx((prob >= BIN_THRESH).astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
        contours, _ = cv2.findContours(bitmap, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        boxes = []
        for c in contours:
            x0, y0, bw, bh = cv2.boundingRect(c)
            if bw < 2 or bh < 2:
                continue
            score = float(prob[y0:y0 + bh + 1, x0:x0 + bw + 1].mean())
            if score < BOX_THRESH:
                continue
            dist = (bw * bh) * UNCLIP / (2 * (bw + bh))       # docTR's polygon expansion, for a straight box
            bx0, by0, bx1, by1 = x0 - dist, y0 - dist, x0 + bw + dist, y0 + bh + dist
            bx0, bx1 = (bx0 - left) / s, (bx1 - left) / s
            by0, by1 = (by0 - top) / s, (by1 - top) / s
            bx0, by0 = max(0.0, bx0), max(0.0, by0)
            bx1, by1 = min(float(w), bx1), min(float(h), by1)
            if bx1 - bx0 >= 2 and by1 - by0 >= 2:
                boxes.append((bx0, by0, bx1, by1, score))
        return boxes

    # ---------- reading ----------
    def _prep_crop(self, crop):
        h, w = crop.shape[:2]
        if w / max(h, 1) > RECO_W / RECO_H:
            nw, nh = RECO_W, max(1, round(RECO_W * h / w))
        else:
            nh, nw = RECO_H, max(1, round(RECO_H * w / h))
        out = np.zeros((RECO_H, RECO_W, 3), np.uint8)
        out[:nh, :nw] = cv2.resize(crop, (nw, nh), interpolation=cv2.INTER_LINEAR)
        return ((out.astype(np.float32) / 255.0 - self.reco_mean) / self.reco_std).transpose(2, 0, 1)

    def _read_batch(self, crops):
        if not crops:
            return []
        out = []
        for i in range(0, len(crops), 64):
            x = np.stack([self._prep_crop(c) for c in crops[i:i + 64]])
            logits = self.reco.run(None, {self.reco_in: x})[0].astype(np.float32)
            if logits.shape[1] == len(self.vocab) + 1 and logits.shape[2] != len(self.vocab) + 1:
                logits = logits.transpose(0, 2, 1)                  # (N, C, T) -> (N, T, C)
            e = np.exp(logits - logits.max(axis=-1, keepdims=True))
            conf = (e / e.sum(axis=-1, keepdims=True)).max(axis=-1).min(axis=1)
            blank = len(self.vocab)
            for seq, cf in zip(logits.argmax(axis=-1), conf):
                chars, prev = [], None
                for k in seq.tolist():
                    if k != prev and k != blank and k < len(self.vocab):
                        chars.append(self.vocab[k])
                    prev = k
                out.append(("".join(chars), float(cf)))
        return out

    def read_words(self, rgb, boxes):
        """Read each box. Very wide boxes are split into overlapping pieces and joined, as docTR does."""
        crops, owners = [], []
        for bi, (x0, y0, x1, y1, _s) in enumerate(boxes):
            crop = rgb[int(y0):int(math.ceil(y1)), int(x0):int(math.ceil(x1))]
            if crop.size == 0:
                continue
            ch, cw = crop.shape[:2]
            if cw / max(ch, 1) > SPLIT_RATIO:
                step = int(TARGET_RATIO * ch); ov = int(0.3 * step)
                xs = list(range(0, max(1, cw - ov), max(1, step - ov)))
                for j, xa in enumerate(xs):
                    crops.append(crop[:, xa:min(cw, xa + step)]); owners.append((bi, j))
            else:
                crops.append(crop); owners.append((bi, 0))
        reads = self._read_batch(crops)
        words = {}
        for (bi, j), (txt, cf) in zip(owners, reads):
            if bi in words:
                prev, pc = words[bi]
                words[bi] = (_merge_overlap(prev, txt), min(pc, cf))
            else:
                words[bi] = (txt, cf)
        return [(boxes[bi][:4], t, c) for bi, (t, c) in words.items() if t.strip()]

    # ---------- one pass, lines ----------
    def _pass(self, rgb, boxes=None, keep=None):
        boxes = self.detect(rgb) if boxes is None else boxes
        if keep:
            boxes = [b for b in boxes if keep(b)]
        return _to_lines(self.read_words(rgb, boxes))

    def read(self, rgb, extra_passes=True):
        """All lines in an RGB picture, with the app's extra passes.
        Returns [(box4pts, text, line confidence, [(word, confidence), ...])]."""
        h, w = rgb.shape[:2]
        lines, vertical = [], False
        if max(h, w) > 2500:                                     # tiles: small labels stay readable
            T, O = 1600, 200
            for y in range(0, h, T - O):
                for x in range(0, w, T - O):
                    for box, t, c, wc in self._pass(np.ascontiguousarray(rgb[y:y + T, x:x + T])):
                        lines.append(([[px + x, py + y] for px, py in box], t, c, wc))
        else:
            got = self._pass(rgb)
            # vertical labels come out of the normal pass as lone characters ("(", "3", "P"): read the page turned
            lone = [ln for ln in got if len(ln[1].replace(" ", "")) <= 1]
            vertical = len(lone) >= 3
            lines += [ln for ln in got if not (vertical and len(ln[1].replace(" ", "")) <= 1)]
        if extra_passes:
            if cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).mean() < 110:   # light text on a dark background
                lines += self._pass(255 - rgb)
            if vertical:
                wide = lambda b: (b[2] - b[0]) > 1.5 * (b[3] - b[1])   # horizontal in the turned page = vertical originally
                for k, back in ((1, _unrot90), (3, _unrot270)):
                    rot = np.ascontiguousarray(np.rot90(rgb, k))
                    for box, t, c, wc in self._pass(rot, keep=wide):
                        if len(t.replace(" ", "")) >= 2:
                            lines.append(([back(px, py, w, h) for px, py in box], t, c, wc))
        return lines

    def __call__(self, img, use_det=True, text_score=None, **_ignored):
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB) if img.ndim == 3 else cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
        if not use_det:
            got = self._read_batch([rgb])
            return ([[got[0][0], got[0][1]]] if got and got[0][0] else []), None
        floor = 0.0 if text_score is None else float(text_score)
        return [[ln[0], ln[1], ln[2]] for ln in self.read(rgb) if ln[2] >= floor], None


def _unrot90(px, py, w, h):    # point in np.rot90(img, 1) -> original
    return [w - 1 - py, px]

def _unrot270(px, py, w, h):   # point in np.rot90(img, 3) -> original
    return [py, h - 1 - px]

def _merge_overlap(a, b):
    for k in range(min(len(a), len(b)), 0, -1):
        if a.endswith(b[:k]):
            return a + b[k:]
    return a + b

def _to_lines(words):
    """Group word boxes into lines: same row (vertical overlap) and close together."""
    if not words:
        return []
    words = sorted(words, key=lambda wd: ((wd[0][1] + wd[0][3]) / 2, wd[0][0]))
    rows = []
    for wd in words:
        x0, y0, x1, y1 = wd[0]
        cy, hh = (y0 + y1) / 2, y1 - y0
        for row in rows:
            ry0, ry1 = row["y0"], row["y1"]
            if abs(cy - (ry0 + ry1) / 2) < 0.5 * max(hh, ry1 - ry0):
                row["w"].append(wd); row["y0"], row["y1"] = min(ry0, y0), max(ry1, y1); break
        else:
            rows.append({"y0": y0, "y1": y1, "w": [wd]})
    lines = []
    for row in rows:
        ws = sorted(row["w"], key=lambda wd: wd[0][0])
        group = [ws[0]]
        for wd in ws[1:]:
            gap = wd[0][0] - group[-1][0][2]
            if gap > 1.2 * (group[-1][0][3] - group[-1][0][1]):
                lines.append(_line(group)); group = [wd]
            else:
                group.append(wd)
        lines.append(_line(group))
    return lines

def _line(group):
    x0 = min(g[0][0] for g in group); y0 = min(g[0][1] for g in group)
    x1 = max(g[0][2] for g in group); y1 = max(g[0][3] for g in group)
    return ([[x0, y0], [x1, y0], [x1, y1], [x0, y1]], " ".join(g[1] for g in group), min(g[2] for g in group),
            [(g[1], g[2]) for g in group])
