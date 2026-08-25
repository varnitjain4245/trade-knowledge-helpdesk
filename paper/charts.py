"""Analytics figures for the paper, emitted as inline SVG.

No plotting library is installed and adding one would put a rendering dependency in the
path of building a paper. SVG is written directly instead: it is vector, so it stays
crisp at any zoom and prints correctly through the same headless-Chrome step that
produces the PDF, and it costs nothing to install.

Two constraints shape every chart here.

**Colour that still works in black and white.** The palette is amber and blue, but the
series are also separated by *luminance*: "before" tints are light and "after" fills are
dark, so a monochrome printer renders them as visibly different greys rather than as two
identical mid-tones. Colour carries the distinction; it is not the only thing carrying
it.

**No axis that starts anywhere but zero.** Every rate plotted lies in [0, 1], and a
truncated axis would exaggerate the very before-and-after differences the paper argues
for. The improvements are large enough that they do not need the help.

All numbers are the measured values reported in Section V; nothing here is illustrative.
"""

from __future__ import annotations

# --- measured data -------------------------------------------------------------------

# Per-language acceptance, before and after the two repairs (Section V.D).
LANGUAGES = ["Hindi", "Bengali", "Tamil", "Telugu", "Marathi"]
BEFORE = {                      # answer rate, citation integrity, script fidelity
    "Hindi":   (0.60, 1.00, 0.20),
    "Bengali": (0.20, 1.00, 0.00),
    "Tamil":   (0.20, 1.00, 0.00),
    "Telugu":  (0.20, 1.00, 0.00),
    "Marathi": (0.40, 1.00, 0.00),
}
AFTER = {
    "Hindi":   (1.00, 1.00, 1.00),
    "Bengali": (1.00, 1.00, 0.80),
    "Tamil":   (1.00, 1.00, 1.00),
    "Telugu":  (0.80, 1.00, 1.00),
    "Marathi": (0.80, 1.00, 0.75),
}
SCRIPT_FLOOR = 0.80

# Outcome distribution by question class (Section V.B).
OUTCOMES = [
    # class, n, answered-with-citation, contradiction surfaced, refused
    ("In-domain\npractitioner", 30, 30, 0, 0),
    ("Deliberate\ncontradiction", 1, 0, 1, 0),
    ("Out-of-domain\ncontrol", 6, 0, 0, 6),
]

# Confidence-source ablation (Section V.B).
ABLATION = [
    # source, in-domain answered rate, out-of-domain wrongly answered rate
    ("Lexical\n(BM25 + coverage)", 27 / 30, 3 / 6),
    ("Relevance\njudging", 30 / 30, 0 / 6),
]

# Reference-free evaluation (Section V.E).
SCORES = [
    ("Faithfulness", 1.00, True),
    ("Citation integrity", 1.00, True),
    ("Refusal accuracy", 1.00, True),
    ("Answer rate", 1.00, True),
    ("Answer relevancy", 0.83, False),
    ("Context precision", 0.83, False),
]

# Per-stage latency budget in milliseconds (Section V.G).
STAGES = [
    ("Language detection", 30),
    ("Query embedding", 120),
    ("Retrieval", 250),
    ("Relevance judging", 400),
    ("Contradiction detection", 50),
    ("Generation, first token", 700),
    ("Generation, complete", 2500),
    ("Grounding verification", 150),
    ("Persistence and audit", 100),
]
BUDGET_TARGET = 5000

#: Per-stage *timeouts* are ceilings on one stage, and are a different quantity from the
#: budgets above. They sum to more than twice the whole-request deadline, which is
#: precisely why a whole-request deadline had to exist: a chain of slow-but-not-timing-out
#: stages would breach the target with nothing to stop it.
TIMEOUTS_TOTAL = 200 + 500 + 1000 + 1200 + 200 + 2000 + 4000 + 500 + 1000

_FONT = "'Times New Roman', Times, serif"

#: Amber and blue, each with a light tint for "before" and a saturated fill for "after",
#: so the pairs differ in luminance as well as hue.
AMBER_LIGHT, AMBER, AMBER_DEEP = "#FBD9A0", "#EFA22E", "#C97C10"
BLUE_LIGHT, BLUE = "#BFE3F5", "#2E7EBB"
GREEN, RED = "#4C9F70", "#C4553B"
AXIS = "#555"


