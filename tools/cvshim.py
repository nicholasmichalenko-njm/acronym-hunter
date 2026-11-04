"""The slice of OpenCV's interface the app calls, answered by imgops (NumPy + Pillow). For the side-by-side only:
it lets the app's own reading code run unchanged with OpenCV swapped out (module.cv2 = cvshim)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import imgops as IO

IMREAD_COLOR, IMREAD_GRAYSCALE, IMREAD_UNCHANGED = 1, 0, -1
COLOR_BGR2GRAY, COLOR_RGB2GRAY, COLOR_GRAY2BGR, COLOR_GRAY2RGB, COLOR_BGR2RGB, COLOR_RGB2BGR = 6, 7, 8, 8, 4, 4
BORDER_CONSTANT = 0
INTER_LINEAR, INTER_CUBIC = 1, 2
ADAPTIVE_THRESH_MEAN_C = 0
THRESH_BINARY_INV, THRESH_OTSU = 1, 8
MORPH_RECT, MORPH_OPEN = 0, 2
RETR_EXTERNAL, CHAIN_APPROX_SIMPLE = 0, 2
_MODES = {IMREAD_COLOR: "color", IMREAD_GRAYSCALE: "gray", IMREAD_UNCHANGED: "unchanged"}


def imdecode(buf, flag):
    return IO.imdecode(np.asarray(buf, np.uint8).tobytes(), _MODES[flag])


def imencode(ext, img, params=None):
    if ext.lower() != ".png":
        raise NotImplementedError(ext)
    return True, np.frombuffer(IO.imencode_png(img), np.uint8)


def imwrite(path, img):
    return IO.imwrite_png(path, img)


def copyMakeBorder(img, t, b, l, r, kind, value=0):
    assert t == b == l == r and kind == BORDER_CONSTANT
    v = value if np.isscalar(value) else value[0]
    return IO.border(img, t, v)


def cvtColor(img, code):
    if code in (COLOR_BGR2GRAY,):
        return IO.bgr2gray(img)
    if code == COLOR_RGB2GRAY:
        return IO.rgb2gray(img)
    if code == COLOR_GRAY2BGR:
        return IO.gray2bgr(img)
    if code == COLOR_BGR2RGB:
        return IO.swap_rb(img)
    raise NotImplementedError(code)


def resize(img, dsize, fx=None, fy=None, interpolation=INTER_LINEAR):
    cubic = interpolation == INTER_CUBIC
    if dsize:
        return IO.resize(img, size=dsize, cubic=cubic)
    return IO.resize(img, fx=fx, fy=fy, cubic=cubic)


class _Clahe:
    def __init__(self, clipLimit=40.0, tileGridSize=(8, 8)):
        self.clip, self.tiles = clipLimit, tileGridSize

    def apply(self, gray):
        return IO.clahe(gray, self.clip, self.tiles)


def createCLAHE(clipLimit=40.0, tileGridSize=(8, 8)):
    return _Clahe(clipLimit, tileGridSize)


def fastNlMeansDenoising(*a, **k):
    raise NotImplementedError("noise removal is not used with Tesseract (US editions)")


def adaptiveThreshold(gray, maxval, method, kind, block, c):
    assert maxval == 255 and method == ADAPTIVE_THRESH_MEAN_C and kind == THRESH_BINARY_INV
    return IO.adaptive_mean_inv(gray, block, c)


def threshold(gray, t, maxval, kind):
    assert kind == THRESH_BINARY_INV + THRESH_OTSU and maxval == 255
    return IO.otsu_inv(gray)


def getStructuringElement(shape, size):
    return np.ones((size[1], size[0]), np.uint8)


def morphologyEx(img, op, kernel):
    assert op == MORPH_OPEN and kernel.all()
    return IO.open_(img, kernel.shape[1], kernel.shape[0])


def dilate(img, kernel):
    assert kernel.all()
    return IO.dilate(img, kernel.shape[1], kernel.shape[0])


def bitwise_or(a, b):
    return np.bitwise_or(a, b)


def countNonZero(a):
    return int(np.count_nonzero(a))


def convertScaleAbs(a, alpha=1.0):
    return IO.scale_abs(a, alpha)


def findContours(bitmap, mode, method):
    assert mode == RETR_EXTERNAL
    return [b for b in IO.outer_boxes(bitmap)], None


def boundingRect(c):
    return c
