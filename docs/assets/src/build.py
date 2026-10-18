#!/usr/bin/env python3
"""Build the README art in docs/assets/: self-contained SVGs, each in a -dark and a -light variant.

    python docs/assets/src/build.py --fonts <dir> [--out docs/assets]

<dir> holds Geist-Medium.ttf, Geist-Regular.ttf, Geist-SemiBold.ttf, GeistMono-Regular.ttf and
GeistMono-Medium.ttf (SIL OFL), searched recursively, e.g. from `npm pack geist@1.7.0` unpacked.
Text is shaped with HarfBuzz (kerning on) and written as outlined glyphs, defined once per file and
reused, so the SVGs need no fonts and render the same everywhere. Needs uharfbuzz and fonttools.
Randomness is seeded, so a rebuild reproduces the files byte for byte.

Colour carries meaning in every asset: accent (orange) only for the human's gates and decisions,
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


def col(i):
    """Left edge of grid column i (0-based); col(12) is the right margin plus a gutter."""
    return M + i * (COL + GUT)


def span(i, n):
    """Width of n columns starting anywhere."""
    return n * COL + (n - 1) * GUT


def f(x):
    """A number for SVG: at most one decimal, no trailing zeros."""
    s = f"{x:.1f}".rstrip("0").rstrip(".")
    return "0" if s == "-0" else s


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

    def width(self, text, size, track=0.0):
        adv = sum(a for _, a, _, _ in self.shape(text))
        n = len(text)
        return (adv + track * self.upm * max(n - 1, 0)) * size / self.upm


class Svg:
    def __init__(self, faces, theme, w, h, title, desc):
        self.faces, self.theme, self.w, self.h = faces, theme, w, h
        self.title, self.desc = title, desc
        self.body, self.defs, self.glyphs, self.css = [], [], {}, []

    def add(self, s):
        self.body.append(s)

    def text(self, s, x, y, size, face="sans", cls="text", track=0.0, anchor="start", upper=False, extra=""):
        """Set s with its baseline at y; returns the advance width. track is in em."""
        fc = self.faces[face]
        if upper:
            s = s.upper()
        width = fc.width(s, size, track)
        x0 = x - width if anchor == "end" else x - width / 2 if anchor == "middle" else x
        k = size / fc.upm
        uses, pen = [], 0.0
        for gid, adv, dx, dy in fc.shape(s):
            gk = f"{fc.key}{gid}"
            if gk not in self.glyphs:
                self.glyphs[gk] = fc.outline(gid)
            if self.glyphs[gk]:
                ys = f' y="{-dy}"' if dy else ""
                uses.append(f'<use xlink:href="#{gk}" x="{round(pen + dx)}"{ys}/>')
            pen += adv + track * fc.upm
        self.add(f'<g class="f-{cls}"{extra} transform="translate({f(x0)} {f(y)}) scale({k:.5g} {-k:.5g})">'
                 + "".join(uses) + "</g>")
        return width

    def mono(self, s, x, y, size=22, cls="muted", anchor="start", track=None, upper=True, face="mono", extra=""):
        """Mono caption: uppercase tracked +0.04em by default; lowercase (code) untracked."""
        track = (0.04 if upper else 0.0) if track is None else track
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


# ---------------------------------------------------------------- hero

GATES = [("01", "Publish"), ("02", "Merge"), ("03", "Budget"), ("04", "Conclude")]


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


def hero(s):
    rng = random.Random(36)
    H = s.h
    t = THEMES[s.theme]
    # Header: wordmark and status, on a hairline.
    s.text("research-harness", M, 92, 40, "semi", "text", -0.02)
    s.mono("Pre-release  ·  a template, not a service", W - M, 90, 22, "muted", anchor="end")
    s.line(M, 124, W - M, 124, "hair")
    for x in (M, W - M):
        s.reg(x, 124)
    # Headline.
    s.text("Agents do the work.", M - 4, 248, 104, "display", "muted", -0.02)
    s.text("You hold the gates.", M - 4, 360, 104, "display", "text", -0.02)
    # Caption block, right.
    cx = col(9)
    s.mono("01 — The harness", cx, 178, 22, "faint")
    for i, ln in enumerate(["Wide, fast agent work", "passes four human gates", "and leaves as one table,",
                            "checked against the spec."]):
        s.text(ln, cx, 228 + i * 36, 26, "sans", "muted")

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
    hero_i = N // R * 2 + 9            # the highlighted trajectory lands in row 3
    for i, pts in enumerate(lines):
        if i != hero_i:
            s.add(f'<path d="{smooth(pts)}" fill="none" stroke="url(#fade)" stroke-width="1"/>')

    # Gates: a wall hairline with an aperture held open by two orange anchor points.
    for k, g in enumerate(gx):
        a, b = c - half[k], c + half[k]
        s.line(g, top - 36, g, a, "hair2", 1)
        s.line(g, b, g, bot + 36, "hair2", 1)
        s.add(f'<path class="k-accent" stroke-width="2" d="M{f(g)} {f(a - 40)}V{f(a)}M{f(g)} {f(b + 40)}V{f(b)}"/>')
        s.rect(g - 5, a - 5, 10, 10, fill="accent")
        s.rect(g - 5, b - 5, 10, 10, fill="accent")
        num, name = GATES[k]
        w = s.mono(num, g - 8, bot + 68, 22, "accent", anchor="end", face="monom")
        s.mono(name, g + 8, bot + 68, 22, "text")
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
    s.css.append(f".pulse{{stroke-dasharray:{dash} 2000;stroke-dashoffset:{f(-(start - dash / 2))};opacity:0;animation:pulse {period}s linear infinite}}")
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
    for x, label, anchor, cls in ((cols_x[0], "Arm", "start", "muted"), (cols_x[1], "n", "start", "muted"),
                                  (cols_x[2], "Top-1", "start", "muted"), (cols_x[3], "Spec", "end", "verify")):
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
    s.mono("Study table · 12 runs", tx, rows[-1] + P / 2 + 36, 22, "faint")

    # Footer: legend.
    fy = H - 52
    s.line(M, fy - 44, W - M, fy - 44, "hair")
    for x in (M, W - M):
        s.reg(x, fy - 44)
    legend(s, M, fy, [("gate", "Human gate"), ("agent", "Agent work"), ("verify", "Checked against the spec")])
    s.mono("doem97/research-harness", W - M, fy, 22, "faint", anchor="end", upper=False)


# ---------------------------------------------------------------- the loop

def arrow(s, x1, y1, x2, y2, cls="text", w=1.5, head=8):
    """A straight arrow from (x1, y1) to (x2, y2) with an open head."""
    a = math.atan2(y2 - y1, x2 - x1)
    h1 = (x2 - head * math.cos(a - .45), y2 - head * math.sin(a - .45))
    h2 = (x2 - head * math.cos(a + .45), y2 - head * math.sin(a + .45))
    s.add(f'<path class="k-{cls}" stroke-width="{f(w)}" stroke-linecap="round" stroke-linejoin="round" '
          f'd="M{f(x1)} {f(y1)}L{f(x2)} {f(y2)}M{f(h1[0])} {f(h1[1])}L{f(x2)} {f(y2)}L{f(h2[0])} {f(h2[1])}"/>')


def lane_label(s, y, name, note):
    """A lane's name and note on a knockout, so connectors pass behind it."""
    width = s.faces["monom"].width(name.upper(), 22, .04) + 16 + s.faces["mono"].width(note.upper(), 22, .04)
    s.rect(M - 8, y - 26, width + 16, 36, fill="bg")
    w = s.mono(name, M, y, 22, "text", face="monom")
    s.mono(note, M + w + 16, y, 22, "faint")