def _open(w: float, h: float) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
            f'width="{w}" height="{h}" font-family="{_FONT}">')


def _legend(items, x: float, y: float, step: float = 56, width: float = 233) -> list:
    """Swatch-and-label legend, wrapping when it reaches the chart edge."""
    out, lx, ly = [], x, y
    for label, fill in items:
        out.append(f'<rect x="{lx:.1f}" y="{ly-3.4:.1f}" width="5" height="4.4" '
                   f'fill="{fill}" stroke="{AXIS}" stroke-width="0.35"/>')
        out.append(f'<text x="{lx+6.5:.1f}" y="{ly:.1f}" font-size="4.9">{label}</text>')
        lx += step
        if lx > width - step * 0.6:
            lx, ly = x, ly + 6.6
    return out


def _y_axis(out: list, left: float, top: float, pw: float, ph: float,
            fmt: str = "{:.2f}", steps: int = 4, vmax: float = 1.0) -> None:
    for k in range(steps + 1):
        v = vmax * k / steps
        y = top + ph - (v / vmax) * ph
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}" '
                   f'stroke="#ddd" stroke-width="0.4"/>')
        out.append(f'<text x="{left-3}" y="{y+2:.1f}" font-size="5.2" '
                   f'text-anchor="end">{fmt.format(v)}</text>')


# --- charts ---------------------------------------------------------------------------

def outcomes() -> str:
    """Correct outcomes by question class — every bar reaches its class size."""
    W, H = 233, 124
    left, top, pw, ph = 22, 12, 200, 64
    slot = pw / len(OUTCOMES)

    out = [_open(W, H)]
    vmax = 30
    for k in range(4):
        v = vmax * k / 3
        y = top + ph - (v / vmax) * ph
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}" '
                   f'stroke="#ddd" stroke-width="0.4"/>')
        out.append(f'<text x="{left-3}" y="{y+2:.1f}" font-size="5.2" '
                   f'text-anchor="end">{v:.0f}</text>')

    for i, (label, n, answered, conflict, refused) in enumerate(OUTCOMES):
        x = left + i * slot + slot * 0.28
        bw = slot * 0.44
        stack = [(answered, AMBER, "answered with citation"),
                 (conflict, BLUE, "contradiction surfaced"),
                 (refused, GREEN, "refused")]
        y = top + ph
        for v, fill, _ in stack:
            if not v:
                continue
            bh = v / vmax * ph
            y -= bh
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                       f'height="{bh:.1f}" fill="{fill}" stroke="{AXIS}" '
                       f'stroke-width="0.4"/>')
            out.append(f'<text x="{x+bw/2:.1f}" y="{y+bh/2+2:.1f}" font-size="5.4" '
                       f'text-anchor="middle" fill="#1a1a1a">{v}</text>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{top+ph+16.5:.1f}" font-size="4.6" '
                   f'text-anchor="middle" fill="{AXIS}">n = {n}</text>')
        for li, line in enumerate(label.split("\n")):
            out.append(f'<text x="{x+bw/2:.1f}" y="{top+ph+6+li*4.8:.1f}" '
                       f'font-size="5" text-anchor="middle">{line}</text>')

    out.append(f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" '
               f'stroke="{AXIS}" stroke-width="0.7"/>')
    out.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" '
               f'stroke="{AXIS}" stroke-width="0.7"/>')
    out += _legend([("answered with citation", AMBER),
                    ("contradiction surfaced", BLUE),
                    ("refused", GREEN)], left, H - 8, 76)
    out.append("</svg>")
    return "".join(out)


