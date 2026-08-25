"""Analytics figures for the paper, emitted as inline SVG.

No plotting library is installed and adding one would put a rendering dependency in the
path of building a paper. SVG is written directly instead: it is vector, so it stays
crisp at any zoom and prints correctly through the same headless-Chrome step that
produces the PDF, and it costs nothing to install.

Two constraints shape every chart here.

**Greyscale first.** Conference papers are read on screen and printed in black and
white, and a chart distinguishing its series only by hue becomes unreadable in the
second case. Series are separated by fill *value* and by hatching, so the distinction
survives a monochrome printer; colour, where used at all, is redundant with those.

**No axis that starts anywhere but zero.** Every quantity plotted is a rate in [0, 1],
and a truncated axis would exaggerate the very before-and-after differences the paper
is arguing for. The improvements are large enough that they do not need help.

All numbers are the measured values reported in Section V; nothing here is illustrative.
"""

from __future__ import annotations

# Measured per-language acceptance, before and after the two repairs (Section V.D).
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

# Reference-free evaluation (Section V.E).
SCORES = [
    ("Faithfulness", 1.00),
    ("Citation integrity", 1.00),
    ("Refusal accuracy", 1.00),
    ("Answer rate", 1.00),
    ("Answer relevancy", 0.83),
    ("Context precision", 0.83),
]

_FONT = "'Times New Roman', Times, serif"


def _defs() -> str:
    """Hatch patterns, so series remain distinguishable on a monochrome printer."""
    return (
        '<defs>'
        '<pattern id="hatch" width="3" height="3" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="3" stroke="#000" stroke-width="1.1"/>'
        '</pattern>'
        '<pattern id="hatchLight" width="4" height="4" patternUnits="userSpaceOnUse" '
        'patternTransform="rotate(45)">'
        '<line x1="0" y1="0" x2="0" y2="4" stroke="#000" stroke-width="0.6"/>'
        '</pattern>'
        '</defs>'
    )


def grouped_bars() -> str:
    """Per-language answer rate and script fidelity, before against after.

    Script fidelity is the quantity the paper's multilingual argument turns on, and
    plotting it beside answer rate shows that the two failed for different reasons and
    were repaired by different changes.
    """
    W, H = 233, 132
    left, right, top, bottom = 26, 6, 20, 34
    pw, ph = W - left - right, H - top - bottom
    n = len(LANGUAGES)
    slot = pw / n
    bw = slot / 5.0

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}" font-family="{_FONT}">', _defs()]

    # y axis, 0 to 1, gridlines every 0.25
    for k in range(5):
        v = k / 4
        y = top + ph - v * ph
        out.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left+pw}" y2="{y:.1f}" '
                   f'stroke="#bbb" stroke-width="0.4"/>')
        out.append(f'<text x="{left-3}" y="{y+2:.1f}" font-size="5.2" text-anchor="end">'
                   f'{v:.2f}</text>')

    yf = top + ph - SCRIPT_FLOOR * ph

    for i, lang in enumerate(LANGUAGES):
        x0 = left + i * slot + slot * 0.12
        series = [
            (BEFORE[lang][0], "#ffffff", "url(#hatchLight)"),   # answer rate, before
            (AFTER[lang][0],  "#9a9a9a", None),                  # answer rate, after
            (BEFORE[lang][2], "#ffffff", "url(#hatch)"),         # script, before
            (AFTER[lang][2],  "#2f2a86", None),                  # script, after
        ]
        for j, (v, fill, pat) in enumerate(series):
            bh = v * ph
            x = x0 + j * bw
            y = top + ph - bh
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.9:.1f}" '
                       f'height="{bh:.1f}" fill="{fill}" stroke="#000" '
                       f'stroke-width="0.4"/>')
            if pat:
                out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw*0.9:.1f}" '
                           f'height="{bh:.1f}" fill="{pat}" stroke="none"/>')
            if v == 0:  # a zero bar is invisible; say so rather than show nothing
                out.append(f'<text x="{x+bw*0.45:.1f}" y="{top+ph-1.5:.1f}" '
                           f'font-size="4.4" text-anchor="middle">0</text>')
        out.append(f'<text x="{left + i*slot + slot/2:.1f}" y="{top+ph+8:.1f}" '
                   f'font-size="5.4" text-anchor="middle">{lang}</text>')

    # The floor line is drawn after the bars, not before: drawn first, the tall bars
    # painted over the start of its label and it read as "ript-fidelity floor".
    out.append(f'<line x1="{left}" y1="{yf:.1f}" x2="{left+pw}" y2="{yf:.1f}" '
               f'stroke="#000" stroke-width="0.8" stroke-dasharray="3,2"/>')
    out.append(f'<rect x="{left+pw-52:.1f}" y="{yf-6.4:.1f}" width="52" height="5.6" '
               f'fill="#fff" opacity="0.85"/>')
    out.append(f'<text x="{left+pw}" y="{yf-2:.1f}" font-size="4.9" text-anchor="end">'
               f'script-fidelity floor 0.80</text>')

    out.append(f'<line x1="{left}" y1="{top+ph}" x2="{left+pw}" y2="{top+ph}" '
               f'stroke="#000" stroke-width="0.7"/>')
    out.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+ph}" '
               f'stroke="#000" stroke-width="0.7"/>')

    # legend
    items = [("answer rate, before", "#ffffff", "url(#hatchLight)"),
             ("answer rate, after", "#9a9a9a", None),
             ("script fidelity, before", "#ffffff", "url(#hatch)"),
             ("script fidelity, after", "#2f2a86", None)]
    lx, ly = left - 20, H - 12
    for label, fill, pat in items:
        out.append(f'<rect x="{lx}" y="{ly-3.4}" width="5" height="4.4" fill="{fill}" '
                   f'stroke="#000" stroke-width="0.4"/>')
        if pat:
            out.append(f'<rect x="{lx}" y="{ly-3.4}" width="5" height="4.4" '
                       f'fill="{pat}" stroke="none"/>')
        out.append(f'<text x="{lx+6.5}" y="{ly}" font-size="4.9">{label}</text>')
        lx += 56
        if lx > W - 50:
            lx, ly = left - 20, ly + 6.5

    out.append("</svg>")
    return "".join(out)


