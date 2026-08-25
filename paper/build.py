"""Render the paper into IEEE conference two-column HTML, for Chrome to print.

No LaTeX toolchain is available, so the format is reproduced in CSS: A4 with IEEE
margins, two balanced columns, Times at 10pt, roman-numeral section headings in small
caps, table captions above and figure captions below.
"""

import html
import re

from charts import CHARTS
from pathlib import Path

HERE = Path(__file__).parent
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


def inline(text: str) -> str:
    """Markdown emphasis and code, escaped first so source text cannot inject markup."""
    text = html.escape(text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"(?<!\*)\*([^*]+?)\*(?!\*)", r"<em>\1</em>", text)
    text = re.sub(r"`(.+?)`", r"<code>\1</code>", text)
    text = text.replace("—", "&#8212;").replace("–", "&#8211;")
    return text


def convert(md: str) -> str:
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    section_no = 0
    table_no = 0
    in_para: list[str] = []

    def flush():
        if in_para:
            out.append(f"<p>{inline(' '.join(in_para))}</p>")
            in_para.clear()

    while i < len(lines):
        line = lines[i].rstrip()

        if not line.strip():
            flush(); i += 1; continue

        if line.startswith("# "):
            flush()
            out.append(f'<h1 class="title">{inline(line[2:])}</h1>')
            i += 1; continue

        if line.startswith("## "):
            flush()
            heading = line[3:].strip()
            if heading.upper() == "REFERENCES":
                out.append('<h2 class="sec refs-head">R<span class="sc">EFERENCES</span></h2>')
            else:
                # "I. INTRODUCTION" -> numbered small-caps heading, as IEEE sets them.
                m = re.match(r"^([IVX]+)\.\s+(.*)$", heading)
                if m:
                    section_no += 1
                    body = m.group(2)
                    out.append(
                        f'<h2 class="sec">{m.group(1)}. '
                        f'{body[0]}<span class="sc">{inline(body[1:].lower())}</span></h2>')
                else:
                    out.append(f'<h2 class="sec">{inline(heading)}</h2>')
            i += 1; continue

        if line.startswith("### "):
            flush()
            body = line[4:].strip()
            out.append(f'<h3 class="sub">{inline(body)}</h3>')
            i += 1; continue

        if line.startswith("---"):
            flush(); i += 1; continue

        # Tables: caption line immediately above, IEEE style.
        if line.startswith("|"):
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(lines[i]); i += 1
            cells = [[c.strip() for c in r.strip("|").split("|")] for r in rows]
            cells = [r for r in cells if not all(set(c) <= set("-: ") for c in r)]
            table_no += 1
            head, *body = cells
            thead = "".join(f"<th>{inline(c)}</th>" for c in head)
            tbody = "".join(
                "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body)
            out.append(
                f'<table class="ieee"><thead><tr>{thead}</tr></thead>'
                f"<tbody>{tbody}</tbody></table>")
            continue

        # Fenced block -> figure art; the "**Caption.** Fig. N." line that follows
        # becomes the caption, which IEEE sets below the figure.
        # A chart marker: <!--CHART:name--> is replaced by inline SVG from charts.py,
        # and the line that follows becomes its caption.
        if line.startswith("<!--CHART:"):
            flush()
            name = line[len("<!--CHART:"):].split("-->")[0].strip()
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            cap = ""
            if i < len(lines) and lines[i].startswith("Fig."):
                cap_lines = []
                while i < len(lines) and lines[i].strip():
                    cap_lines.append(lines[i].strip()); i += 1
                cap = inline(" ".join(cap_lines))
            out.append(f'<figure class="ieee chart">{CHARTS[name]()}'
                       f'<figcaption>{cap}</figcaption></figure>')
            continue

        if line.startswith("```"):
            flush()
            i += 1
            art = []
            while i < len(lines) and not lines[i].startswith("```"):
                art.append(lines[i]); i += 1
            i += 1
            while i < len(lines) and not lines[i].strip():
                i += 1
            cap = ""
            if i < len(lines) and lines[i].startswith("**Caption.**"):
                cap_lines = []
                while i < len(lines) and lines[i].strip():
                    cap_lines.append(lines[i].strip()); i += 1
                cap = inline(" ".join(cap_lines).replace("**Caption.** ", ""))
            out.append(
                '<figure class="ieee"><pre class="fig">'
                + html.escape("\n".join(art)).rstrip()
                + f'</pre><figcaption>{cap}</figcaption></figure>')
            continue

        if line.startswith("**Abstract**") or line.startswith("*Index Terms*"):
            flush()
            out.append(f'<p class="abstract">{inline(line)}</p>')
            i += 1; continue

        if re.match(r"^\[\d+\]", line):
            flush()
            out.append(f'<p class="ref">{inline(line)}</p>')
            i += 1; continue

        if line.startswith("**") and line.endswith("**") and len(line) < 90:
            flush()
            out.append(f'<p class="lead">{inline(line)}</p>')
            i += 1; continue

        in_para.append(line.strip())
        i += 1

    flush()
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 17mm 15mm 17mm 15mm; }
* { box-sizing: border-box; }
body {
  font-family: 'Times New Roman', Times, serif;
  font-size: 10pt; line-height: 1.09; margin: 0; color: #000;
  text-align: justify; hyphens: auto;
}
.title {
  font-size: 22pt; font-weight: 400; text-align: center; line-height: 1.15;
  margin: 0 0 14pt; column-span: all; font-family: 'Times New Roman', serif;
}
.authors {
  column-span: all; text-align: center; font-size: 10pt; margin: 0 0 16pt;
  line-height: 1.3;
}
/* IEEE sets author blocks in a centred grid; five authors take three then two, as
   the reference paper does, so the second row is centred under the first. */