def ablation() -> str:
    """What changes when confidence comes from judging rather than lexical overlap."""
    W, H = 233, 118
    left, top, pw, ph = 26, 14, 196, 64
    slot = pw / len(ABLATION)

    out = [_open(W, H)]
    _y_axis(out, left, top, pw, ph)

    for i, (label, good, bad) in enumerate(ABLATION):
        x0 = left + i * slot + slot * 0.2
        bw = slot * 0.26
        for j, (v, fill) in enumerate(((good, AMBER), (bad, RED))):
            bh = v * ph
            x = x0 + j * (bw + 3)
            y = top + ph - bh
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw:.1f}" '
                       f'height="{bh:.1f}" fill="{fill}" stroke="{AXIS}" '
                       f'stroke-width="0.4"/>')
            out.append(f'<text x="{x+bw/2:.1f}" y="{(y-1.6) if v > 0.06 else (top+ph-1.6):.1f}" '
                       f'font-size="5" text-anchor="middle">{v:.2f}</text>')
        for li, line in enumerate(label.split("\n")):
            out.append(f'<text x="{left + i*slot + slot/2:.1f}" '
                       f'y="{top+ph+7+li*4.8:.1f}" font-size="5" '
                       f'text-anchor="middle">{line}</text>')

    out.append(f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" '
               f'stroke="{AXIS}" stroke-width="0.7"/>')
    out.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" '
               f'stroke="{AXIS}" stroke-width="0.7"/>')
    out += _legend([("in-domain answered", AMBER),
                    ("out-of-domain wrongly answered", RED)], left, H - 8, 80)
    out.append("</svg>")
    return "".join(out)


def grouped_bars() -> str:
    """Per-language answer rate and script fidelity, before against after."""
    W, H = 233, 132
    left, top, pw, ph = 26, 18, 201, 64
    slot = pw / len(LANGUAGES)
    bw = slot / 5.0

    out = [_open(W, H)]
    _y_axis(out, left, top, pw, ph)
    yf = top + ph - SCRIPT_FLOOR * ph

    for i, lang in enumerate(LANGUAGES):
        x0 = left + i * slot + slot * 0.1
        series = [(BEFORE[lang][0], AMBER_LIGHT), (AFTER[lang][0], AMBER),
                  (BEFORE[lang][2], BLUE_LIGHT), (AFTER[lang][2], BLUE)]
        for j, (v, fill) in enumerate(series):
            bh = v * ph
            x = x0 + j * bw
            y = top + ph - bh
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.88:.1f}" '
                       f'height="{bh:.1f}" fill="{fill}" stroke="{AXIS}" '
                       f'stroke-width="0.35"/>')
            if v == 0:      # a zero bar is invisible; say so rather than show nothing
                out.append(f'<text x="{x+bw*0.44:.1f}" y="{top+ph-1.4:.1f}" '
                           f'font-size="4.4" text-anchor="middle" fill="{AXIS}">0</text>')
        out.append(f'<text x="{left + i*slot + slot/2:.1f}" y="{top+ph+7:.1f}" '
                   f'font-size="5.4" text-anchor="middle">{lang}</text>')

    # Drawn after the bars: drawn before, the tall bars painted over the start of the
    # label and it read as "ript-fidelity floor".
    out.append(f'<line x1="{left}" y1="{yf:.1f}" x2="{left+pw}" y2="{yf:.1f}" '
               f'stroke="{RED}" stroke-width="0.9" stroke-dasharray="3,2"/>')
    out.append(f'<rect x="{left+pw-53:.1f}" y="{yf-6.6:.1f}" width="53" height="5.8" '
               f'fill="#fff" opacity="0.88"/>')
    out.append(f'<text x="{left+pw}" y="{yf-2:.1f}" font-size="4.9" text-anchor="end" '
               f'fill="{RED}">script-fidelity floor 0.80</text>')

    out.append(f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" '
               f'stroke="{AXIS}" stroke-width="0.7"/>')
    out.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" '
               f'stroke="{AXIS}" stroke-width="0.7"/>')
    out += _legend([("answer rate, before", AMBER_LIGHT),
                    ("answer rate, after", AMBER),
                    ("script fidelity, before", BLUE_LIGHT),
                    ("script fidelity, after", BLUE)], left - 20, H - 13, 58)
    out.append("</svg>")
    return "".join(out)


