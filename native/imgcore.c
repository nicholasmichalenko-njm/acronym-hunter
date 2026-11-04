/* imgcore: the picture steps Stationkeeper's reading needs, in plain C, held to OpenCV's arithmetic.
 *
 * No network, no files, no allocation outside the buffers given (except small scratch). Each function works on
 * uint8 buffers laid out the way NumPy and OpenCV lay them out (rows, then columns, then channels).
 * imgops.py computes the tables (source indices and fixed-point weights) and calls these through ctypes; it keeps
 * a NumPy version of every step as the reference the tests compare against.
 *
 * Build (Windows, MSYS2 UCRT64):  gcc -O2 -ffp-contract=off -fno-fast-math -shared -o imgcore.dll imgcore.c
 * Build (Linux, for the tests):   gcc -O2 -ffp-contract=off -fno-fast-math -shared -fPIC -o imgcore.so imgcore.c -lm
 * -ffp-contract=off keeps every float multiply and add separate, as OpenCV's SSE code does them. */
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#if defined(__x86_64__) || defined(_M_X64) || defined(__i386__)
#include <emmintrin.h>
static inline int rint_even(float v) { return _mm_cvtss_si32(_mm_set_ss(v)); }   /* SSE: round half to even */
#else
static inline int rint_even(float v) { return (int)lrintf(v); }
#endif

#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API __attribute__((visibility("default")))
#endif

static inline uint8_t sat_u8(int v) { return (uint8_t)(v < 0 ? 0 : (v > 255 ? 255 : v)); }
static inline uint8_t sat_f(float v) { return sat_u8(rint_even(v)); }

API int imgcore_version(void) { return 1; }

/* ---------------------------------------------------------------- grey: (B*3735 + G*19235 + R*9798 + 16384) >> 15 */
API void gray_bgr(const uint8_t *src, int64_t n, uint8_t *dst)
{
    for (int64_t i = 0; i < n; i++, src += 3)
        dst[i] = (uint8_t)((src[0] * 3735u + src[1] * 19235u + src[2] * 9798u + 16384u) >> 15);
}

/* ---------------------------------------------------------------- resize, OpenCV's fixed-point path
 * xi/xw: for each output column, k source columns (already held to the edges) and their 11-bit weights.
 * yi/yw: the same for output rows. cubic=0: OpenCV's linear vertical step; cubic=1: OpenCV's cubic vertical step,
 * whose vector loop does the first (row width / lanes) * lanes values in float and the rest in fixed point. */
static void hrow(const uint8_t *s, int cn, int nw, int k, const int32_t *xi, const int32_t *xw, int32_t *d)
{
    if (k == 4 && cn == 1) {
        for (int x = 0; x < nw; x++) {
            const int32_t *ix = xi + 4 * x, *wx = xw + 4 * x;
            d[x] = s[ix[0]] * wx[0] + s[ix[1]] * wx[1] + s[ix[2]] * wx[2] + s[ix[3]] * wx[3];
        }
        return;
    }
    if (k == 4 && cn == 3) {
        for (int x = 0; x < nw; x++) {
            const int32_t *ix = xi + 4 * x, *wx = xw + 4 * x;
            const uint8_t *p0 = s + 3 * ix[0], *p1 = s + 3 * ix[1], *p2 = s + 3 * ix[2], *p3 = s + 3 * ix[3];
            int32_t w0 = wx[0], w1 = wx[1], w2 = wx[2], w3 = wx[3];
            int32_t *o = d + 3 * x;
            o[0] = p0[0] * w0 + p1[0] * w1 + p2[0] * w2 + p3[0] * w3;
            o[1] = p0[1] * w0 + p1[1] * w1 + p2[1] * w2 + p3[1] * w3;
            o[2] = p0[2] * w0 + p1[2] * w1 + p2[2] * w2 + p3[2] * w3;
        }
        return;
    }
    for (int x = 0; x < nw; x++) {
        const int32_t *ix = xi + (int64_t)x * k, *wx = xw + (int64_t)x * k;
        for (int c = 0; c < cn; c++) {
            int32_t acc = 0;
            for (int t = 0; t < k; t++) acc += (int32_t)s[(int64_t)ix[t] * cn + c] * wx[t];
            d[(int64_t)x * cn + c] = acc;
        }
    }
}

