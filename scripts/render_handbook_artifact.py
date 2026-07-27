# /// script
# requires-python = ">=3.11"
# dependencies = ["markdown>=3.5"]
# ///
"""Render the engineering handbook into a single self-contained HTML artifact.

The prose is produced verbatim by a Markdown converter over
``docs/engineering/*.md``, so the HTML text is identical to the repo; only
cross-links (``foo.md`` -> ``#anchor``) and table / task-list markup are
transformed, and the result is wrapped in a styled, single-page shell (sidebar
nav, light/dark theme toggle, scroll-spy). Re-run after editing any doc to
regenerate the shareable artifact; there is no hand-maintained copy to drift.

Usage::

    # standalone (uv fetches `markdown` from the inline dependency header)
    uv run scripts/render_handbook_artifact.py
    uv run scripts/render_handbook_artifact.py --out /tmp/handbook.html
    uv run scripts/render_handbook_artifact.py --docs-dir docs/engineering --out build/handbook.html

The output is a fragment (``<title> + <style> + <body> markup + <script>``)
suitable for publishing as a Claude artifact, and it also renders as a complete
page when opened directly in a browser.

NOT a CI test. The pure transforms (:func:`rewrite_links`, :func:`wrap_tables`,
:func:`mark_task_items`) are unit-tested in ``tests/scripts/``.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

# (anchor id, markdown stem, sidebar label). Order defines the page order;
# README is the intro section (#top), the eight parts follow, the coda closes.
PARTS: list[tuple[str, str, str]] = [
    ("top", "README", "Overview &amp; the story"),
    ("p1", "lifecycle", "Development lifecycle"),
    ("p2", "codebase-structure", "Codebase structure"),
    ("p3", "three-layer-model", "Three-layer model"),
    ("p4", "agent-harness", "The agent harness"),
    ("p5", "observability", "Observability"),
    ("p6", "evaluation", "Evaluation"),
    ("p7", "documentation", "Documentation"),
    ("p8", "security-supply-chain", "Security &amp; supply chain"),
    ("coda", "coda", "Coda"),
]

# `<stem>.md` -> in-page anchor, used to turn repo cross-links into scroll links.
LINKMAP: dict[str, str] = {stem + ".md": "#" + anchor for anchor, stem, _ in PARTS}


def rewrite_links(html: str, linkmap: dict[str, str]) -> tuple[str, list[str]]:
    """Rewrite ``*.md`` hrefs to in-page anchors.

    Returns the rewritten HTML and the list of hrefs that could not be mapped
    (external links, or docs outside the handbook), so the caller can warn.
    """
    unmapped: list[str] = []

    def repl(m: re.Match[str]) -> str:
        href = m.group(1)
        base = href.split("#")[0]
        anchor = linkmap.get(base)
        if anchor is not None:
            return f'href="{anchor}"'
        unmapped.append(href)
        return m.group(0)

    out = re.sub(r'href="([^"]+\.md[^"]*)"', repl, html)
    return out, unmapped


def wrap_tables(html: str) -> str:
    """Wrap every ``<table>`` in an overflow container so wide tables scroll."""
    return html.replace("<table>", '<div class="tablewrap"><table>').replace(
        "</table>", "</table></div>"
    )


def mark_task_items(html: str) -> str:
    """Turn GitHub-style task-list items into styled checkbox rows.

    ``<li>[ ] text`` -> ``<li class="task">text`` and ``<li>[x] text`` ->
    ``<li class="task done">text``. The item text itself is left untouched.
    """
    html = re.sub(r"<li>\s*\[ \]\s*", '<li class="task">', html)
    html = re.sub(r"<li>\s*\[[xX]\]\s*", '<li class="task done">', html)
    return html


def post_process(html: str, linkmap: dict[str, str]) -> tuple[str, list[str]]:
    """Apply all HTML transforms; return the result and any unmapped hrefs."""
    html, unmapped = rewrite_links(html, linkmap)
    html = wrap_tables(html)
    html = mark_task_items(html)
    return html, unmapped


def render_doc(
    docs_dir: Path, stem: str, linkmap: dict[str, str]
) -> tuple[str, list[str]]:
    """Convert one markdown doc to post-processed HTML (lazy-imports markdown)."""
    import markdown  # lazy: keeps the pure helpers importable without the dep

    md = (docs_dir / f"{stem}.md").read_text()
    html = markdown.markdown(md, extensions=["tables", "fenced_code", "sane_lists"])
    return post_process(html, linkmap)


def render_nav(parts: list[tuple[str, str, str]]) -> str:
    """Build the sidebar table-of-contents markup."""
    rows = []
    for i, (anchor, _, label) in enumerate(parts):
        lead = ' class="lead"' if anchor == "top" else ""
        num = "§" if anchor == "top" else "∎" if anchor == "coda" else f"{i:02d}"
        rows.append(
            f'      <a href="#{anchor}"{lead}><span class="num">{num}</span>'
            f"<span>{label}</span></a>"
        )
    return "\n".join(rows)


def to_ascii_entities(html: str) -> str:
    """Escape every non-ASCII character to a numeric HTML entity.

    The artifact host serves the page from a wrapper whose ``<head>`` we do not
    control, so we cannot declare ``<meta charset="utf-8">``. Raw UTF-8 bytes
    then mojibake under a Latin-1 interpretation (``·`` -> ``Â·``). Numeric
    entities are pure ASCII and render as the same glyph under any charset.
    """
    return html.encode("ascii", "xmlcharrefreplace").decode("ascii")


def build(docs_dir: Path, parts: list[tuple[str, str, str]] = PARTS) -> str:
    """Render the full handbook artifact HTML from ``docs_dir``."""
    linkmap = {stem + ".md": "#" + anchor for anchor, stem, _ in parts}
    sections = []
    for anchor, stem, _ in parts:
        cls = "part intro" if anchor == "top" else "part"
        html, unmapped = render_doc(docs_dir, stem, linkmap)
        for href in unmapped:
            print(f"  WARNING unmapped link in {stem}.md: {href}")
        sections.append(
            f'    <section id="{anchor}" class="{cls}">\n'
            f'      <div class="col doc">\n{html}\n      </div>\n    </section>'
        )
    body = _BODY % {"nav": render_nav(parts), "sections": "\n".join(sections)}
    return to_ascii_entities(_HEAD + body + _SCRIPT)


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=repo_root / "docs" / "engineering",
        help="Directory holding the handbook markdown (default: docs/engineering).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=repo_root / "test-reports" / "handbook.html",
        help="Output HTML path (default: test-reports/handbook.html, gitignored).",
    )
    args = parser.parse_args(argv)

    html = build(args.docs_dir)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(html)

    residual = len(re.findall(r'href="[^"]+\.md', html))
    print(f"wrote {args.out} ({len(html)} bytes)")
    print(
        f"  sections: {html.count('<section id=')}  "
        f"task items: {html.count('class="task')}  "
        f"em-dashes: {html.count(chr(8212))}  "
        f"residual .md hrefs: {residual}"
    )
    return 0


_HEAD = """<title>AI Agent Development Handbook</title>
<style>
  :root {
    --bg: #edece6; --surface: #f7f6f2; --surface-2: #e6e4db;
    --ink: #1c2024; --ink-soft: #4b5057; --ink-faint: #6d7178;
    --line: #d6d3c8; --line-strong: #c3bfb1;
    --accent: #9a6a1c; --accent-ink: #6f4c12; --accent-wash: #ece2cd;
    --shadow: 0 1px 2px rgba(28,32,36,.05), 0 8px 30px rgba(28,32,36,.06);
    --serif: ui-serif, Georgia, "Iowan Old Style", Palatino, "Book Antiqua", serif;
    --sans: system-ui, -apple-system, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    --mono: ui-monospace, "SF Mono", "Cascadia Code", Menlo, Consolas, monospace;
    --measure: 72ch;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #16181c; --surface: #1e2126; --surface-2: #23272d;
      --ink: #e9e7df; --ink-soft: #adaaa0; --ink-faint: #85837b;
      --line: #2b3037; --line-strong: #3a4048;
      --accent: #d9a441; --accent-ink: #e7bd6c; --accent-wash: #2a2519;
      --shadow: 0 1px 2px rgba(0,0,0,.3), 0 10px 34px rgba(0,0,0,.34);
    }
  }
  :root[data-theme="light"] {
    --bg: #edece6; --surface: #f7f6f2; --surface-2: #e6e4db;
    --ink: #1c2024; --ink-soft: #4b5057; --ink-faint: #6d7178;
    --line: #d6d3c8; --line-strong: #c3bfb1;
    --accent: #9a6a1c; --accent-ink: #6f4c12; --accent-wash: #ece2cd;
    --shadow: 0 1px 2px rgba(28,32,36,.05), 0 8px 30px rgba(28,32,36,.06);
  }
  :root[data-theme="dark"] {
    --bg: #16181c; --surface: #1e2126; --surface-2: #23272d;
    --ink: #e9e7df; --ink-soft: #adaaa0; --ink-faint: #85837b;
    --line: #2b3037; --line-strong: #3a4048;
    --accent: #d9a441; --accent-ink: #e7bd6c; --accent-wash: #2a2519;
    --shadow: 0 1px 2px rgba(0,0,0,.3), 0 10px 34px rgba(0,0,0,.34);
  }

  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  @media (prefers-reduced-motion: reduce) { html { scroll-behavior: auto; } }
  body {
    margin: 0; background: var(--bg); color: var(--ink);
    font-family: var(--sans); font-size: 17px; line-height: 1.62;
    -webkit-font-smoothing: antialiased; text-rendering: optimizeLegibility;
  }

  .wrap { display: grid; grid-template-columns: 260px minmax(0,1fr); max-width: 1200px; margin: 0 auto; }

  .rail {
    position: sticky; top: 0; align-self: start; height: 100vh;
    padding: 34px 26px 34px 32px; border-right: 1px solid var(--line);
    display: flex; flex-direction: column; gap: 22px; overflow-y: auto;
  }
  .brand { display: flex; flex-direction: column; gap: 6px; }
  .brand .mark { font-family: var(--mono); font-size: .68rem; letter-spacing: .22em; text-transform: uppercase; color: var(--accent); }
  .brand .name { font-family: var(--serif); font-size: 1.32rem; line-height: 1.12; letter-spacing: -.01em; }
  nav.toc { display: flex; flex-direction: column; gap: 2px; }
  nav.toc a {
    display: grid; grid-template-columns: 22px 1fr; gap: 10px; align-items: baseline;
    padding: 7px 8px; border-radius: 6px; text-decoration: none; color: var(--ink-soft);
    font-size: .875rem; border: 1px solid transparent; transition: background .18s ease, color .18s ease;
  }
  nav.toc a .num { font-family: var(--mono); font-size: .72rem; color: var(--ink-faint); font-variant-numeric: tabular-nums; }
  nav.toc a:hover { background: var(--surface-2); color: var(--ink); }
  nav.toc a.active { background: var(--accent-wash); color: var(--ink); border-color: var(--line-strong); }
  nav.toc a.active .num { color: var(--accent); }
  nav.toc a.lead { color: var(--ink); font-weight: 600; }
  nav.toc a.lead .num { color: var(--accent); }

  .railfoot { margin-top: auto; display: flex; flex-direction: column; gap: 14px; }
  .toggle {
    display: inline-flex; align-items: center; gap: 8px; background: var(--surface); color: var(--ink);
    border: 1px solid var(--line-strong); border-radius: 999px; padding: 7px 13px;
    font-family: var(--mono); font-size: .72rem; letter-spacing: .06em; cursor: pointer; width: max-content;
  }
  .toggle:hover { border-color: var(--accent); color: var(--accent-ink); }
  .toggle:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  .railfoot .fine { font-family: var(--mono); font-size: .68rem; color: var(--ink-faint); line-height: 1.5; }

  main { padding: 40px clamp(24px,5vw,76px) 96px; min-width: 0; }
  .col { max-width: var(--measure); }
  section.part { padding-top: 40px; scroll-margin-top: 20px; }
  section.part.intro { padding-top: 16px; }

  /* rendered-markdown content */
  .doc h1 {
    font-family: var(--serif); font-weight: 600; font-size: clamp(1.9rem,3.6vw,2.4rem);
    line-height: 1.08; letter-spacing: -.015em; text-wrap: balance;
    margin: 0 0 6px; padding-bottom: 12px; border-bottom: 2px solid var(--accent); display: inline-block;
  }
  .intro .doc h1 { font-size: clamp(2.4rem,6vw,3.6rem); border-bottom: none; padding-bottom: 0; letter-spacing: -.02em; }
  .doc h2 { font-family: var(--serif); font-weight: 600; font-size: 1.42rem; line-height: 1.15; letter-spacing: -.01em; text-wrap: balance; margin: 36px 0 6px; }
  .doc h3 { font-family: var(--sans); font-weight: 700; font-size: 1.04rem; letter-spacing: .005em; margin: 28px 0 4px; }
  .doc p { margin: 14px 0; }
  .doc b, .doc strong { color: var(--ink); font-weight: 650; }
  .doc em, .doc i { color: inherit; }
  .doc a { color: var(--accent-ink); text-decoration: none; border-bottom: 1px solid var(--line-strong); }
  .doc a:hover { border-color: var(--accent); }
  .doc ul, .doc ol { margin: 14px 0; padding-left: 24px; }
  .doc li { position: relative; margin: 6px 0; }
  .doc li::marker { color: var(--accent); }
  .doc code { font-family: var(--mono); font-size: .84em; background: var(--surface-2); padding: 1px 5px; border-radius: 3px; color: var(--accent-ink); }
  .doc pre { background: var(--surface); border: 1px solid var(--line); border-radius: 4px; padding: 14px 16px; overflow-x: auto; margin: 18px 0; }
  .doc pre code { background: none; padding: 0; color: var(--ink-soft); font-size: .86rem; }
  .doc blockquote { margin: 20px 0; padding: 12px 18px; border-left: 3px solid var(--accent); background: var(--surface); border-radius: 4px; color: var(--ink-soft); }
  .doc blockquote > :first-child { margin-top: 0; }
  .doc blockquote > :last-child { margin-bottom: 0; }

  .tablewrap { overflow-x: auto; margin: 20px 0; border: 1px solid var(--line); border-radius: 4px; }
  table { border-collapse: collapse; width: 100%; font-size: .92rem; background: var(--surface); }
  th, td { text-align: left; padding: 10px 14px; vertical-align: top; border-bottom: 1px solid var(--line); }
  thead th { font-family: var(--mono); font-size: .68rem; letter-spacing: .06em; text-transform: uppercase; color: var(--ink-faint); background: var(--surface-2); font-weight: 600; }
  tbody tr:last-child td { border-bottom: none; }
  td code { white-space: nowrap; }

  /* task-list checklists */
  .doc li.task { list-style: none; padding-left: 4px; }
  .doc li.task::before {
    content: ""; position: absolute; left: -20px; top: .32em; width: 14px; height: 14px;
    border: 1px solid var(--line-strong); border-radius: 3px; background: var(--surface-2);
  }
  .doc li.task.done::before { content: "\\2713"; color: var(--accent); font-size: .7rem; line-height: 13px; text-align: center; }

  footer { max-width: var(--measure); margin: 70px 0 0; padding-top: 24px; border-top: 1px solid var(--line); font-size: .82rem; color: var(--ink-faint); }
  footer code { font-family: var(--mono); background: var(--surface-2); padding: 1px 5px; border-radius: 3px; }

  .fade { opacity: 0; transform: translateY(8px); animation: rise .6s ease forwards; }
  @keyframes rise { to { opacity: 1; transform: none; } }
  @media (prefers-reduced-motion: reduce) { .fade { animation: none; opacity: 1; transform: none; } }

  @media (max-width: 860px) {
    .wrap { grid-template-columns: 1fr; }
    .rail { position: static; height: auto; border-right: none; border-bottom: 1px solid var(--line); }
    nav.toc { flex-direction: row; flex-wrap: wrap; gap: 6px; }
    nav.toc a { grid-template-columns: auto auto; }
    .railfoot { margin-top: 6px; }
    main { padding: 28px 22px 64px; }
  }