def heatmap() -> str:
    """Languages against the three gate measures, before and after.

    A heat map is the right form because the interesting structure is *which column* is
    saturated: citation integrity is uniformly 1.00 in both panels, which is the paper's
    point that the structural guarantee held while the tuned behaviour was wrong.
    """
    metrics = ["Answer\nrate", "Citation\nintegrity", "Script\nfidelity"]
    W, H = 233, 118
    cell, left, top, gap = 15.5, 42, 26, 20
    panel_w = len(metrics) * cell

    def shade(v: float) -> str:
        """White through amber to deep amber. Warm ramp, monotone in luminance."""
        stops = [(0.0, (255, 255, 255)), (0.5, (251, 217, 160)), (1.0, (201, 124, 16))]
        for (a, ca), (b, cb) in zip(stops, stops[1:]):
            if a <= v <= b:
                t = 0 if b == a else (v - a) / (b - a)
                r, g, bl = (round(ca[k] + (cb[k] - ca[k]) * t) for k in range(3))
                return f"rgb({r},{g},{bl})"
        return "rgb(255,255,255)"

    out = [_open(W, H)]
    for p, (title, data) in enumerate((("Before", BEFORE), ("After", AFTER))):
        px = left + p * (panel_w + gap)
        out.append(f'<text x="{px + panel_w/2:.1f}" y="{top-13:.1f}" font-size="6" '
                   f'text-anchor="middle" font-style="italic">{title}</text>')
        for c, m in enumerate(metrics):
            for li, line in enumerate(m.split("\n")):
                out.append(f'<text x="{px + c*cell + cell/2:.1f}" '
                           f'y="{top - 6 + li*4.6:.1f}" font-size="4.6" '
                           f'text-anchor="middle">{line}</text>')
        for r, lang in enumerate(LANGUAGES):
            if p == 0:
                out.append(f'<text x="{left-3}" y="{top + r*cell + cell/2 + 2:.1f}" '
                           f'font-size="5.4" text-anchor="end">{lang}</text>')
            for c in range(len(metrics)):
                v = data[lang][c]
                x, y = px + c * cell, top + r * cell
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{cell}" '
                           f'height="{cell}" fill="{shade(v)}" stroke="#fff" '
                           f'stroke-width="0.8"/>')
                # Always dark: measured against this amber ramp, white text reaches
                # only 1.8:1 contrast even on the deepest cell, while black reaches
                # 11.4:1 on that cell and 19.9:1 on the lightest.
                out.append(f'<text x="{x+cell/2:.1f}" y="{y+cell/2+2:.1f}" '
                           f'font-size="5" text-anchor="middle" '
                           f'fill="#1a1a1a">{v:.2f}</text>')

    sx, sy = left, top + len(LANGUAGES) * cell + 10
    for k in range(6):
        out.append(f'<rect x="{sx + k*9:.1f}" y="{sy}" width="9" height="5" '
                   f'fill="{shade(k/5)}" stroke="#bbb" stroke-width="0.3"/>')
    out.append(f'<text x="{sx-3}" y="{sy+4.2}" font-size="4.8" text-anchor="end">0.00</text>')
    out.append(f'<text x="{sx+57}" y="{sy+4.2}" font-size="4.8">1.00</text>')
    out.append("</svg>")
    return "".join(out)


def score_bars() -> str:
    """Reference-free scores as a horizontal bar chart."""
    W = 233
    row, top, left = 11.5, 8, 62
    H = top + len(SCORES) * row + 16
    pw = W - left - 16

    out = [_open(W, H)]
    for k in range(6):
        v = k / 5
        x = left + v * pw
        out.append(f'<line x1="{x:.1f}" y1="{top-2}" x2="{x:.1f}" '
                   f'y2="{top + len(SCORES)*row - 2:.1f}" stroke="#ddd" '
                   f'stroke-width="0.4"/>')
        out.append(f'<text x="{x:.1f}" y="{top + len(SCORES)*row + 5:.1f}" '
                   f'font-size="4.8" text-anchor="middle">{v:.1f}</text>')

    for i, (label, v, guaranteed) in enumerate(SCORES):
        y = top + i * row
        out.append(f'<text x="{left-4}" y="{y+6:.1f}" font-size="5.4" '
                   f'text-anchor="end">{label}</text>')
        out.append(f'<rect x="{left}" y="{y+1.5:.1f}" width="{v*pw:.1f}" height="7" '
                   f'fill="{AMBER if guaranteed else BLUE_LIGHT}" stroke="{AXIS}" '
                   f'stroke-width="0.4"/>')
        out.append(f'<text x="{left + v*pw + 3:.1f}" y="{y+6.6:.1f}" '
                   f'font-size="5">{v:.2f}</text>')

    out.append(f'<line x1="{left}" y1="{top-2}" x2="{left}" '
               f'y2="{top + len(SCORES)*row - 2:.1f}" stroke="{AXIS}" '
               f'stroke-width="0.7"/>')
    out += _legend([("structurally guaranteed", AMBER),
                    ("measured, not guaranteed", BLUE_LIGHT)], left - 40, H - 3, 88)
    out.append("</svg>")
    return "".join(out)