API int resize_fixed(const uint8_t *src, int h, int w, int cn, uint8_t *dst, int nh, int nw, int k,
                     const int32_t *xi, const int32_t *xw, const int32_t *yi, const int32_t *yw, int cubic, int lanes)
{
    int64_t width = (int64_t)nw * cn;
    int32_t *rows = (int32_t *)malloc(sizeof(int32_t) * width * k);
    int *have = (int *)malloc(sizeof(int) * k);
    if (!rows || !have) { free(rows); free(have); return -1; }
    for (int t = 0; t < k; t++) have[t] = -1;
    int64_t n = cubic ? (width / lanes) * lanes : 0;
    const float sc = 1.0f / (2048.0f * 2048.0f);
    int32_t *S[4];
    for (int dy = 0; dy < nh; dy++) {
        const int32_t *iy = yi + (int64_t)dy * k, *wy = yw + (int64_t)dy * k;
        for (int t = 0; t < k; t++) {             /* reuse a row already worked out, else work it out */
            int sy = iy[t], slot = -1;
            for (int u = 0; u < k; u++) if (have[u] == sy) { slot = u; break; }
            if (slot < 0) {
                for (int u = 0; u < k; u++) {     /* a free slot: one this output row does not use */
                    int used = 0;
                    for (int v = 0; v < k; v++) if (have[u] == iy[v]) { used = 1; break; }
                    if (!used) { slot = u; break; }
                }
                hrow(src + (int64_t)sy * w * cn, cn, nw, k, xi, xw, rows + (int64_t)slot * width);
                have[slot] = sy;
            }
            S[t] = rows + (int64_t)slot * width;
        }
        uint8_t *d = dst + (int64_t)dy * width;
        if (!cubic) {
            int32_t b0 = wy[0], b1 = wy[1];
            for (int64_t x = 0; x < width; x++)
                d[x] = sat_u8((((b0 * (S[0][x] >> 4)) >> 16) + ((b1 * (S[1][x] >> 4)) >> 16) + 2) >> 2);
        } else {
            float b0 = (float)wy[0] * sc, b1 = (float)wy[1] * sc, b2 = (float)wy[2] * sc, b3 = (float)wy[3] * sc;
            for (int64_t x = 0; x < n; x++) {
                float v = (float)S[3][x] * b3;
                v = (float)S[2][x] * b2 + v;
                v = (float)S[1][x] * b1 + v;
                v = (float)S[0][x] * b0 + v;
                d[x] = sat_f(v);
            }
            for (int64_t x = n; x < width; x++) {
                int64_t v = (int64_t)S[0][x] * wy[0] + (int64_t)S[1][x] * wy[1] + (int64_t)S[2][x] * wy[2] +
                            (int64_t)S[3][x] * wy[3];
                d[x] = sat_u8((int)((v + (1 << 21)) >> 22));
            }
        }
    }
    free(rows); free(have);
    return 0;
}

/* ---------------------------------------------------------------- contrast boost: CLAHE's blend between tiles
 * luts: (ty, tx, 256) float; per column x1, x2 (tile columns), xa, xa1; per row y1, y2, ya, ya1. */
API void clahe_blend(const uint8_t *src, int H, int W, int tx, const float *luts,
                     const int32_t *x1, const int32_t *x2, const float *xa, const float *xa1,
                     const int32_t *y1, const int32_t *y2, const float *ya, const float *ya1, uint8_t *dst)
{
    for (int y = 0; y < H; y++) {
        const float *L1 = luts + (int64_t)y1[y] * tx * 256, *L2 = luts + (int64_t)y2[y] * tx * 256;
        const uint8_t *s = src + (int64_t)y * W;
        uint8_t *d = dst + (int64_t)y * W;
        float wa1 = ya1[y], wa = ya[y];
        for (int x = 0; x < W; x++) {
            int v = s[x];
            const float *a1 = L1 + x1[x] * 256, *a2 = L1 + x2[x] * 256, *c1 = L2 + x1[x] * 256, *c2 = L2 + x2[x] * 256;
            float top = a1[v] * xa1[x] + a2[v] * xa[x];
            float bot = c1[v] * xa1[x] + c2[v] * xa[x];
            float res = top * wa1 + bot * wa;
            d[x] = sat_f(res);
        }
    }
}

