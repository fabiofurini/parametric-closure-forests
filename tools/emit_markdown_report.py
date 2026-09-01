#!/usr/bin/env python3
"""Generate the browsable Markdown edition of the computational report.

The PDF report (report/computational_report.tex) is the citable artefact; this
tool renders the same content as a set of cross-linked Markdown pages under
docs/report/, one page per section, so the results can be navigated on GitHub
without downloading a PDF. Nothing is written twice: the prose, the captions and
the table fragments all come from the LaTeX source, and each plot is compiled
from the very same tikzpicture into a PNG.

  python3 tools/emit_markdown_report.py            # pages + plot images
  python3 tools/emit_markdown_report.py --no-plots # pages only (no LaTeX run)

Requires pdflatex and pdftocairo for the plots; with --no-plots neither is used.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# ---------------------------------------------------------------- brace parsing


def read_group(text: str, start: int) -> tuple[str, int]:
    """Read a brace-delimited group starting at text[start] == '{'.
    Returns its content and the index just past the closing brace."""
    assert text[start] == "{", text[start:start + 40]
    depth, i = 0, start
    while i < len(text):
        if text[i] == "\\":
            i += 2
            continue
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i], i + 1
        i += 1
    raise ValueError("unbalanced braces")


def read_args(text: str, pos: int, count: int) -> tuple[list[str], int]:
    args = []
    for _ in range(count):
        while pos < len(text) and text[pos] in " \n\t%":
            pos += 1
        group, pos = read_group(text, pos)
        args.append(group)
    return args, pos


# ------------------------------------------------------------ inline conversion

INLINE = [
    (r"\\texttt\{([^{}]*)\}", r"`\1`"),
    (r"\\path\{([^{}]*)\}", r"`\1`"),
    (r"\\emph\{([^{}]*)\}", r"*\1*"),
    (r"\\textbf\{([^{}]*)\}", r"**\1**"),
    (r"\\textit\{([^{}]*)\}", r"*\1*"),
    (r"\\url\{([^{}]*)\}", r"<\1>"),
    (r"\\sloppy", ""),
    (r"\\noindent", ""),
    (r"\\centering", ""),
    (r"\\small|\\scriptsize|\\tiny|\\normalsize", ""),
    (r"\\vspace\{[^{}]*\}", ""),
    (r"\\setlength\{[^{}]*\}\{[^{}]*\}", ""),
    (r"\\label\{([^{}]*)\}", ""),
    (r"\\,", "\u2009"),          # thin space
    (r"\\;", " "),
    (r"\\ ", " "),
    (r"\\%", "%"),
    (r"\\&", "&"),
    (r"\\#", "#"),
    (r"\\_", "_"),
    (r"\\dots", "…"),
    (r"\\emdash|---", "—"),
    (r"--", "–"),
    (r"``", "\u201c"),
    (r"''", "\u201d"),
    (r"\\i\.e\.\\?", "i.e."),
    (r"\\@", ""),
]


def crefs(text: str, anchors: dict[str, tuple[str, str]]) -> str:
    """Turn \\cref{a,b} into Markdown links to the page/anchor they live on."""
    def one(match: re.Match) -> str:
        names = [n.strip() for n in match.group(2).split(",")]
        parts = []
        for name in names:
            if name in anchors:
                page, title = anchors[name]
                parts.append(f"[{title}]({page})")
            else:
                parts.append(name.split(":")[-1].replace("_", " "))
        cap = match.group(1)[0] == "C"
        joined = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
        return joined if not cap else joined
    return re.sub(r"\\(c|C)ref\{([^{}]*)\}", one, text)


def strip_comments(text: str) -> str:
    """Drop LaTeX comments: an unescaped % to the end of its line. The \tabfig
    arguments all start with one (the line-continuation idiom `{%`)."""
    return re.sub(r"(?<!\\)%.*", "", text)


def replace_macro(text: str, name: str, wrap: str) -> str:
    """Brace-aware replacement of \name{...}: the regexes below cannot do it
    when the argument itself contains braces or math."""
    needle = "\\" + name + "{"
    while needle in text:
        start = text.index(needle)
        body, end = read_group(text, start + len(needle) - 1)
        if "$" in body and wrap == "`":
            # code font would swallow the math: keep the content as it is
            replacement = body
        else:
            replacement = f"{wrap}{body}{wrap}"
        text = text[:start] + replacement + text[end:]
    return text


def inline(text: str, anchors: dict[str, tuple[str, str]] | None = None) -> str:
    text = strip_comments(text)
    text = crefs(text, anchors or {})
    for name, wrap in (("texttt", "`"), ("path", "`"), ("textbf", "**"),
                       ("emph", "*"), ("textit", "*")):
        text = replace_macro(text, name, wrap)
    # \rev{...} (the manuscript's revision colour) has no meaning here
    while "\\rev{" in text:
        start = text.index("\\rev{") + 4
        body, end = read_group(text, start)
        text = text[:start - 4] + body + text[end:]
    # Math is passed through untouched: GitHub renders $...$ with KaTeX, which
    # wants LaTeX in there (\% is a percent sign, a bare % starts a comment).
    parts = re.split(r"(\$[^$]*\$)", text)
    for index, part in enumerate(parts):
        if part.startswith("$"):
            continue
        for pattern, repl in INLINE:
            part = re.sub(pattern, repl, part)
        parts[index] = part
    text = "".join(parts)
    text = text.replace("\\maketitle", "")
    text = re.sub(r"\\\s*\n", " ", text)      # a line-continuation backslash
    text = re.sub(r"\s*\n\s*", " ", text)      # LaTeX hard wrapping is not MD
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


# ------------------------------------------------------------- table conversion


def strip_tex_cell(cell: str) -> str:
    cell = cell.strip()
    cell = re.sub(r"\\multicolumn\{\d+\}\{[^{}]*\}\{(.*)\}", r"\1", cell)
    return inline(cell)


def tabular_to_markdown(tex: str) -> str:
    """Convert one booktabs `tabular` (as emitted by the tools) to a Markdown
    table. Group headers spanning several columns are flattened into the header
    row, since Markdown has no multi-row headers."""
    start = tex.find("\\begin{tabular}")
    if start == -1 or "\\end{tabular}" not in tex:
        return ""
    _, after = read_group(tex, tex.index("{", start + len("\\begin{tabular}")))
    body = re.match(r"(?s)(.*)", tex[after:tex.index("\\end{tabular}")])
    lines = []
    group = None
    for position, raw in enumerate(body.group(1).split("\\\\")):
        if group is None and "\\multicolumn" in raw and not lines:
            cells = raw.split("&")
            for index, cell in enumerate(cells):
                match = re.search(r"\\multicolumn\{(\d+)\}\{[^{}]*\}\{(.*)\}",
                                  cell.strip(), re.S)
                if match:
                    group = (index, inline(match.group(2)))
                    break
        raw = raw.replace("\\toprule", "").replace("\\bottomrule", "")
        raw = re.sub(r"\\cmidrule(\(l?r?\))?\{[^}]*\}", "", raw)
        raw = raw.replace("\\midrule", "")
        if not raw.strip():
            continue
        lines.append([strip_tex_cell(c) for c in raw.split("&")])
    if not lines:
        return ""
    # A leading \multicolumn row is a group header. Markdown has no spanning
    # cells, so the label is prefixed to the first column the group covers.
    header, rest = lines[0], lines[1:]
    if rest and group is not None:
        start, label = group
        header = rest[0]
        rest = rest[1:]
        if label and start < len(header):
            header[start] = f"{label}: {header[start]}"
    width = max(len(r) for r in [header] + rest)
    header += [""] * (width - len(header))
    out = ["| " + " | ".join(header) + " |",
           "|" + "|".join(["---"] * width) + "|"]
    for row in rest:
        row = row + [""] * (width - len(row))
        out.append("| " + " | ".join(row) + " |")
    return "\n".join(out)


# ------------------------------------------------------------------ plot images

PREAMBLE_KEYS = ("\\pgfplotsset", "\\definecolor", "\\usetikzlibrary",
                 "\\usepgfplotslibrary", "\\pgfplotscreateplotcyclelist",
                 "\\newcommand{\\dat}", "\\newcommand{\\dfile}")


def latex_preamble(source: str) -> str:
    """Everything the tikzpictures need: the pgfplots setup of the report."""
    keep = []
    for block in re.split(r"\n(?=\\)", source.split("\\begin{document}")[0]):
        if any(block.startswith(key) for key in PREAMBLE_KEYS):
            keep.append(block)
    return "\n".join(keep)


def render_plot(tikz: str, preamble: str, out_png: Path, tables_dir: Path,
                dpi: int = 160) -> bool:
    """Compile one tikzpicture standalone and convert it to PNG."""
    document = "\n".join([
        "\\documentclass[border=4pt]{standalone}",
        "\\usepackage{amsmath}\\usepackage{amssymb}\\usepackage{lmodern}",
        "\\usepackage{pgfplots}",
        "\\pgfplotsset{compat=1.18}",
        preamble,
        "\\begin{document}", tikz, "\\end{document}"])
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        # \dat / \dfile resolve to ../results/tables, i.e. relative to the
        # report directory: reproduce that layout so the data files are found.
        (work / "results").mkdir()
        (work / "results" / "tables").symlink_to(tables_dir.resolve())
        build = work / "report"
        build.mkdir()
        (build / "plot.tex").write_text(document, encoding="utf-8")
        run = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "plot.tex"],
            cwd=build, capture_output=True, text=True)
        pdf = build / "plot.pdf"
        if not pdf.exists():
            tail = "\n".join(run.stdout.splitlines()[-12:])
            print(f"  !! {out_png.name}: pdflatex failed\n{tail}")
            return False
        out_png.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["pdftocairo", "-png", "-r", str(dpi), "-singlefile",
                        str(pdf), str(out_png.with_suffix(""))], check=True)
    return True


# ------------------------------------------------------------- document walking

class Block:
    """One piece of the document: prose, a figure, or a table."""

    def __init__(self, kind: str, **kw):
        self.kind = kind
        self.__dict__.update(kw)


def parse_body(source: str) -> list[Block]:
    body = source.split("\\begin{document}", 1)[1].split("\\end{document}")[0]
    blocks: list[Block] = []
    prose: list[str] = []
    i = 0

    def flush() -> None:
        text = "".join(prose).strip()
        if text:
            blocks.append(Block("prose", text=text))
        prose.clear()

    while i < len(body):
        if body.startswith("\\tabfig{", i) or body.startswith("\\tabfigwide{", i):
            flush()
            wide = body.startswith("\\tabfigwide{", i)
            pos = i + (len("\\tabfigwide") if wide else len("\\tabfig"))
            (label, caption, table, plot), i = read_args(body, pos, 4)
            blocks.append(Block("figure", label=label, caption=caption,
                                table=table, plot=plot, wide=wide))
            continue
        if body.startswith("\\begin{table}", i):
            flush()
            end = body.index("\\end{table}", i) + len("\\end{table}")
            chunk = body[i:end]
            caption = ""
            if "\\caption{" in chunk:
                start = chunk.index("\\caption{") + len("\\caption") 
                caption, _ = read_group(chunk, start)
            label = ""
            if "\\label{" in chunk:
                start = chunk.index("\\label{") + len("\\label")
                label, _ = read_group(chunk, start)
            blocks.append(Block("table", label=label, caption=caption,
                                content=chunk))
            i = end
            continue
        for macro, kind in (("\\section{", "section"),
                            ("\\subsection{", "subsection"),
                            ("\\paragraph{", "paragraph")):
            if body.startswith(macro, i):
                flush()
                title, j = read_group(body, i + len(macro) - 1)
                label = ""
                rest = body[j:j + 60]
                match = re.match(r"\s*\\label\{([^{}]*)\}", rest)
                if match:
                    label = match.group(1)
                    j += match.end()
                blocks.append(Block(kind, title=title, label=label))
                i = j
                break
        else:
            if body.startswith("\\appendix", i):
                flush()
                blocks.append(Block("appendix"))
                i += len("\\appendix")
                continue
            if body.startswith("\\tableofcontents", i):
                i += len("\\tableofcontents")
                continue
            prose.append(body[i])
            i += 1
    flush()
    return blocks


ENVIRONMENTS = ("itemize", "enumerate", "verbatim")


def prose_to_markdown(text: str, anchors) -> str:
    """Convert the prose subset used by the report: paragraphs, itemize,
    enumerate, verbatim."""
    out: list[str] = []
    i = 0
    while i < len(text):
        env_hit = None
        for env in ENVIRONMENTS:
            if text.startswith(f"\\begin{{{env}}}", i):
                env_hit = env
                break
        if env_hit:
            end = text.index(f"\\end{{{env_hit}}}", i)
            inner = text[i + len(f"\\begin{{{env_hit}}}"):end]
            i = end + len(f"\\end{{{env_hit}}}")
            if env_hit == "verbatim":
                out.append("\n```\n" + inner.strip("\n") + "\n```\n")
                continue
            inner = re.sub(r"^\s*\[[^\]]*\]", "", inner)
            items = [x for x in re.split(r"\\item\b", inner)[1:]]
            bullet = "-" if env_hit == "itemize" else None
            for number, item in enumerate(items, 1):
                mark = bullet or f"{number}."
                out.append(f"{mark} " + inline(item, anchors))
            out.append("")
            continue
        chunk_end = len(text)
        for env in ENVIRONMENTS:
            pos = text.find(f"\\begin{{{env}}}", i)
            if pos != -1:
                chunk_end = min(chunk_end, pos)
        chunk = text[i:chunk_end]
        i = chunk_end
        for paragraph in re.split(r"\n\s*\n", chunk):
            converted = inline(paragraph, anchors)
            if converted:
                out.append(converted)
                out.append("")
    return "\n".join(out).strip()


# --------------------------------------------------------------- page assembly

def slug(title: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", inline(title).lower()).strip("-")
    return text or "section"


def build_pages(blocks: list[Block]) -> list[dict]:
    """Split the blocks into one page per \\section, keeping the front matter
    (everything before the first section) as the landing page."""
    pages: list[dict] = [{"title": "Overview", "file": "README.md",
                          "blocks": [], "appendix": False}]
    in_appendix = False
    number = 0
    for block in blocks:
        if block.kind == "appendix":
            in_appendix = True
            continue
        if block.kind == "section":
            number += 1
            pages.append({"title": inline(block.title), "label": block.label,
                          "file": f"{number:02d}-{slug(block.title)}.md",
                          "blocks": [], "appendix": in_appendix})
            continue
        pages[-1]["blocks"].append(block)
    return pages


def collect_anchors(pages: list[dict]) -> dict[str, tuple[str, str]]:
    """label -> (page, link text), so \\cref becomes a working link."""
    anchors: dict[str, tuple[str, str]] = {}
    figure_number = table_number = 0
    for page in pages:
        if page.get("label"):
            anchors[page["label"]] = (page["file"], page["title"])
        for block in page["blocks"]:
            if block.kind == "figure":
                figure_number += 1
                anchors[block.label] = (
                    f"{page['file']}#figure-{figure_number}",
                    f"Figure {figure_number}")
                block.number = figure_number
            elif block.kind == "table":
                table_number += 1
                if block.label:
                    anchors[block.label] = (
                        f"{page['file']}#table-{table_number}",
                        f"Table {table_number}")
                block.number = table_number
            elif block.kind in ("subsection", "paragraph") and block.label:
                anchors[block.label] = (
                    f"{page['file']}#{slug(block.title)}", inline(block.title))
    return anchors


def figure_markdown(block: Block, anchors, image: str | None) -> str:
    out = [f'<a id="figure-{block.number}"></a>', "",
           f"**Figure {block.number}.** {inline(block.caption, anchors)}", ""]
    table = block.table
    match = re.search(r"\\tab\{([a-z_0-9]+)\}", table)
    if match:
        path = TABLES / f"{match.group(1)}.tex"
        table = path.read_text(encoding="utf-8") if path.exists() else ""
    md_table = tabular_to_markdown(table)
    if md_table:
        out += [md_table, ""]
    if image:
        out += [f"![Figure {block.number}]({image})", ""]
    return "\n".join(out)


def table_markdown(block: Block, anchors) -> str:
    content = block.content
    inner = content
    match = re.search(r"\\tab\{([a-z_0-9]+)\}", content)
    if match:
        path = TABLES / f"{match.group(1)}.tex"
        inner = path.read_text(encoding="utf-8") if path.exists() else ""
    out = [f'<a id="table-{block.number}"></a>', "",
           f"**Table {block.number}.** {inline(block.caption, anchors)}", ""]
    md_table = tabular_to_markdown(inner)
    if md_table:
        out += [md_table, ""]
    return "\n".join(out)


def render_page(page: dict, pages: list[dict], index: int, anchors,
                images: dict[str, str]) -> str:
    out = [f"# {page['title']}", ""]
    for block in page["blocks"]:
        if block.kind == "prose":
            text = prose_to_markdown(block.text, anchors)
            if text:
                out += [text, ""]
        elif block.kind == "subsection":
            out += [f"## {inline(block.title)}", ""]
        elif block.kind == "paragraph":
            out += [f"### {inline(block.title).rstrip('.')}", ""]
        elif block.kind == "figure":
            out += [figure_markdown(block, anchors, images.get(block.label)), ""]
        elif block.kind == "table":
            out += [table_markdown(block, anchors), ""]
    nav = ["---", ""]
    previous = pages[index - 1] if index > 0 else None
    following = pages[index + 1] if index + 1 < len(pages) else None
    bits = []
    if previous:
        bits.append(f"← [{previous['title']}]({previous['file']})")
    bits.append("[Contents](README.md)")
    if following:
        bits.append(f"[{following['title']}]({following['file']}) →")
    nav.append(" · ".join(bits))
    return "\n".join(out + nav) + "\n"


def contents_markdown(pages: list[dict]) -> str:
    out = ["", "## Contents", ""]
    for page in pages[1:]:
        if page["appendix"] and "appendix" not in "".join(out[-3:]).lower():
            out += ["", "### Appendix", ""]
        out.append(f"- [{page['title']}]({page['file']})")
    out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------- driver

REPO = Path(__file__).resolve().parent.parent
TABLES = REPO / "results" / "tables"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path,
                        default=REPO / "report" / "computational_report.tex")
    parser.add_argument("--output-dir", type=Path,
                        default=REPO / "docs" / "report")
    parser.add_argument("--no-plots", action="store_true",
                        help="skip the plot images (no pdflatex run)")
    parser.add_argument("--dpi", type=int, default=160)
    args = parser.parse_args()

    source = args.source.read_text(encoding="utf-8")
    blocks = parse_body(source)
    pages = build_pages(blocks)
    anchors = collect_anchors(pages)

    out_dir = args.output_dir
    image_dir = out_dir / "images"
    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    images: dict[str, str] = {}
    if not args.no_plots:
        preamble = latex_preamble(source)
        figures = [(p, b) for p in pages for b in p["blocks"]
                   if b.kind == "figure"]
        print(f"rendering {len(figures)} plots ...")
        for page, block in figures:
            name = f"fig{block.number:02d}-{block.label.split(':')[-1]}"
            png = image_dir / f"{name}.png"
            if render_plot(block.plot, preamble, png, TABLES, args.dpi):
                images[block.label] = f"images/{png.name}"

    front = pages[0]
    body = render_page(front, pages, 0, anchors, images)
    # the landing page carries the table of contents
    body = body.replace("---\n\n[Contents](README.md)",
                        contents_markdown(pages) + "\n---\n")
    body = re.sub(r"\n---\n\s*·\s*", "\n---\n\nNext: ", body)
    header = ("# Parametric Maximum Closure on Directed Forests\n"
              "## Computational report — data release `v0.3.0`\n\n"
              "Valerio Dose · Fabio Furini · Marco Locatelli\n\n"
              "*Browsable edition of "
              "[`report/computational_report.pdf`](../../report/computational_report.pdf); "
              "generated from the same LaTeX source by "
              "`tools/emit_markdown_report.py`, so the numbers are the same.*\n")
    body = re.sub(r"^# Overview\n", header, body)
    (out_dir / "README.md").write_text(body, encoding="utf-8")
    print(f"wrote {out_dir / 'README.md'}")
    for index, page in enumerate(pages[1:], start=1):
        text = render_page(page, pages, index, anchors, images)
        (out_dir / page["file"]).write_text(text, encoding="utf-8")
        print(f"wrote {out_dir / page['file']}")


if __name__ == "__main__":
    main()
