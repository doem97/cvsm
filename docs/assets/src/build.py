#!/usr/bin/env python3
"""Build the README figures in docs/assets/: self-contained SVGs in English and Chinese, dark and light.

    python docs/assets/src/build.py --fonts <dir> [<dir> ...] [--out docs/assets] [--only hero ...]

Writes <name>-{dark,light}.svg (English, README.md) and <name>-zh-{dark,light}.svg (Chinese,
docs/README.zh-CN.md) for each figure: hero and contract.

Fonts, all SIL Open Font License 1.1, searched recursively under the --fonts dirs; none is committed:
- Geist and Geist Mono 1.7.0, from `npm pack geist@1.7.0` (package/dist/fonts): Geist-Regular.ttf,
  Geist-Medium.ttf, Geist-SemiBold.ttf, GeistMono-Regular.ttf, GeistMono-Medium.ttf.
- Noto Sans SC 2.004, from github.com/notofonts/noto-cjk at tag Sans2.004,
  Sans/SubsetOTF/SC/NotoSansSC-Regular.otf and NotoSansSC-Medium.otf.

Text is shaped with HarfBuzz (kerning on) and written as outlined glyphs, defined once per file and
reused, so the SVGs need no fonts and render the same everywhere. In Chinese figures each CJK run is
set in Noto Sans SC and everything else (Latin, digits, code) in Geist; a space between CJK and Latin
becomes a fixed quarter-em gap, and CJK is never tracked tighter than zero. Needs uharfbuzz and
fonttools. Randomness is seeded, so a rebuild reproduces the files byte for byte.

Colour carries meaning in every figure: accent (orange) only for the human's gates and decisions,
ink for agent work, verify (blue) only for records checked against the spec.
"""
import argparse
import math
import random
from pathlib import Path

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont

THEMES = {
    "dark": dict(bg="#0B0C0F", surface="#121419", hair="rgba(255,255,255,.10)", hair2="rgba(255,255,255,.18)",
                 text="#F2F2F0", muted="#9BA0A8", faint="#5C616B", accent="#FF5A1F", verify="#6EA8FF"),
    "light": dict(bg="#F7F6F2", surface="#FFFFFF", hair="rgba(10,12,15,.10)", hair2="rgba(10,12,15,.20)",
                  text="#0B0C0F", muted="#5F646C", faint="#A3A7AE", accent="#F04A0E", verify="#2F6FE0"),
}
W, M, GUT = 1600, 96, 24
COL = (W - 2 * M - 11 * GUT) / 12
CJK_FACE = {"sans": "zh", "mono": "zh", "display": "zhm", "semi": "zhm", "monom": "zhm"}
CJK_GAP = 0.25    # em between CJK and Latin (and around · and —) where the copy has a space
CJK_SCALE = {"display": 0.88}   # CJK set smaller than Latin in display type, so ideographs match its weight


def col(i):
    """Left edge of grid column i (0-based)."""
    return M + i * (COL + GUT)


def f(x):
    """A number for SVG: at most one decimal, no trailing zeros."""
    s = f"{x:.1f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


def tight(ch):
    """Characters whose neighbouring spaces become the fixed CJK gap in Chinese figures."""
    return is_cjk(ch) or ch in "·—"


def is_cjk(ch):
    o = ord(ch)
    return (0x2E80 <= o <= 0x9FFF or 0x3000 <= o <= 0x303F or 0xFF00 <= o <= 0xFFEF
            or 0x3400 <= o <= 0x4DBF or 0xF900 <= o <= 0xFAFF)


# ---------------------------------------------------------------- type

class Face:
    def __init__(self, path, key, mono=False):
        self.tt = TTFont(path)
        self.glyphs = self.tt.getGlyphSet()
        self.upm = self.tt["head"].unitsPerEm
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(path))))
        self.key = key
        self.features = {"kern": True, "liga": not mono, "calt": not mono}

    def shape(self, text):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.hb, buf, self.features)
        return [(i.codepoint, p.x_advance, p.x_offset, p.y_offset) for i, p in zip(buf.glyph_infos, buf.glyph_positions)]

    def outline(self, gid):
        pen = SVGPathPen(self.glyphs)
        self.glyphs[self.tt.getGlyphName(gid)].draw(pen)
        return pen.getCommands()