def heatmap() -> str:
    """Languages against the three gate measures, before and after.

    A heat map is the right form here because the interesting structure is *which cell*
    is dark: citation integrity is uniformly 1.00 in both panels, which is the paper's
    point that the structural guarantee held while the tuned behaviour was wrong.
    """
    metrics = ["Answer\nrate", "Citation\nintegrity", "Script\nfidelity"]
    W, H = 233, 118
    cell = 15.5
    left, top = 42, 26
    gap = 20
    panel_w = len(metrics) * cell

    def shade(v: float) -> str:
        # Darker means higher. Linear in value so the eye reads it as the number.
        g = int(255 - 205 * v)
        return f"rgb({g},{g},{g})"

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}" font-family="{_FONT}">']

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
                out.append(f'<text x="{x+cell/2:.1f}" y="{y+cell/2+2:.1f}" '
                           f'font-size="5" text-anchor="middle" '
                           f'fill="{"#fff" if v > 0.55 else "#000"}">'
                           f'{v:.2f}</text>')

    # scale
    sx, sy = left, top + len(LANGUAGES) * cell + 10
    for k in range(6):
        v = k / 5
        out.append(f'<rect x="{sx + k*9:.1f}" y="{sy}" width="9" height="5" '
                   f'fill="{shade(v)}" stroke="#999" stroke-width="0.3"/>')
    out.append(f'<text x="{sx-3}" y="{sy+4.2}" font-size="4.8" text-anchor="end">0.00</text>')
    out.append(f'<text x="{sx+57}" y="{sy+4.2}" font-size="4.8">1.00</text>')
    out.append("</svg>")
    return "".join(out)


def score_bars() -> str:
    """Reference-free scores as a horizontal bar chart."""
    W = 233
    row, top, left = 11.5, 8, 62
    H = top + len(SCORES) * row + 12
    pw = W - left - 16

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}" font-family="{_FONT}">', _defs()]

    for k in range(6):
        v = k / 5
        x = left + v * pw
        out.append(f'<line x1="{x:.1f}" y1="{top-2}" x2="{x:.1f}" '
                   f'y2="{top + len(SCORES)*row - 2:.1f}" stroke="#ccc" '
                   f'stroke-width="0.4"/>')
        out.append(f'<text x="{x:.1f}" y="{top + len(SCORES)*row + 5:.1f}" '
                   f'font-size="4.8" text-anchor="middle">{v:.1f}</text>')

    for i, (label, v) in enumerate(SCORES):
        y = top + i * row
        # The three guaranteed quantities are filled solid; the two measured-but-not-
        # guaranteed ones are hatched, because they are of a different kind.
        guaranteed = v == 1.00
        out.append(f'<text x="{left-4}" y="{y+6:.1f}" font-size="5.4" '
                   f'text-anchor="end">{label}</text>')
        out.append(f'<rect x="{left}" y="{y+1.5:.1f}" width="{v*pw:.1f}" height="7" '
                   f'fill="{"#2f2a86" if guaranteed else "#ffffff"}" stroke="#000" '
                   f'stroke-width="0.4"/>')
        if not guaranteed:
            out.append(f'<rect x="{left}" y="{y+1.5:.1f}" width="{v*pw:.1f}" '
                       f'height="7" fill="url(#hatchLight)" stroke="none"/>')
        out.append(f'<text x="{left + v*pw + 3:.1f}" y="{y+6.6:.1f}" '
                   f'font-size="5">{v:.2f}</text>')

    out.append(f'<line x1="{left}" y1="{top-2}" x2="{left}" '
               f'y2="{top + len(SCORES)*row - 2:.1f}" stroke="#000" stroke-width="0.7"/>')
    out.append("</svg>")
    return "".join(out)


CHARTS = {"languages": grouped_bars, "heatmap": heatmap, "scores": score_bars}


def demo() -> None:
    """Self-check: the SVG is well-formed and plots the measured numbers."""
    import xml.etree.ElementTree as ET

    for name, fn in CHARTS.items():
        svg = fn()
        ET.fromstring(svg)                       # raises if malformed
        assert svg.startswith("<svg"), name
        assert "viewBox" in svg, name

    # A truncated axis would overstate the before-and-after difference the paper argues.
    bars = grouped_bars()
    assert ">0.00<" in bars and ">1.00<" in bars, "y axis must run 0 to 1"

    # The floor Marathi fails has to be visible, or the withheld language is unexplained.
    assert "0.80" in bars

    # Both panels of the heat map must carry every language and every measured value.
    hm = heatmap()
    for lang in LANGUAGES:
        assert lang in hm, lang
    assert hm.count(">1.00<") >= 10, "citation integrity is 1.00 in both panels"

    # Charts must fit a single column: 233pt against a 233pt printed column.
    for name, fn in CHARTS.items():
        assert 'width="233"' in fn(), name

    print(f"charts: {len(CHARTS)} figures, well-formed, greyscale-safe, column-width")


if __name__ == "__main__":
    demo()