/* ---------------------------------------------------------------- local threshold (mean of a block x block window)
 * dst = 255 where round(window sum / area) >= pixel + c (OpenCV's ADAPTIVE_THRESH_MEAN_C, THRESH_BINARY_INV),
 * border copied from the edge. thr[g] = area * (g + c) - (area - 1) / 2 is worked out by the caller. */
API int adaptive_mean_inv(const uint8_t *src, int H, int W, int block, const int64_t *thr, uint8_t *dst)
{
    int r = block / 2;
    int64_t *col = (int64_t *)calloc((size_t)W, sizeof(int64_t));   /* column sums over the current window rows */
    if (!col) return -1;
    #define PX(yy, xx) src[(int64_t)((yy) < 0 ? 0 : ((yy) >= H ? H - 1 : (yy))) * W + ((xx) < 0 ? 0 : ((xx) >= W ? W - 1 : (xx)))]
    for (int x = 0; x < W; x++) {
        int64_t s = 0;
        for (int yy = -r; yy <= r; yy++) s += PX(yy, x);
        col[x] = s;
    }
    for (int y = 0; y < H; y++) {
        if (y > 0) {
            for (int x = 0; x < W; x++) col[x] += (int64_t)PX(y + r, x) - PX(y - 1 - r, x);
        }
        int64_t s = 0;
        for (int xx = -r; xx <= r; xx++) s += col[xx < 0 ? 0 : (xx >= W ? W - 1 : xx)];
        for (int x = 0; x < W; x++) {
            if (x > 0) {
                int xa = x + r, xb = x - 1 - r;
                s += col[xa >= W ? W - 1 : xa] - col[xb < 0 ? 0 : xb];
            }
            dst[(int64_t)y * W + x] = s >= thr[src[(int64_t)y * W + x]] ? 255 : 0;
        }
    }
    #undef PX
    free(col);
    return 0;
}

/* ---------------------------------------------------------------- opening by a straight line, by whole runs
 * axis 1: along rows; axis 0: down columns. Keeps runs at least k long (k - k/2 touching the start edge,
 * k/2 + 1 touching the end edge, any length touching both); an even k moves the kept run one cell on. */
API void open_line(const uint8_t *src, int H, int W, int k, int axis, uint8_t on, uint8_t *dst)
{
    int a = k / 2, sh = 2 * a - k + 1;
    int lines = axis == 1 ? H : W, len = axis == 1 ? W : H;
    int64_t step = axis == 1 ? 1 : W;
    memset(dst, 0, (size_t)H * W);
    for (int l = 0; l < lines; l++) {
        const uint8_t *s = src + (axis == 1 ? (int64_t)l * W : l);
        uint8_t *d = dst + (axis == 1 ? (int64_t)l * W : l);
        int i = 0;
        while (i < len) {
            if (!s[i * step]) { i++; continue; }
            int b = i;
            while (i < len && s[i * step]) i++;
            int e = i, at_s = b == 0, at_e = e == len;
            int need = at_s && at_e ? 0 : (at_s ? k - a : (at_e ? a + 1 : k));
            if (e - b < need) continue;
            int b2 = at_s ? 0 : b + sh, e2 = at_e ? len : e + sh;
            if (b2 > len) b2 = len;
            if (e2 > len) e2 = len;
            for (int j = b2; j < e2; j++) d[j * step] = on;
        }
    }
}

/* ---------------------------------------------------------------- 3 x 3 dilation of a 0 / non-zero picture */
API void dilate3(const uint8_t *src, int H, int W, uint8_t on, uint8_t *dst)
{
    uint8_t *tmp = (uint8_t *)malloc((size_t)H * W);
    if (!tmp) return;
    for (int y = 0; y < H; y++) {
        const uint8_t *s = src + (int64_t)y * W;
        uint8_t *t = tmp + (int64_t)y * W;
        for (int x = 0; x < W; x++)
            t[x] = (s[x] || (x > 0 && s[x - 1]) || (x + 1 < W && s[x + 1])) ? 1 : 0;
    }
    for (int y = 0; y < H; y++) {
        const uint8_t *u = tmp + (int64_t)(y > 0 ? y - 1 : y) * W, *m = tmp + (int64_t)y * W,
                      *b = tmp + (int64_t)(y + 1 < H ? y + 1 : y) * W;
        uint8_t *d = dst + (int64_t)y * W;
        for (int x = 0; x < W; x++) d[x] = (u[x] || m[x] || b[x]) ? on : 0;
    }
    free(tmp);
}