class Svg:
    def __init__(self, faces, theme, lang, w, h, title, desc):
        self.faces, self.theme, self.lang, self.w, self.h = faces, theme, lang, w, h
        self.title, self.desc = title, desc
        self.body, self.defs, self.glyphs, self.css = [], [], {}, []

    def tr(self, en, zh):
        return zh if self.lang == "zh" else en

    def add(self, s):
        self.body.append(s)

    def runs(self, s, face):
        """Split s into [face, text] runs: CJK in Noto Sans SC (Chinese figures only), the rest in face;
        a space touching CJK, · or — becomes a ["gap", " "] run."""
        base = self.faces[face]
        cjk = self.faces[CJK_FACE[face]] if self.lang == "zh" else None
        out = []
        for i, ch in enumerate(s):
            if cjk and ch == " " and ((i and tight(s[i - 1])) or (i + 1 < len(s) and tight(s[i + 1]))):
                kind = "gap"
            else:
                kind = cjk if cjk and is_cjk(ch) else base
            if out and out[-1][0] is kind and kind != "gap":
                out[-1][1] += ch
            else:
                out.append([kind, ch])
        return out

    def layout(self, s, face, track):
        """Glyphs as (glyph key, face, gid, x, dy, scale) in font units, and the advance width in font units."""
        upm = self.faces[face].upm
        placed, pen, last = [], 0.0, 0.0
        for kind, text in self.runs(s, face):
            if kind == "gap":
                pen += CJK_GAP * upm
                last = 0.0
                continue
            assert kind.upm == upm
            zh = kind.key.startswith("z")
            tk = max(track, 0.0) if zh else track
            sc = CJK_SCALE.get(face, 1.0) if zh else 1.0
            for gid, adv, dx, dy in kind.shape(text):
                placed.append((f"{kind.key}{gid}", kind, gid, pen + dx * sc, dy * sc, sc))
                pen += adv * sc + tk * upm
                last = tk * upm
        return placed, pen - last

    def width(self, s, size, face="mono", track=0.0, upper=False):
        return self.layout(s.upper() if upper else s, face, track)[1] * size / self.faces[face].upm

    def text(self, s, x, y, size, face="sans", cls="text", track=0.0, anchor="start", upper=False, extra=""):
        """Set s with its baseline at y; returns the advance width. track is in em."""
        if upper:
            s = s.upper()
        placed, adv = self.layout(s, face, track)
        k = size / self.faces[face].upm
        width = adv * k
        x0 = x - width if anchor == "end" else x - width / 2 if anchor == "middle" else x
        uses = []
        for gk, fc, gid, gx, dy, sc in placed:
            if gk not in self.glyphs:
                self.glyphs[gk] = fc.outline(gid)
            if self.glyphs[gk] and sc != 1.0:
                uses.append(f'<use xlink:href="#{gk}" transform="translate({round(gx)} {-round(dy)}) scale({sc:g})"/>')
            elif self.glyphs[gk]:
                ys = f' y="{-dy}"' if dy else ""
                uses.append(f'<use xlink:href="#{gk}" x="{round(gx)}"{ys}/>')
        self.add(f'<g class="f-{cls}"{extra} transform="translate({f(x0)} {f(y)}) scale({k:.5g} {-k:.5g})">'
                 + "".join(uses) + "</g>")
        return width

    def mono(self, s, x, y, size=22, cls="muted", anchor="start", track=None, upper=None, face="mono", extra=""):
        """Mono caption. English: uppercase, tracked +0.04em; code (upper=False) untracked.
        Chinese: no case change, tracked +0.02em."""
        if upper is None:
            upper = self.lang == "en"
        if track is None:
            track = 0.0 if upper is False and self.lang == "en" else 0.04 if upper else 0.02
        if self.lang == "zh" and upper is False and track == 0.02 and not any(is_cjk(c) for c in s):
            track = 0.0     # pure code stays untracked
        return self.text(s, x, y, size, face, cls, track, anchor, upper, extra)

    def line(self, x1, y1, x2, y2, cls="hair", w=1, extra=""):
        self.add(f'<path class="k-{cls}" stroke-width="{f(w)}" d="M{f(x1)} {f(y1)}L{f(x2)} {f(y2)}"{extra}/>')

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=1, rx=0, extra=""):
        a = f' class="{"f-" + fill if fill else ""} {"k-" + stroke if stroke else ""}"'
        r = f' rx="{f(rx)}"' if rx else ""
        nf = "" if fill else ' fill="none"'
        sws = f' stroke-width="{f(sw)}"' if stroke else ""
        self.add(f'<rect x="{f(x)}" y="{f(y)}" width="{f(w)}" height="{f(h)}"{r}{a}{nf}{sws}{extra}/>')

    def check(self, x, y, s=14, cls="verify", w=2.5):
        """A check mark whose box is s wide, bottom-left near (x, y)."""
        self.add(f'<path class="k-{cls}" fill="none" stroke-width="{f(w)}" stroke-linecap="round" '
                 f'stroke-linejoin="round" d="M{f(x)} {f(y - s * .45)}L{f(x + s * .36)} {f(y - s * .08)}'
                 f'L{f(x + s)} {f(y - s * .9)}"/>')

    def reg(self, x, y, n=10):
        """A registration mark: a small cross at (x, y)."""
        self.add(f'<path class="k-muted" stroke-width="1" d="M{f(x - n)} {f(y)}H{f(x + n)}M{f(x)} {f(y - n)}V{f(y + n)}"/>')

    def render(self):
        t = THEMES[self.theme]
        css = [f".f-{k}{{fill:{v}}}.k-{k}{{stroke:{v}}}" for k, v in t.items()]
        css.append("path[class^='k-'],path[class*=' k-']{fill:none}")
        defs = "".join(f'<path id="{k}" d="{d}"/>' for k, d in self.glyphs.items() if d) + "".join(self.defs)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                f'viewBox="0 0 {self.w} {self.h}" width="{self.w}" height="{self.h}" role="img" '
                f'aria-labelledby="t d"><title id="t">{self.title}</title><desc id="d">{self.desc}</desc>'
                f'<style>{"".join(css)}{"".join(self.css)}</style><defs>{defs}</defs>'
                f'<rect width="{self.w}" height="{self.h}" class="f-bg"/>' + "".join(self.body) + "</svg>\n")