</style>
"""

_BODY = """
<div class="wrap">
  <aside class="rail">
    <div class="brand">
      <span class="mark">Lidia · Engineering</span>
      <span class="name">AI Agent Development Handbook</span>
    </div>
    <nav class="toc" id="toc">
%(nav)s
    </nav>
    <div class="railfoot">
      <button class="toggle" id="themeBtn" type="button" aria-label="Toggle colour theme">◐ Theme</button>
      <span class="fine">Verbatim render of <br><code>docs/engineering/</code></span>
    </div>
  </aside>

  <main class="fade">
%(sections)s
    <footer class="col">This page is generated verbatim from the handbook in the repository at <code>docs/engineering/</code>; cross-links are rewritten to in-page anchors. When the two disagree, the repo wins.</footer>
  </main>
</div>
"""

_SCRIPT = """
<script>
  (function () {
    var root = document.documentElement;
    var btn = document.getElementById("themeBtn");
    try { var saved = localStorage.getItem("hwd-theme"); if (saved) root.setAttribute("data-theme", saved); } catch (e) {}
    function current() {
      var attr = root.getAttribute("data-theme");
      if (attr) return attr;
      return window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
    }
    btn.addEventListener("click", function () {
      var next = current() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("hwd-theme", next); } catch (e) {}
    });
    var links = Array.prototype.slice.call(document.querySelectorAll("nav.toc a"));
    var map = {};
    links.forEach(function (a) { map[a.getAttribute("href").slice(1)] = a; });
    var reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    // Intercept EVERY in-page #anchor (sidebar nav, the "parts" table, and the
    // "See also" links inside the rendered docs). Letting the fragment trigger a
    // top-level navigation is what the sandboxed artifact frame rejects (403).
    var anchors = Array.prototype.slice.call(document.querySelectorAll('a[href^="#"]'));
    anchors.forEach(function (a) {
      a.addEventListener("click", function (e) {
        var el = document.getElementById(a.getAttribute("href").slice(1));
        if (el) { e.preventDefault(); el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" }); }
      });
    });
    var targets = Object.keys(map).map(function (id) { return document.getElementById(id); }).filter(Boolean);
    if ("IntersectionObserver" in window) {
      var obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          if (en.isIntersecting) {
            links.forEach(function (l) { l.classList.remove("active"); });
            var a = map[en.target.id];
            if (a) a.classList.add("active");
          }
        });
      }, { rootMargin: "-12% 0px -80% 0px", threshold: 0 });
      targets.forEach(function (t) { obs.observe(t); });
    }
  })();
</script>
"""


if __name__ == "__main__":
    raise SystemExit(main())