def loop(s):
    H = s.h
    frame(s, 96, H - 112, "03 — State", "One loop · four gates · every step on GitHub")
    phases = ["Plan", "Implement", "Review", "Merge", "Run", "Analyze"]
    x0 = [col(2 * k) for k in range(6)]
    cw = span(0, 2)
    for k, name in enumerate(phases):
        w = s.mono(f"0{k + 1}", x0[k], 152, 22, "faint")
        s.mono(name, x0[k] + w + 14, 152, 22, "text")
    s.line(M, 180, W - M, 180, "hair2")
    for k in range(1, 6):
        s.line(x0[k] - GUT / 2, 196, x0[k] - GUT / 2, H - 150, "hair", 1, ' stroke-dasharray="2 6"')

    # HUMAN: four gates and a blocker, nothing else.
    lane_label(s, 232, "Human", "in a session; never clicks on GitHub")
    gy = 284
    gates = {0: ("01", "Publish", "“publish”"), 3: ("02", "Merge", "“merge”"),
             4: ("03", "Budget", "“continue”"), 5: ("04", "Conclude", "“conclude #10”")}
    for k, (num, name, say) in gates.items():
        s.rect(x0[k], gy - 7, 14, 14, fill="accent")
        w = s.mono(num, x0[k] + 26, gy + 8, 22, "accent", face="monom")
        s.mono(name, x0[k] + 26 + w + 10, gy + 8, 22, "accent")
        s.text(say, x0[k], gy + 52, 26, "sans", "text")
        s.line(x0[k] + 7, gy + 70, x0[k] + 7, 448, "accent", 1.5)
    k = 1
    s.add(f'<circle class="k-accent" fill="none" stroke-width="2" cx="{f(x0[k] + 7)}" cy="{gy}" r="7"/>')
    s.mono("Blocker", x0[k] + 26, gy + 8, 22, "accent")
    s.text("“option 2”", x0[k], gy + 52, 26, "sans", "text")
    s.line(x0[k] + 7, gy + 70, x0[k] + 7, 448, "accent", 1.5, ' stroke-dasharray="4 5"')
    s.line(M, 384, W - M, 384, "hair")

    # AGENTS: the skills, in fresh sessions where it matters.
    lane_label(s, 428, "Agents", "four skills; Claude Code or Codex")
    cy, ch = 448, 120
    cards = [("plan", "discuss, draft"), ("implement", "code to a PR"), ("review", "fresh session"),
             ("merge.py", "the only merge"), ("run", "launch, check"), ("report", "three lines")]
    for k, (title, sub) in enumerate(cards):
        dash = ' stroke-dasharray="6 5"' if title == "review" else ""
        s.rect(x0[k], cy, cw, ch, fill="surface", stroke="text" if title == "review" else "hair2",
               sw=1, extra=dash + (' stroke-opacity=".55"' if dash else ""))
        face = "mono" if title.endswith(".py") else "display"
        if face == "mono":
            s.text(title, x0[k] + 20, cy + 50, 28, "monom", "text")
        else:
            s.text(title, x0[k] + 20, cy + 50, 30, "display", "text", -0.01)
        s.text(sub, x0[k] + 20, cy + 90, 26, "sans", "muted")
        if k < 5:
            arrow(s, x0[k] + cw + 3, cy + ch / 2, x0[k + 1] - 3, cy + ch / 2, "text", 1.5, 7)
    # The review loop: changes go back to implement, a pass goes on.
    ly = cy + ch + 34
    xa, xb = x0[2] + cw / 2, x0[1] + cw / 2
    s.add(f'<path class="k-text" stroke-width="1.5" d="M{f(xa)} {f(cy + ch)}V{f(ly - 12)}Q{f(xa)} {f(ly)} {f(xa - 12)} {f(ly)}'
          f'H{f(xb + 12)}Q{f(xb)} {f(ly)} {f(xb)} {f(ly - 12)}V{f(cy + ch + 4)}"/>')
    arrow(s, xb, cy + ch + 14, xb, cy + ch + 3, "text", 1.5, 7)
    s.add(f'<rect class="f-bg" x="{f((xa + xb) / 2 - 64)}" y="{f(ly - 14)}" width="128" height="28"/>')
    s.mono("changes", (xa + xb) / 2, ly + 8, 22, "muted", anchor="middle")
    s.line(M, 664, W - M, 664, "hair")

    # RECORD: what each step leaves behind.
    lane_label(s, 708, "Record", "GitHub and MLflow, written as it happens")
    ry = 756
    rec = [("Issues", ["study #10", "code #11", "run #12"]),
           ("Pull request", ["Closes #11", "guard · test"]),
           ("Review", ["Verdict: pass", "@ 3f9c2a1"]),
           ("main", ["squash merge", "of that head"]),
           ("MLflow runs", ["rh.*  cfg.*", "artifacts"]),
           ("Results", ["per-issue table", "spec check", "study table"])]
    for k, (head, lines) in enumerate(rec):
        s.rect(x0[k], ry - 17, 10, 10, stroke="text", sw=1.5)
        s.mono(head, x0[k] + 22, ry - 6, 22, "muted")
        for i, ln in enumerate(lines):
            cls = "verify" if ln in ("spec check", "study table") else "text"
            s.mono(ln, x0[k], ry + 40 + i * 36, 22, cls, upper=False)
        if k == 5:
            s.check(x0[k] + s.faces["mono"].width("spec check", 22) + 12, ry + 76 - 2, 16)
            s.check(x0[k] + s.faces["mono"].width("study table", 22) + 12, ry + 112 - 2, 16)
        if k in gates:
            s.mono("Decision:", x0[k], ry + 40 + 3 * 36, 22, "accent", upper=False)
    # Footer.
    legend(s, M, H - 64, [("gate", "Human gate · decision"), ("agent", "Agent work"), ("verify", "Checked against the spec")])