# ---------------------------------------------------------------- geometry

def smooth(pts):
    """Catmull-Rom through pts as one cubic Bezier path."""
    d = [f"M{f(pts[0][0])} {f(pts[0][1])}"]
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d.append(f"C{f(c1[0])} {f(c1[1])} {f(c2[0])} {f(c2[1])} {f(p2[0])} {f(p2[1])}")
    return "".join(d)


def bezier_points(pts, n=40):
    """Sample the Catmull-Rom curve smooth() draws, for arc-length lookups."""
    out = []
    for i in range(len(pts) - 1):
        p0, p1, p2 = pts[max(i - 1, 0)], pts[i], pts[i + 1]
        p3 = pts[min(i + 2, len(pts) - 1)]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        for j in range(n + (i == len(pts) - 2)):
            t = j / n
            u = 1 - t
            out.append(tuple(u ** 3 * a + 3 * u * u * t * b + 3 * u * t * t * c + t ** 3 * e
                             for a, b, c, e in zip(p1, c1, c2, p2)))
    return out


def arc_fraction(samples, x):
    """Fraction of the curve's length at which it first reaches abscissa x."""
    acc, at = [0.0], None
    for a, b in zip(samples, samples[1:]):
        acc.append(acc[-1] + math.dist(a, b))
    for i, p in enumerate(samples):
        if at is None and p[0] >= x:
            at = acc[i]
    return at / acc[-1]


def keyframes(name, stops):
    """CSS keyframes from [(percent, declarations)]."""
    return f"@keyframes {name}{{" + "".join(f"{p:.2f}%{{{d}}}" for p, d in stops) + "}"


REDUCED = "@media (prefers-reduced-motion:reduce){.anim{animation:none!important;opacity:0!important}}"


def arrow(s, x1, y1, x2, y2, cls="text", w=1.5, head=8):
    """A straight arrow from (x1, y1) to (x2, y2) with an open head."""
    a = math.atan2(y2 - y1, x2 - x1)
    h1 = (x2 - head * math.cos(a - .45), y2 - head * math.sin(a - .45))
    h2 = (x2 - head * math.cos(a + .45), y2 - head * math.sin(a + .45))
    s.add(f'<path class="k-{cls}" stroke-width="{f(w)}" stroke-linecap="round" stroke-linejoin="round" '
          f'd="M{f(x1)} {f(y1)}L{f(x2)} {f(y2)}M{f(h1[0])} {f(h1[1])}L{f(x2)} {f(y2)}L{f(h2[0])} {f(h2[1])}"/>')


def legend(s, x, y, items):
    """A row of legend entries at baseline y: [(kind, label)], kind in gate|agent|verify."""
    for kind, label in items:
        if kind == "gate":
            s.rect(x, y - 14, 14, 14, fill="accent")
        elif kind == "agent":
            s.line(x, y - 7, x + 28, y - 7, "text", 1.5)
        else:
            s.check(x, y - 1, 16)
        x += (42 if kind == "agent" else 28) + s.mono(label, x + (42 if kind == "agent" else 28), y, 22, "muted") + 48
    return x