/* ---------------------------------------------------------------- 3 x 3 erosion (outside counts as on) */
API void erode3(const uint8_t *src, int H, int W, uint8_t on, uint8_t *dst)
{
    uint8_t *tmp = (uint8_t *)malloc((size_t)H * W);
    if (!tmp) return;
    for (int y = 0; y < H; y++) {
        const uint8_t *s = src + (int64_t)y * W;
        uint8_t *t = tmp + (int64_t)y * W;
        for (int x = 0; x < W; x++)
            t[x] = (s[x] && (x == 0 || s[x - 1]) && (x + 1 == W || s[x + 1])) ? 1 : 0;
    }
    for (int y = 0; y < H; y++) {
        const uint8_t *u = tmp + (int64_t)(y > 0 ? y - 1 : y) * W, *m = tmp + (int64_t)y * W,
                      *b = tmp + (int64_t)(y + 1 < H ? y + 1 : y) * W;
        uint8_t *d = dst + (int64_t)y * W;
        for (int x = 0; x < W; x++) d[x] = (u[x] && m[x] && b[x]) ? on : 0;
    }
    free(tmp);
}

/* ---------------------------------------------------------------- outer shapes and their boxes
 * 8-connected shapes of a 0 / non-zero picture, leaving out shapes inside another shape's hole (what OpenCV's
 * findContours with RETR_EXTERNAL returns). Works on runs, row by row: shapes are runs joined with the row above
 * (touching corners count); the background is runs joined straight up and down; background touching the edge is
 * outside, and a shape is outer when it touches the edge or a run of outside background beside, above or below.
 * Writes up to max_boxes boxes as x, y, w, h; returns how many, -2 when max_boxes is too small, or -1. */
static int32_t uf_find(int32_t *p, int32_t i) { while (p[i] != i) { p[i] = p[p[i]]; i = p[i]; } return i; }
static void uf_join(int32_t *p, int32_t a, int32_t b)
{
    a = uf_find(p, a); b = uf_find(p, b);
    if (a != b) { if (a < b) p[b] = a; else p[a] = b; }
}

typedef struct { int32_t *row0, *s, *e, *par; int64_t n, cap; } Runs;

static int runs_of(const uint8_t *src, int H, int W, int fg, int eight, Runs *R)
{
    R->cap = 1024; R->n = 0;
    R->s = (int32_t *)malloc(sizeof(int32_t) * R->cap);
    R->e = (int32_t *)malloc(sizeof(int32_t) * R->cap);
    R->row0 = (int32_t *)malloc(sizeof(int32_t) * (H + 1));
    if (!R->s || !R->e || !R->row0) return -1;
    for (int y = 0; y < H; y++) {
        const uint8_t *r = src + (int64_t)y * W;
        R->row0[y] = (int32_t)R->n;
        int x = 0;
        while (x < W) {
            if ((r[x] != 0) != fg) { x++; continue; }
            int b = x;
            while (x < W && (r[x] != 0) == fg) x++;
            if (R->n == R->cap) {
                R->cap *= 2;
                int32_t *ns = (int32_t *)realloc(R->s, sizeof(int32_t) * R->cap);
                if (!ns) return -1;
                R->s = ns;
                int32_t *ne = (int32_t *)realloc(R->e, sizeof(int32_t) * R->cap);
                if (!ne) return -1;
                R->e = ne;
            }
            R->s[R->n] = b; R->e[R->n] = x; R->n++;
        }
    }
    R->row0[H] = (int32_t)R->n;
    R->par = (int32_t *)malloc(sizeof(int32_t) * (R->n + 1));
    if (!R->par) return -1;
    for (int64_t i = 0; i < R->n; i++) R->par[i] = (int32_t)i;
    int g = eight ? 1 : 0;
    for (int y = 1; y < H; y++) {                         /* join runs touching the row above */
        int32_t a = R->row0[y - 1], ae = R->row0[y], b = R->row0[y], be = R->row0[y + 1];
        while (a < ae && b < be) {
            if (R->e[a] + g <= R->s[b]) { a++; continue; }
            if (R->e[b] + g <= R->s[a]) { b++; continue; }
            uf_join(R->par, a, b);
            if (R->e[a] < R->e[b]) a++; else b++;
        }
    }
    return 0;
}