# ---------------------------------------------------------------- the spec is the contract

SPEC = [("h", "### Arms"),
        ("kv", "full: model.adapter=none", ""),
        ("kv", "lora: model.adapter=lora model.lora.rank=8", ""),
        ("h", "### Controlled"),
        ("kv", "optim.lr=3e-4", "# paper X, table 2"),
        ("kv", "train.effective_batch=256", "# paper X, table 2"),
        ("kv", "seed in 1,2,3", "# three seeds"),
        ("h", "### Adaptable"),
        ("kv", "train.per_device_batch", "# fit GPU memory")]


def contract(s):
    H = s.h
    rng = random.Random(7)
    frame(s, 96, H - 112, "04 — Contract", "The spec is the last layer you can read")
    L, Rr = M, col(7) - GUT                 # left block: columns 1-7
    px = col(8)                              # right panel: columns 9-12
    # The spec card.
    top, lh = 144, 40
    bottom = top + 88 + len(SPEC) * lh + 16
    s.rect(L, top, Rr - L, bottom - top, fill="surface", stroke="hair2")
    s.rect(L, top, 6, bottom - top, fill="accent")
    s.mono("Study #10 · spec", L + 40, top + 50, 22, "text", face="monom")
    s.mono("Layer 0", Rr - 32, top + 50, 22, "faint", anchor="end")
    s.line(L + 40, top + 72, Rr - 32, top + 72, "hair")
    y = top + 72 + lh + 4
    for kind, *t in SPEC:
        if kind == "h":
            s.mono(t[0], L + 40, y, 24, "muted", upper=False)
        else:
            s.mono(t[0], L + 40, y, 24, "text", upper=False)
            if t[1]:
                s.mono(t[1], L + 40 + 27 * 14.4, y, 24, "faint", upper=False)
        y += lh
    # Its annotation, each note on the baseline of the section it explains.
    s.rect(px, top + 34, 14, 14, fill="accent")
    w = s.mono("Readable by you", px + 26, top + 50, 22, "accent")
    s.mono("· gate 01", px + 26 + w + 12, top + 50, 22, "faint")
    heads = [i for i, (kind, *_) in enumerate(SPEC) if kind == "h"]
    notes = [("Arms", "the only differences"), ("Controlled", "held fixed, each with a reason"),
             ("Adaptable", "may differ, within its rule")]
    for i, (name, note) in zip(heads, notes):
        yb = top + 72 + lh + 4 + i * lh
        s.mono(name, px, yb, 22, "muted")
        s.text(note, px, yb + 36, 26, "sans", "text")

    # The layers below it: denser, fainter, too deep to read.
    layers = [("Layer 1 · code", 112, 6, (40, 260), .34), ("Layer 2 · config", 112, 9, (14, 70), .26),
              ("Layer 3 · launches and runs", 148, 13, (3, 6), .22)]
    y = bottom + 96
    s.mono("Below it: agent work, too deep to read", L, y - 40, 22, "muted")
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
    lw = s.faces["mono"].width("6 run records", 22)
    s.rect(rx[0] - 36 - lw, ry - 22, lw + 24, 34, fill="bg")
    s.rect(rx[0] - 18, ry - 18, rx[-1] - rx[0] + 36, 36, fill="bg")
    for x in rx:
        s.rect(x - 9, ry - 9, 18, 18, fill="surface", stroke="verify", sw=2)
    s.mono("6 run records", rx[0] - 24, ry + 8, 22, "verify", anchor="end", upper=False)
    # The blue arrow: from the records, back up to the spec.
    ax = (Rr + px) / 2
    ay = top + 144
    s.add(f'<path class="k-verify" stroke-width="2" d="M{f(rx[-1] + 9)} {f(ry)}H{f(ax - 16)}Q{f(ax)} {f(ry)} {f(ax)} {f(ry - 16)}'
          f'V{f(ay + 16)}Q{f(ax)} {f(ay)} {f(ax - 16)} {f(ay)}H{f(Rr + 10)}"/>')
    arrow(s, Rr + 26, ay, Rr + 3, ay, "verify", 2, 10)
    # The check result, as results.py reports it (its text follows the project's language).
    l1 = bottom + 96
    cy, chh = l1, 336
    cw = W - M - px
    s.line(ax, cy + 46, px, cy + 46, "verify", 2)
    s.add(f'<circle class="f-verify" cx="{f(ax)}" cy="{f(cy + 46)}" r="4"/>')
    s.rect(px, cy, cw, chh, fill="surface", stroke="verify", sw=1.5)
    s.check(px + 24, cy + 56, 18)
    s.mono("Spec check · 6 runs", px + 56, cy + 56, 22, "verify", face="monom")
    s.line(px + 24, cy + 78, W - M - 24, cy + 78, "hair")
    out = [("text", "≠ train.effective_batch=256"), ("muted", "  1 run took 128"),
           ("text", "≠ undeclared: train.precision"), ("muted", "  bf16 × 5, fp16 × 1"),
           ("text", "· adaptable per_device_batch"), ("muted", "  full 64; lora 64, 32")]
    for i, (cls, ln) in enumerate(out):
        s.mono(ln, px + 24, cy + 122 + (i // 2) * 78 + (i % 2) * 32, 22, cls, upper=False)
    for i, (ln, cls) in enumerate([("Checked right after launch", "verify"), ("and in every results comment,", "verify"),
                                   ("from the record, not from", "muted"), ("an agent's account.", "muted")]):
        s.mono(ln, px, cy + chh + 44 + i * 32, 22, cls, upper=False)
    legend(s, M, H - 64, [("gate", "Approved by you"), ("agent", "Agent work"), ("verify", "Checked against the spec")])


# ---------------------------------------------------------------- stats

STATS = [("0", "text", ["Services", "to install"]),
         ("80", "text", ["Lines of", "rules, capped", "by a test"]),
         ("4", "text", ["Skills of", "≤ 120 lines", "each"]),
         ("4", "accent", ["Human gates,", "the only", "planned stops"]),
         ("1", "text", ["Merge path", "for agents:", "merge.py"]),
         ("2", "text", ["Agent CLIs,", "one set of", "skills"])]


def stats(s):
    H = s.h
    frame(s, 96, H - 56, "02 — Facts", "The template in six numbers")
    for k, (num, cls, cap) in enumerate(STATS):
        x = col(2 * k)
        if k:
            s.line(x - GUT / 2, 120, x - GUT / 2, H - 80, "hair")
        s.text(num, x - 4, 232, 104, "display", cls, -0.03)
        for i, ln in enumerate(cap):
            s.mono(ln, x, 288 + i * 32, 22, "muted")


# ---------------------------------------------------------------- talk, don't click

SESSION = [("you", "let’s plan this study: does LoRA match full fine-tuning?", None),
           ("agent", ["Discusses the spec with you, then drafts study #10 with code #11 and run #12."], None),
           ("you", "publish", "01"),
           ("agent", ["Done: published #10 with #11 and #12", "Decision: recorded on #10"], None),
           ("you", "do #11", None),
           ("agent", ["Done: PR #13 is merge-ready, Verdict: pass @ 3f9c2a1",
                      "Waiting for you: merge PR #13", "Next: run #12"], None),
           ("you", "merge", "02"),
           ("agent", ["Done: merged PR #13 with merge.py --human; #11 closed", "Decision: recorded on #11"], None),
           ("you", "take #10 to analysis", None),
           ("agent", ["Done: #12 closed with its results and spec check; study table on #10",
                      "Waiting for you: conclude #10", "Next: nothing"], None),
           ("you", "what’s waiting for me?", None),
           ("agent", ["Study #10 awaits your conclusion (gate 04). No blockers, no PRs waiting."], None)]


def session(s):
    H = s.h
    frame(s, 96, H - 112, "05 — Session", "Talk, don’t click")
    x_who, x_say = M, col(2)
    y = 168
    for who, say, gate in SESSION:
        if who == "you":
            s.mono("You", x_who, y, 22, "accent", face="monom")
            s.text(say, x_say, y + 2, 32, "display", "text", -0.01)
            if gate:
                w = s.mono(f"Gate {gate}", W - M, y, 22, "accent", anchor="end")
                s.rect(W - M - w - 26, y - 14, 14, 14, fill="accent")
            y += 64
        else:
            s.mono("Agent", x_who, y, 22, "muted")
            for i, ln in enumerate(say):
                key, sep, rest = ln.partition(": ")
                if sep and key in ("Done", "Waiting for you", "Next", "Decision"):
                    w = s.mono(key + ":", x_say, y, 24, "accent" if key == "Decision" else "text", upper=False)
                    s.text(rest, x_say + w + 14, y, 26, "sans", "muted")
                else:
                    s.text(ln, x_say, y, 26, "sans", "muted")
                y += 40
            y += 24
            if y < s.h - 200:
                s.line(x_say, y - 32, W - M, y - 32, "hair")
    legend(s, M, H - 64, [("gate", "Your words at a gate"), ("agent", "Agent work and reports")])


# ---------------------------------------------------------------- main

ASSETS = {
    "hero": (hero, 980, "research-harness: agents do the work, you hold the gates",
             "Many fine agent trajectories enter from the left, pass through four orange human gates "
             "(publish, merge, budget, conclude), grow more ordered at each, and resolve into a results "
             "table whose rows are checked against the study spec."),
    "loop": (loop, 1080, "The rh loop: plan, implement, review, merge, run, analyze",
             "Three swimlanes. Human: four orange gates (publish, merge, budget, conclude) and blocker answers. "
             "Agents: the plan, implement, review (fresh session) and run skills, merge.py, and the three-line "
             "report. Record: issues, the pull request, the Verdict comment, the squash merge, MLflow runs, and "
             "the results comment with its spec check and the study table."),
    "contract": (contract, 1340, "The spec is the contract",
                 "A study spec card (arms, controlled settings with reasons, adaptable settings), readable by you and "
                 "approved at gate 01. Below it, denser layers of agent work: code, config, launches and runs. A blue "
                 "arrow runs from six run records back up to the spec, with the spec check those records produced."),
    "stats": (stats, 456, "research-harness in numbers",
              "0 services to install; 80 lines of rules, capped by a test; 4 skills of at most 120 lines each; "
              "4 human gates (publish, merge, budget, conclude); 1 merge path for agents, merge.py; 2 agent CLIs "
              "(Claude Code and Codex) sharing one set of skills."),
    "session": (session, 1300, "Talk, don't click: a session with rh",
                "A session transcript: you plan a study, say publish (gate 01), do #11, merge (gate 02), take the "
                "study to analysis and ask what is waiting; the agent answers each stop with Done, Waiting for "
                "you and Next."),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fonts", required=True, help="directory holding the Geist TTFs (searched recursively)")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--only", nargs="*")
    a = ap.parse_args()
    root = Path(a.fonts)

    def find(name):
        hits = sorted(root.rglob(name))
        if not hits:
            raise SystemExit(f"font {name} not found under {root}")
        return hits[0]

    faces = {"sans": Face(find("Geist-Regular.ttf"), "s"), "display": Face(find("Geist-Medium.ttf"), "d"),
             "semi": Face(find("Geist-SemiBold.ttf"), "b"),
             "mono": Face(find("GeistMono-Regular.ttf"), "m", mono=True),
             "monom": Face(find("GeistMono-Medium.ttf"), "n", mono=True)}
    for name, (fn, h, title, desc) in ASSETS.items():
        if a.only and name not in a.only:
            continue
        for theme in THEMES:
            s = Svg(faces, theme, W, h, title, desc)
            fn(s)
            out = Path(a.out) / f"{name}-{theme}.svg"
            out.write_text(s.render())
            print(f"{out}  {out.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