def frame(s, top, bottom, index, right):
    """Header and footer rules with registration marks, a section index and a right caption."""
    s.line(M, top, W - M, top, "hair")
    s.line(M, bottom, W - M, bottom, "hair")
    for x in (M, W - M):
        for y in (top, bottom):
            s.reg(x, y)
    s.mono(index, M, top - 24, 22, "muted")
    s.mono(right, W - M, top - 24, 22, "faint", anchor="end")


# ---------------------------------------------------------------- hero

def hero(s):
    rng = random.Random(36)
    H = s.h
    t = THEMES[s.theme]
    zh = s.lang == "zh"
    # Header: wordmark and status, on a hairline.
    s.text("CVSM", M, 92, 40, "semi", "text", -0.02)
    s.mono(s.tr("Pre-release  ·  a template, not a service", "预发布 · 是模板，不是服务"), W - M, 90, 22, "muted",
           anchor="end")
    s.line(M, 124, W - M, 124, "hair")
    for x in (M, W - M):
        s.reg(x, 124)
    # Headline.
    # The full name, in two lines that break at the phrase boundary. English is set smaller than the
    # old slogan so that its longer line stays left of the caption column.
    hs = 104 if zh else 88
    s.text(s.tr("Controlled-Variable", "控制变量"), M - 4, 248, hs, "display", "muted", -0.02)
    s.text(s.tr("State Machine Protocol", "状态机协议"), M - 4, 360, hs, "display", "text", -0.02)
    # Caption block, right.
    cx = col(9)
    s.mono(s.tr("01 — The protocol", "01 — 总览"), cx, 178, 22, "faint")
    cap = s.tr(["Wide, fast agent work", "passes four human gates", "and leaves as one table,", "checked against the spec."],
               ["agent 的工作又快又杂，", "穿过你守的四道关口，", "最后汇成一张表，", "每一行都按规格核对过。"])
    for i, ln in enumerate(cap):
        s.text(ln, cx, 228 + i * (40 if zh else 36), 26, "sans", "muted")

    # Illustration band.
    top, bot = 452, 788
    c = (top + bot) / 2
    g0, g3 = col(2) + COL / 2, col(7) + COL / 2
    gx = [g0 + k * (g3 - g0) / 3 for k in range(4)]
    half = [158, 124, 100, 88]         # aperture half-heights, gate 1 to 4
    order = [0.28, 0.66, 0.92, 1.0]    # how far each gate sorts the lines toward their rows
    tx, R, P = col(8), 4, 48
    rows = [c - P * (R - 1) / 2 + r * P + 20 for r in range(R)]   # row centres (below the header)
    N = 104
    s.defs.append(f'<linearGradient id="fade" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{f(gx[0])}" y2="0">'
                  f'<stop offset="0" stop-color="{t["text"]}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{t["text"]}" stop-opacity=".30"/></linearGradient>')
    s.defs.append(f'<linearGradient id="fadeh" gradientUnits="userSpaceOnUse" x1="0" y1="0" x2="{f(gx[0])}" y2="0">'
                  f'<stop offset="0" stop-color="{t["text"]}" stop-opacity="0"/>'
                  f'<stop offset="1" stop-color="{t["text"]}" stop-opacity=".95"/></linearGradient>')
    lines = []
    for i in range(N):
        r = i * R // N
        within = (i % (N // R)) / (N // R - 1) * 2 - 1
        target = rows[r]
        pts, y = [], rng.uniform(top - 8, bot + 8)
        for x in (0, gx[0] * .25, gx[0] * .5, gx[0] * .75):
            pts.append((x, y))
            y = min(max(y + rng.uniform(-80, 80), top - 8), bot + 8)
        prev = gx[0]
        for k, g in enumerate(gx):
            ordered = c + (target - c) * min(1, half[k] / 96) + within * half[k] * .22 * (1 - order[k] * .8)
            loose = c + rng.uniform(-1, 1) * half[k] * .92
            yk = order[k] * ordered + (1 - order[k]) * loose
            yk = min(max(yk, c - half[k] + 8), c + half[k] - 8)
            if k:
                mid = (prev + g) / 2
                amp = [0, 40, 20, 8][k]
                pts.append((mid, (pts[-1][1] + yk) / 2 + rng.uniform(-amp, amp)))
            pts.append((g, yk))
            prev = g
        pts.append((gx[3] + (tx - gx[3]) * .5, target + (pts[-1][1] - target) * .15))
        pts.append((tx - 20, target))
        pts.append((tx, target))
        lines.append(pts)
    hero_i = N // R * 2 + 9            # the highlighted trajectory
    for i, pts in enumerate(lines):
        if i != hero_i:
            s.add(f'<path d="{smooth(pts)}" fill="none" stroke="url(#fade)" stroke-width="1"/>')

    # Gates: a wall hairline with an aperture held open by two orange anchor points.
    names = s.tr(["Publish", "Merge", "Budget", "Conclude"], ["发布", "合并", "预算", "下结论"])
    for k, g in enumerate(gx):
        a, b = c - half[k], c + half[k]
        s.line(g, top - 36, g, a, "hair2", 1)
        s.line(g, b, g, bot + 36, "hair2", 1)
        s.add(f'<path class="k-accent" stroke-width="2" d="M{f(g)} {f(a - 40)}V{f(a)}M{f(g)} {f(b + 40)}V{f(b)}"/>')
        s.rect(g - 5, a - 5, 10, 10, fill="accent")
        s.rect(g - 5, b - 5, 10, 10, fill="accent")
        s.mono(f"0{k + 1}", g - 8, bot + 68, 22, "accent", anchor="end", face="monom")
        s.mono(names[k], g + 8, bot + 68, 22, "text")
    # The highlighted trajectory and its pulse.
    hp = lines[hero_i]
    d = smooth(hp)
    s.add(f'<path stroke="url(#fadeh)" fill="none" stroke-width="1.75" d="{d}"/>')
    samples = bezier_points(hp)
    fr = [arc_fraction(samples, g) * 1000 for g in gx]
    dash, period = 22, 11.0
    travel, hold = 6.6, 0.55
    speed = 1000 / travel
    # The pulse starts invisible where the trajectory has faded in (not at the canvas edge), fades in,
    # holds at each gate, and fades out as it runs into its table row. Hidden when not animating.
    start = arc_fraction(samples, gx[0] * .4) * 1000

    def at(p):
        return f"stroke-dashoffset:{f(-(p - dash / 2))}"

    stops, tcur, pos = [(0, at(start) + ";opacity:0")], 0.0, start
    stops.append(((tcur + 50 / speed) / period * 100, at(start + 50) + ";opacity:1"))
    for k, p in enumerate(fr):
        tcur += (p - pos) / speed
        stops.append((tcur / period * 100, at(p)))
        tcur += hold
        stops.append((tcur / period * 100, at(p) + ";opacity:1"))
        pos = p
    end = 1000 - dash / 2
    tcur += (end - pos) / speed
    stops.append((tcur / period * 100, at(end) + ";opacity:0"))
    stops.append((100, at(end) + ";opacity:0"))
    s.css.append(keyframes("pulse", stops))
    s.css.append(f".pulse{{stroke-dasharray:{dash} 2000;stroke-dashoffset:{f(-(start - dash / 2))};opacity:0;"
                 f"animation:pulse {period}s linear infinite}}")
    s.add(f'<path class="k-accent pulse anim" pathLength="1000" stroke-width="4" stroke-linecap="round" d="{d}"/>')
    # Each gate's crossing point rings while the pulse holds there.
    t0, pos = 0.0, start
    for k, g in enumerate(gx):
        t0 += (fr[k] - pos) / speed
        a, b = t0 / period * 100, (t0 + hold) / period * 100
        s.css.append(keyframes(f"ring{k}", [(0, "opacity:0"), (max(a - .3, 0), "opacity:0"), (a, "opacity:1"),
                                            (b, "opacity:1"), (b + 1.2, "opacity:0"), (100, "opacity:0")]))
        s.css.append(f".ring{k}{{opacity:0;animation:ring{k} {period}s linear infinite}}")
        y = next(p[1] for p in samples if p[0] >= g)
        s.add(f'<circle class="k-accent ring{k} anim" fill="none" stroke-width="2" cx="{f(g)}" cy="{f(y)}" r="9"/>')
        t0 += hold
        pos = fr[k]
    s.css.append(REDUCED)

    # The table the work resolves into: one row per arm, runs grouped as results.py groups them.
    hy = rows[0] - P / 2 - 44
    right = W - M
    cols_x = [tx + 24, tx + 168, tx + 216, right - 24]
    s.line(tx, hy, right, hy, "hair2")
    for x, label, anchor, cls in ((cols_x[0], "arm", "start", "muted"), (cols_x[1], "n", "start", "muted"),
                                  (cols_x[2], "top-1", "start", "muted"),
                                  (cols_x[3], s.tr("spec", "规格"), "end", "verify")):
        s.mono(label, x, hy + 30, 22, cls, anchor=anchor)
    data = [("linear", "71.4", "0.6"), ("full", "85.1", "0.4"), ("lora-8", "84.2", "0.5"), ("lora-16", "84.6", "0.3")]
    for r, (arm, v, sd) in enumerate(data):
        y = rows[r]
        s.line(tx, y - P / 2, right, y - P / 2, "hair")
        s.mono(arm, cols_x[0], y + 8, 22, "text", upper=False)
        s.mono("3", cols_x[1], y + 8, 22, "text", upper=False)
        w = s.mono(v, cols_x[2], y + 8, 22, "text", upper=False)
        s.mono("± " + sd, cols_x[2] + w + 12, y + 8, 22, "muted", upper=False)
        s.check(cols_x[3] - 18, y + 7, 18)
        s.add(f'<circle class="f-text" cx="{f(tx)}" cy="{f(y)}" r="3"/>')
    s.line(tx, rows[-1] + P / 2, right, rows[-1] + P / 2, "hair2")
    s.line(tx, hy, tx, rows[-1] + P / 2, "hair2")
    s.mono(s.tr("Study table · 12 runs", "研究总表 · 12 个 run"), tx, rows[-1] + P / 2 + 36, 22, "faint")

    # Footer: legend.
    fy = H - 52
    s.line(M, fy - 44, W - M, fy - 44, "hair")
    for x in (M, W - M):
        s.reg(x, fy - 44)
    legend(s, M, fy, [("gate", s.tr("Human gate", "人的关口")), ("agent", s.tr("Agent work", "agent 的工作")),
                      ("verify", s.tr("Checked against the spec", "已按规格核对"))])
    s.mono("doem97/cvsm", W - M, fy, 22, "faint", anchor="end", upper=False)


# ---------------------------------------------------------------- the spec is the contract

def contract(s):
    H = s.h
    rng = random.Random(7)
    zh = s.lang == "zh"
    frame(s, 96, H - 112, s.tr("02 — Contract", "02 — 合同"),
          s.tr("The spec is the last layer you can read", "规格是你能读懂的最后一层"))
    L, Rr = M, col(7) - GUT                 # left block: columns 1-7
    px = col(8)                              # right panel: columns 9-12
    spec = [("h", "### Arms"),
            ("kv", "full: model.adapter=none", ""),
            ("kv", "lora: model.adapter=lora model.lora.rank=8", ""),
            ("h", "### Controlled"),
            ("kv", "optim.lr=3e-4", s.tr("# paper X, table 2", "# 论文 X 表 2")),
            ("kv", "train.effective_batch=256", s.tr("# paper X, table 2", "# 论文 X 表 2")),
            ("kv", "seed in 1,2,3", s.tr("# three seeds", "# 三个 seed")),
            ("h", "### Adaptable"),
            ("kv", "train.per_device_batch", s.tr("# fit GPU memory", "# 按显存调整"))]
    # The spec card.
    top, lh = 144, 40
    bottom = top + 88 + len(spec) * lh + 16
    s.rect(L, top, Rr - L, bottom - top, fill="surface", stroke="hair2")
    s.rect(L, top, 6, bottom - top, fill="accent")
    s.mono(s.tr("Study #10 · spec", "研究 #10 · 规格"), L + 40, top + 50, 22, "text", face="monom")
    s.mono(s.tr("Layer 0", "第 0 层"), Rr - 32, top + 50, 22, "faint", anchor="end")
    s.line(L + 40, top + 72, Rr - 32, top + 72, "hair")
    y = top + 72 + lh + 4
    for kind, *t in spec:
        if kind == "h":
            s.mono(t[0], L + 40, y, 24, "muted", upper=False)
        else:
            s.mono(t[0], L + 40, y, 24, "text", upper=False)
            if t[1]:
                s.mono(t[1], L + 40 + 27 * 14.4, y, 24, "faint", upper=False)
        y += lh
    # Its annotation, each note on the baseline of the section it explains.
    s.rect(px, top + 34, 14, 14, fill="accent")
    w = s.mono(s.tr("Readable by you", "你能读懂"), px + 26, top + 50, 22, "accent")
    s.mono(s.tr("· gate 01", "· 关口 01"), px + 26 + w + 12, top + 50, 22, "faint")
    heads = [i for i, (kind, *_) in enumerate(spec) if kind == "h"]
    notes = [("Arms", s.tr("the only differences", "各组之间仅有的不同")),
             ("Controlled", s.tr("held fixed, each with a reason", "固定不变，各带理由")),
             ("Adaptable", s.tr("may differ, within its rule", "可以不同，但守住规则"))]
    for i, (name, note) in zip(heads, notes):
        yb = top + 72 + lh + 4 + i * lh
        s.mono(name, px, yb, 22, "muted")
        s.text(note, px, yb + 36, 26, "sans", "text")

    # The layers below it: denser, fainter, too deep to read.
    layers = [(s.tr("Layer 1 · code", "第 1 层 · 代码"), 112, 6, (40, 260), .34),
              (s.tr("Layer 2 · config", "第 2 层 · 配置"), 112, 9, (14, 70), .26),
              (s.tr("Layer 3 · launches and runs", "第 3 层 · 启动和运行"), 148, 13, (3, 6), .22)]
    y = bottom + 96
    s.mono(s.tr("Below it: agent work, too deep to read", "规格以下：agent 的工作，多到读不完"), L, y - 40, 22, "muted")
    runs_box = None
    for li, (name, h, nrows, wrange, op) in enumerate(layers):
        s.rect(L, y, Rr - L, h, stroke="hair")
        s.mono(name, L + 20, y + 32, 22, "muted")
        x_start, pitch = L + 20, (h - 52) / max(nrows - 1, 1)
        bars = []
        for r in range(nrows):
            yy = y + 48 + r * pitch
            x = x_start + (rng.choice([0, 0, 24, 48, 72]) if li == 0 else 0)
            while x < Rr - 20:
                w = rng.uniform(*wrange)
                if x + w > Rr - 20:
                    break
                bars.append(f"M{f(x)} {f(yy)}h{f(w)}")
                x += w + (rng.uniform(10, 26) if li < 2 else rng.uniform(4, 7))
                if li == 0 and rng.random() < .25:
                    break
        s.add(f'<path class="k-text" stroke-opacity="{op}" stroke-width="{3 if li < 2 else 2.5}" d="{"".join(bars)}"/>')
        if li == 2:
            runs_box = (y, h)
        y += h + 24
    # Layer 3 runs on below the frame: fade it out.
    t = THEMES[s.theme]
    ly, lhh = runs_box
    s.defs.append(f'<linearGradient id="deep" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{t["bg"]}" '
                  f'stop-opacity="0"/><stop offset="1" stop-color="{t["bg"]}" stop-opacity=".92"/></linearGradient>')
    s.add(f'<rect x="{f(L + 1)}" y="{f(ly + lhh * .45)}" width="{f(Rr - L - 2)}" height="{f(lhh * .55)}" fill="url(#deep)"/>')
    # Six run records, picked out in the densest layer, checked against the spec.
    rx = [Rr - 290 + i * 44 for i in range(6)]
    ry = ly + 78
    label = s.tr("6 run records", "6 条运行记录")
    lw = s.width(label, 22, "mono", 0.0 if not zh else 0.02)
    s.rect(rx[0] - 36 - lw, ry - 22, lw + 24, 34, fill="bg")
    s.rect(rx[0] - 18, ry - 18, rx[-1] - rx[0] + 36, 36, fill="bg")
    for x in rx:
        s.rect(x - 9, ry - 9, 18, 18, fill="surface", stroke="verify", sw=2)
    s.mono(label, rx[0] - 24, ry + 8, 22, "verify", anchor="end", upper=False)
    # The blue arrow: from the records, back up to the spec.
    ax = (Rr + px) / 2
    ay = top + 144
    s.add(f'<path class="k-verify" stroke-width="2" d="M{f(rx[-1] + 9)} {f(ry)}H{f(ax - 16)}Q{f(ax)} {f(ry)} {f(ax)} {f(ry - 16)}'
          f'V{f(ay + 16)}Q{f(ax)} {f(ay)} {f(ax - 16)} {f(ay)}H{f(Rr + 10)}"/>')
    arrow(s, Rr + 26, ay, Rr + 3, ay, "verify", 2, 10)
    # The check result, as results.py reports it.
    l1 = bottom + 96
    cy, chh = l1, 336
    cw = W - M - px
    s.line(ax, cy + 46, px, cy + 46, "verify", 2)
    s.add(f'<circle class="f-verify" cx="{f(ax)}" cy="{f(cy + 46)}" r="4"/>')
    s.rect(px, cy, cw, chh, fill="surface", stroke="verify", sw=1.5)
    s.check(px + 24, cy + 56, 18)
    s.mono(s.tr("Spec check · 6 runs", "规格核对 · 6 个 run"), px + 56, cy + 56, 22, "verify", face="monom")
    s.line(px + 24, cy + 78, W - M - 24, cy + 78, "hair")
    out = s.tr([("text", "≠ train.effective_batch=256"), ("muted", "  1 run took 128"),
                ("text", "≠ undeclared: train.precision"), ("muted", "  bf16 × 5, fp16 × 1"),
                ("text", "· adaptable per_device_batch"), ("muted", "  full 64; lora 64, 32")],
               [("text", "≠ train.effective_batch=256"), ("muted", "  1 个 run 取 128"),
                ("text", "≠ 未声明的差异 train.precision"), ("muted", "  bf16 5 个，fp16 1 个"),
                ("text", "· Adaptable per_device_batch"), ("muted", "  full 取 64；lora 取 64、32")])
    for i, (cls, ln) in enumerate(out):
        s.mono(ln, px + 24, cy + 122 + (i // 2) * 78 + (i % 2) * 32, 22, cls, upper=False)
    caption = s.tr([("Checked right after launch", "verify"), ("and in every results comment,", "verify"),
                    ("from the record, not from", "muted"), ("an agent's account.", "muted")],
                   [("启动后马上核对，", "verify"), ("每条结果评论里再核对；", "verify"),
                    ("依据是记录，", "muted"), ("不是 agent 的说法。", "muted")])
    for i, (ln, cls) in enumerate(caption):
        s.mono(ln, px, cy + chh + 44 + i * (36 if zh else 32), 22, cls, upper=False)
    legend(s, M, H - 64, [("gate", s.tr("Approved by you", "由你批准")), ("agent", s.tr("Agent work", "agent 的工作")),
                          ("verify", s.tr("Checked against the spec", "已按规格核对"))])


# ---------------------------------------------------------------- main

ASSETS = {
    "hero": (hero, 980, {
        "en": ("CVSM: Controlled-Variable State Machine Protocol",
               "Many fine agent trajectories enter from the left, pass through four orange human gates "
               "(publish, merge, budget, conclude), grow more ordered at each, and resolve into a results "
               "table whose rows are checked against the study spec."),
        "zh": ("CVSM：控制变量状态机协议",
               "许多细密的 agent 轨迹从左边进来，穿过四道橙色的人的关口（发布、合并、预算、下结论），"
               "每过一道就更有序，最后汇成一张结果表，每一行都按研究规格核对过。")}),
    "contract": (contract, 1340, {
        "en": ("Every run is checked against the study spec",
               "A study spec card (arms, controlled settings with reasons, adaptable settings), readable by you and "
               "approved at gate 01. Below it, denser layers of agent work: code, config, launches and runs. A blue "
               "arrow runs from six run records back up to the spec, with the spec check those records produced."),
        "zh": ("每个 run 都对照研究规格核对",
               "一张研究规格卡片（各组的不同、带理由的固定设置、可调整的设置），你能读懂，在关口 01 批准。"
               "下面是越来越密的 agent 工作层：代码、配置、启动和运行。一支蓝色箭头从六条运行记录指回规格，"
               "旁边是这些记录得出的规格核对。")}),
}
FONTS = {"sans": ("Geist-Regular.ttf", "s", False), "display": ("Geist-Medium.ttf", "d", False),
         "semi": ("Geist-SemiBold.ttf", "b", False), "mono": ("GeistMono-Regular.ttf", "m", True),
         "monom": ("GeistMono-Medium.ttf", "n", True), "zh": ("NotoSansSC-Regular.otf", "zr", False),
         "zhm": ("NotoSansSC-Medium.otf", "zm", False)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True, nargs="+", help="directories holding the fonts (searched recursively)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()

    def find(name):
        hits = sorted(h for d in a.fonts for h in Path(d).rglob(name))
        if not hits:
            raise SystemExit(f"font {name} not found under {' '.join(a.fonts)}")
        return hits[0]

    faces = {k: Face(find(name), key, mono) for k, (name, key, mono) in FONTS.items()}
    for name, (fn, h, text) in ASSETS.items():
        if a.only and name not in a.only:
            continue
        for lang, suffix in (("en", ""), ("zh", "-zh")):
            for theme in THEMES:
                s = Svg(faces, theme, lang, W, h, *text[lang])
                fn(s)
                out = Path(a.out) / f"{name}{suffix}-{theme}.svg"
                out.write_text(s.render())
                print(f"{out}  {out.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