def latency() -> str:
    """Where the request budget goes, and how much of the target it leaves."""
    W = 233
    row, top, left = 9.6, 10, 74
    H = top + len(STAGES) * row + 18
    pw = W - left - 20
    vmax = 2500

    out = [_open(W, H)]
    for k in range(6):
        v = vmax * k / 5
        x = left + (v / vmax) * pw
        out.append(f'<line x1="{x:.1f}" y1="{top-2}" x2="{x:.1f}" '
                   f'y2="{top + len(STAGES)*row - 2:.1f}" stroke="#ddd" '
                   f'stroke-width="0.4"/>')
        out.append(f'<text x="{x:.1f}" y="{top + len(STAGES)*row + 5:.1f}" '
                   f'font-size="4.6" text-anchor="middle">{v:.0f}</text>')

    for i, (label, ms) in enumerate(STAGES):
        y = top + i * row
        # The two model-bound stages dominate the budget and are coloured to say so.
        model_bound = "Generation" in label or "judging" in label
        out.append(f'<text x="{left-4}" y="{y+5.4:.1f}" font-size="5" '
                   f'text-anchor="end">{label}</text>')
        out.append(f'<rect x="{left}" y="{y+1:.1f}" width="{ms/vmax*pw:.1f}" '
                   f'height="6" fill="{AMBER if model_bound else BLUE_LIGHT}" '
                   f'stroke="{AXIS}" stroke-width="0.35"/>')
        out.append(f'<text x="{left + ms/vmax*pw + 2.5:.1f}" y="{y+5.8:.1f}" '
                   f'font-size="4.7">{ms}</text>')

    out.append(f'<line x1="{left}" y1="{top-2}" x2="{left}" '
               f'y2="{top + len(STAGES)*row - 2:.1f}" stroke="{AXIS}" '
               f'stroke-width="0.7"/>')
    total = sum(ms for _, ms in STAGES)
    out.append(f'<text x="{left-58:.1f}" y="{H-9:.1f}" font-size="4.8" fill="{AXIS}">'
               f'budgets sum to {total} ms; the whole-request deadline is '
               f'{BUDGET_TARGET} ms</text>')
    out.append(f'<text x="{left-58:.1f}" y="{H-3:.1f}" font-size="4.8" fill="{RED}">'
               f'per-stage timeouts sum to {TIMEOUTS_TOTAL} ms &#8212; '
               f'{TIMEOUTS_TOTAL/BUDGET_TARGET:.1f}&#215; the deadline</text>')
    out.append("</svg>")
    return "".join(out)


CHARTS = {
    "outcomes": outcomes,
    "ablation": ablation,
    "languages": grouped_bars,
    "heatmap": heatmap,
    "scores": score_bars,
    "latency": latency,
}


def demo() -> None:
    """Self-check: well-formed SVG, measured numbers, column width, honest axes."""
    import xml.etree.ElementTree as ET

    for name, fn in CHARTS.items():
        svg = fn()
        ET.fromstring(svg)                      # raises if malformed
        assert svg.startswith("<svg"), name
        assert 'width="233"' in svg, f"{name} must fit a single column"

    bars = grouped_bars()
    assert ">0.00<" in bars and ">1.00<" in bars, "y axis must run 0 to 1"
    assert "0.80" in bars, "the floor Marathi fails must be visible"

    hm = heatmap()
    for lang in LANGUAGES:
        assert lang in hm, lang
    assert hm.count(">1.00<") >= 10, "citation integrity is 1.00 in both panels"

    oc = outcomes()
    assert ">30<" in oc and ">6<" in oc

    ab = ablation()
    assert ">0.90<" in ab and ">0.50<" in ab and ">0.00<" in ab

    lat = latency()
    assert "4300 ms" in lat and "5000 ms" in lat
    assert "10600 ms" in lat, "the timeout total is the point of the chart"

    sc = score_bars()
    assert sc.count(">1.00<") == 4 and sc.count(">0.83<") == 2

    print(f"charts: {len(CHARTS)} figures, well-formed, column-width, "
          f"colour with luminance contrast")


if __name__ == "__main__":
    demo()