static void runs_free(Runs *R) { free(R->s); free(R->e); free(R->row0); free(R->par); }

/* the background run holding column x of row y (it must be background there) */
static int32_t bg_at(const Runs *B, int y, int x)
{
    int32_t lo = B->row0[y], hi = B->row0[y + 1] - 1;
    while (lo < hi) { int32_t m = (lo + hi + 1) / 2; if (B->s[m] <= x) lo = m; else hi = m - 1; }
    return lo;
}

API int outer_boxes(const uint8_t *src, int H, int W, int32_t *boxes, int max_boxes)
{
    Runs F = {0}, B = {0};
    int count = 0;
    uint8_t *out_b = NULL, *outer = NULL;
    int32_t *bx = NULL;
    if (runs_of(src, H, W, 1, 1, &F) || runs_of(src, H, W, 0, 0, &B)) { count = -1; goto done; }
    out_b = (uint8_t *)calloc((size_t)B.n + 1, 1);     /* per background root: reaches the edge */
    outer = (uint8_t *)calloc((size_t)F.n + 1, 1);     /* per shape root: outer */
    bx = (int32_t *)malloc(sizeof(int32_t) * 4 * (F.n + 1));
    if (!out_b || !outer || !bx) { count = -1; goto done; }
    for (int y = 0; y < H; y++)
        for (int32_t i = B.row0[y]; i < B.row0[y + 1]; i++)
            if (y == 0 || y == H - 1 || B.s[i] == 0 || B.e[i] == W) out_b[uf_find(B.par, i)] = 1;
    for (int64_t i = 0; i < F.n; i++) { bx[4*i] = W; bx[4*i+1] = H; bx[4*i+2] = -1; bx[4*i+3] = -1; }
    for (int y = 0; y < H; y++) {
        for (int32_t i = F.row0[y]; i < F.row0[y + 1]; i++) {
            int32_t r = uf_find(F.par, i), s0 = F.s[i], e0 = F.e[i];
            int32_t *b = bx + 4 * r;
            if (s0 < b[0]) b[0] = s0;
            if (y < b[1]) b[1] = y;
            if (e0 - 1 > b[2]) b[2] = e0 - 1;
            if (y > b[3]) b[3] = y;
            if (outer[r]) continue;
            if (y == 0 || y == H - 1 || s0 == 0 || e0 == W) { outer[r] = 1; continue; }
            if (out_b[uf_find(B.par, bg_at(&B, y, s0 - 1))] || out_b[uf_find(B.par, bg_at(&B, y, e0))]) { outer[r] = 1; continue; }
            for (int dy = -1; dy <= 1 && !outer[r]; dy += 2) {   /* background runs straight above or below */
                int yy = y + dy;
                int32_t j = B.row0[yy], je = B.row0[yy + 1];
                while (j < je && B.e[j] <= s0) j++;
                for (; j < je && B.s[j] < e0; j++)
                    if (out_b[uf_find(B.par, j)]) { outer[r] = 1; break; }
            }
        }
    }
    for (int64_t i = 0; i < F.n; i++) {
        if (F.par[i] != i || !outer[i]) continue;
        if (count >= max_boxes) { count = -2; break; }
        boxes[4*count] = bx[4*i]; boxes[4*count+1] = bx[4*i+1];
        boxes[4*count+2] = bx[4*i+2] - bx[4*i] + 1; boxes[4*count+3] = bx[4*i+3] - bx[4*i+1] + 1;
        count++;
    }
done:
    free(out_b); free(outer); free(bx); runs_free(&F); runs_free(&B);
    return count;
}