.arow { display: flex; justify-content: center; gap: 10mm; margin-bottom: 8pt; }
.arow-2 { gap: 16mm; }
.authors .author { min-width: 42mm; }
.authors .name { font-size: 11pt; margin-bottom: 1pt; }
.authors .aff { font-style: italic; }
.authors .mail { word-break: break-all; }
.body { column-count: 2; column-gap: 6mm; }
h2.sec {
  font-size: 10pt; font-weight: 400; text-align: center; text-transform: none;
  margin: 7pt 0 2pt; break-after: avoid;
}
h2.sec .sc { font-variant: small-caps; }
h3.sub {
  font-size: 10pt; font-weight: 400; font-style: italic; text-align: left;
  margin: 9pt 0 3pt; break-after: avoid;
}
p { margin: 0 0 0; text-indent: 12pt; }
p + p { margin-top: 0; }
p.abstract { font-weight: bold; font-style: italic; text-indent: 0; margin-bottom: 8pt; }
p.lead { text-indent: 12pt; }
p.ref {
  font-size: 7.3pt; text-indent: -9pt; padding-left: 9pt; margin-bottom: 1pt;
  text-align: left;
}
h2.refs-head { text-align: center; }
table.ieee {
  width: 100%; border-collapse: collapse; font-size: 7.4pt; margin: 3pt 0 7pt;
  break-inside: avoid; text-align: center;
}
table.ieee th {
  border-top: 1px solid #000; border-bottom: 1px solid #000;
  padding: 2pt 3pt; font-weight: 400; font-style: italic;
}
table.ieee td { padding: 1.8pt 3pt; border-bottom: 0.4pt solid #999; }
table.ieee tr:last-child td { border-bottom: 1px solid #000; }
figure.ieee {
  margin: 5pt 0 6pt; text-align: center; break-inside: avoid;
}
pre.fig {
  font-family: 'Menlo', 'DejaVu Sans Mono', 'Courier New', monospace;
  font-size: 5.4pt; line-height: 1.05; margin: 0 0 4pt; display: inline-block;
  text-align: left; white-space: pre;
}
figure.ieee.chart svg { max-width: 100%; height: auto; }
figure.ieee figcaption {
  font-size: 8pt; text-align: justify; margin: 0 auto; max-width: 100%;
}
code { font-family: 'Courier New', monospace; font-size: 8.5pt; }
strong { font-weight: bold; }
"""


def main() -> None:
    md = (HERE / "paper.md").read_text()

    # The author block is set by hand: IEEE centres it above the columns, and the
    # markdown byline cannot express that layout.
    md = re.sub(r"^Varnit Jain, Tanu.*?\n---\n", "", md, flags=re.S | re.M)
    title_match = re.search(r"^# (.+)$", md, flags=re.M)
    title = title_match.group(1) if title_match else "Paper"
    md = md.replace(f"# {title}\n", "", 1)

    authors = """
<div class="authors">
<div class="arow arow-3">
  <div class="author">
    <div class="name">Varnit Jain</div>
    <div class="aff">Computer Science</div>
    <div class="aff">KIET Group of Institutions</div>
    <div>Ghaziabad, Delhi-NCR</div>
    <div class="mail">varnit.2327cs1237@kiet.edu</div>
  </div>
  <div class="author">
    <div class="name">Tanu</div>
    <div class="aff">Computer Science</div>
    <div class="aff">KIET Group of Institutions</div>
    <div>Ghaziabad, Delhi-NCR</div>
    <div class="mail">tanu.2327cs1027@kiet.edu</div>
  </div>
  <div class="author">
    <div class="name">Yash Yadav</div>
    <div class="aff">Computer Science</div>
    <div class="aff">KIET Group of Institutions</div>
    <div>Ghaziabad, Delhi-NCR</div>
    <div class="mail">yash.2327csit1035@kiet.edu</div>
  </div>
</div>
<div class="arow arow-2">
  <div class="author">
    <div class="name">Swarna Chaudhary</div>
    <div class="aff">Computer Science</div>
    <div class="aff">KIET Group of Institutions</div>
    <div>Ghaziabad, Delhi-NCR</div>
    <div class="mail">Swarna.2327cs1026@kiet.edu</div>
  </div>
  <div class="author">
    <div class="name">Prof. Sunil</div>
    <div class="aff">Computer Science</div>
    <div class="aff">KIET Group of Institutions</div>
    <div>Ghaziabad, Delhi-NCR</div>
  </div>
</div>
</div>"""

    page = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>{CSS}</style></head><body>
<h1 class="title">{inline(title)}</h1>
{authors}
<div class="body">
{convert(md)}
</div>
</body></html>"""

    out = HERE / "paper.html"
    out.write_text(page)
    print(f"  wrote {out.name}: {len(page):,} bytes")


if __name__ == "__main__":
    main()
