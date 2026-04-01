#!/usr/bin/env python3
"""Gearpunk Reader — static site generator.

Run: python generate.py
Output: gearpunk-reader/ (this directory)
"""

import re
import html as html_lib
import subprocess
from pathlib import Path
from datetime import datetime

GEARPUNK = Path("C:/Users/Trist/engineering/gearpunk")
OUT = Path(__file__).parent

CHAPTERS = [
    ("01-the-meridian",         "The Meridian",         1),
    ("02-two-readings",         "Two Readings",          2),
    ("03-the-proof",            "The Proof",             3),
    ("04-the-ratchet",          "The Ratchet",           4),
    ("05-the-conversation",     "The Conversation",      5),
    ("06-the-first-winding",    "The First Winding",     6),
    ("07-eighteen-years-later", "Eighteen Years Later",  7),
    ("08-the-visitor",          "The Visitor",           8),
    ("09-the-temptation",       "The Temptation",        9),
    ("10-the-morning-ticking",  "The Morning Ticking",   10),
]

CHANGELOG = [
    ("2026-04-01", [
        "All 10 chapters revised (2 passes each) — narrator mediation cut, sensory detail added, dialogue made spoken",
        "New spring failure scene added to Chapter 7",
        "Demiurge mythology woven subtly through all chapters",
        "Demiurge Protocol consolidated from two documents into one",
        "Bible updated with cosmology section (gods, the ground, the Crossed Ones)",
        "Under-construction banner added",
    ]),
    ("2026-03-30", [
        "Gearpunk reader site launched",
        "All 10 chapters of The Winding Shift published (first draft)",
        "Gearpunk Bible, Demiurge Protocol, and Voice guide published",
    ]),
]


def get_file_mtime(path):
    """Get file modification time as a formatted date string."""
    if path.exists():
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts).strftime("%B %#d, %Y")
    return None


def get_word_count(path):
    """Rough word count from a markdown file."""
    if path.exists():
        text = path.read_text(encoding="utf-8")
        # Strip markdown headers and blank lines
        words = len(text.split())
        return f"{words:,}"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Markdown → HTML
# ─────────────────────────────────────────────────────────────────────────────

def slugify(t):
    t = t.lower().replace("–", "-").replace("—", "-")
    t = re.sub(r"[^\w\s-]", "", t)
    t = re.sub(r"[\s/]+", "-", t)
    t = re.sub(r"-+", "-", t)
    return t.strip("-")


def inline_md(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    return t


def md_to_html(src):
    """Convert Markdown text to HTML. Returns (html_str, headings_list)."""
    lines = src.split("\n")
    out, headings = [], []
    in_ul = in_ol = False
    para = []
    i = 0

    def fp():
        nonlocal para
        if para:
            txt = " ".join(para).strip()
            if txt:
                out.append(f"<p>{inline_md(txt)}</p>")
            para.clear()

    def ful():
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    def fol():
        nonlocal in_ol
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        ln = lines[i]
        s = ln.strip()

        # Code fence
        if s.startswith("```"):
            fp(); ful(); fol()
            i += 1
            cl = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                cl.append(html_lib.escape(lines[i]))
                i += 1
            out.append(f"<pre><code>{chr(10).join(cl)}</code></pre>")
            i += 1
            continue

        # Heading
        m = re.match(r"^(#{1,6})\s+(.+)$", ln)
        if m:
            fp(); ful(); fol()
            lvl = len(m.group(1))
            txt = m.group(2).strip()
            hid = slugify(txt)
            headings.append((lvl, txt, hid))
            out.append(f'<h{lvl} id="{hid}">{inline_md(txt)}</h{lvl}>')
            i += 1
            continue

        # Horizontal rule → decorative scene break
        if re.match(r"^(-{3,}|\*{3,})\s*$", s):
            fp(); ful(); fol()
            out.append('<div class="scene-break"></div>')
            i += 1
            continue

        # Unordered list
        m = re.match(r"^[ \t]*[-*+]\s+(.+)$", ln)
        if m:
            fp(); fol()
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{inline_md(m.group(1))}</li>")
            i += 1
            continue

        # Ordered list
        m = re.match(r"^[ \t]*\d+\.\s+(.+)$", ln)
        if m:
            fp(); ful()
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{inline_md(m.group(1))}</li>")
            i += 1
            continue

        # Empty line
        if not s:
            fp(); ful(); fol()
            i += 1
            continue

        # Regular paragraph text
        ful(); fol()
        para.append(s)
        i += 1

    fp(); ful(); fol()
    return "\n".join(out), headings


# ─────────────────────────────────────────────────────────────────────────────
# Navigation drawer
# ─────────────────────────────────────────────────────────────────────────────

def nav_html(root, cur):
    """root: '' for root pages, '../' for chapter pages. cur: path like 'bible.html'."""

    def link(href, label, extra_cls=""):
        cls = f"nav-a{extra_cls}" + (" cur" if href == cur else "")
        return f'<a href="{root}{href}" class="{cls}">{label}</a>'

    parts = [
        '<div class="nav-sec">',
        link("index.html", "Home"),
        "</div>",
        '<div class="nav-sec">',
        '<div class="nav-label">World</div>',
        link("bible.html", "Gearpunk Bible"),
        link("demiurge.html", "The Demiurge Protocol"),
        "</div>",
        '<div class="nav-sec">',
        '<div class="nav-label">The Winding Shift</div>',
    ]
    for slug, title, num in CHAPTERS:
        parts.append(link(f"chapters/{slug}.html", f"Ch&nbsp;{num}: {title}", " sub"))
    parts += [
        "</div>",
        '<div class="nav-sec">',
        '<div class="nav-label">Reference</div>',
        link("voice.html", "Voice &amp; Style"),
        link("changelog.html", "Changelog"),
        "</div>",
    ]
    return "\n".join(parts)


# ─────────────────────────────────────────────────────────────────────────────
# In-page TOC
# ─────────────────────────────────────────────────────────────────────────────

def build_toc(headings):
    items = [(l, t, h) for l, t, h in headings if 2 <= l <= 4]
    if not items:
        return ""
    li = [
        f'<li class="t{lvl}"><a href="#{hid}">{html_lib.escape(txt)}</a></li>'
        for lvl, txt, hid in items
    ]
    return (
        '<div class="toc"><div class="toc-title">Contents</div>'
        f'<ol>{"".join(li)}</ol></div>\n'
    )


# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────

CSS = """\
/* Gearpunk Reader — Warm Dark Theme */
:root {
  --bg:             #0f0d0a;
  --surface:        #1a1714;
  --surface-raised: #201d18;
  --border:         #2d2822;
  --text:           #cfc1a8;
  --text-dim:       #7a6e5e;
  --accent:         #c4863a;
  --accent-h:       #d49540;
  --code-bg:        #181510;
  --nav-w:          280px;
  --font:    Georgia, 'Times New Roman', serif;
  --font-ui: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { font-size: 18px; scroll-behavior: smooth; -webkit-text-size-adjust: 100%; }
body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--font);
  line-height: 1.78;
  min-height: 100vh;
}

/* ── Top bar ──────────────────────────────────────────── */
.topbar {
  position: fixed; top: 0; left: 0; right: 0; z-index: 100;
  height: 52px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  display: flex; align-items: center;
  padding: 0 16px; gap: 12px;
}
.menu-btn {
  background: none; border: none; cursor: pointer;
  display: flex; flex-direction: column; gap: 5px;
  padding: 4px; color: var(--text-dim); flex-shrink: 0;
}
.menu-btn span {
  display: block; width: 22px; height: 2px;
  background: currentColor; border-radius: 1px;
  transition: background .2s;
}
.menu-btn:hover span { background: var(--text); }
.site-title {
  font-family: var(--font-ui); font-size: 13px; font-weight: 700;
  letter-spacing: .14em; text-transform: uppercase;
  color: var(--accent); text-decoration: none; flex: 1;
}
.breadcrumb {
  font-family: var(--font-ui); font-size: 11px;
  color: var(--text-dim); letter-spacing: .06em;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  max-width: 160px;
}

/* ── Reading progress bar ─────────────────────────────── */
.progress {
  position: fixed; top: 52px; left: 0; right: 0;
  height: 2px; background: var(--border); z-index: 90;
}
.progress-bar {
  height: 100%; background: var(--accent);
  width: 0%; transition: width .12s linear;
}

/* ── Nav overlay ──────────────────────────────────────── */
.overlay {
  display: none; position: fixed; inset: 0;
  z-index: 150; background: rgba(0,0,0,.65);
}
.overlay.open { display: block; }

/* ── Nav drawer ───────────────────────────────────────── */
.drawer {
  position: fixed; top: 0; left: 0; bottom: 0; z-index: 200;
  width: var(--nav-w);
  background: var(--surface);
  border-right: 1px solid var(--border);
  transform: translateX(-100%);
  transition: transform .25s ease;
  overflow-y: auto;
  overscroll-behavior: contain;
}
.drawer.open { transform: translateX(0); }
.drawer-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid var(--border);
}
.drawer-title {
  font-family: var(--font-ui); font-size: 10px; font-weight: 700;
  letter-spacing: .18em; text-transform: uppercase; color: var(--accent);
}
.drawer-close {
  background: none; border: none; color: var(--text-dim);
  font-size: 22px; cursor: pointer; line-height: 1; padding: 0 4px;
}
.drawer-close:hover { color: var(--text); }
.nav-sec { padding: 5px 0; border-bottom: 1px solid var(--border); }
.nav-label {
  font-family: var(--font-ui); font-size: 9px; font-weight: 700;
  letter-spacing: .2em; text-transform: uppercase;
  color: var(--text-dim); padding: 8px 16px 3px;
}
.nav-a {
  display: block; padding: 7px 16px;
  font-family: var(--font-ui); font-size: 13.5px;
  color: var(--text); text-decoration: none;
  transition: color .15s, background .15s; line-height: 1.3;
}
.nav-a:hover, .nav-a.cur { color: var(--accent); }
.nav-a.cur { background: rgba(196,134,58,.06); }
.nav-a.sub { padding-left: 28px; font-size: 13px; color: var(--text-dim); }
.nav-a.sub:hover, .nav-a.sub.cur { color: var(--accent); }

/* ── Content area ─────────────────────────────────────── */
.content { max-width: 680px; margin: 0 auto; padding: 72px 22px 80px; }
@media (min-width: 640px) { .content { padding: 80px 36px 100px; } }

/* ── Typography ───────────────────────────────────────── */
article h1 {
  font-size: 1.75em; font-weight: normal;
  line-height: 1.25; margin: 2em 0 .5em; color: var(--text);
}
article h1:first-child { margin-top: .35em; }
article h2 {
  font-size: 1.2em; font-weight: normal;
  line-height: 1.3; margin: 2.5em 0 .5em; color: var(--text);
  border-bottom: 1px solid var(--border); padding-bottom: .3em;
}
article h3 {
  font-size: 1em; font-weight: 600;
  margin: 1.8em 0 .4em; color: var(--accent); letter-spacing: .02em;
}
article h4 {
  font-size: .9em; font-weight: 600; font-style: italic;
  margin: 1.4em 0 .3em; color: var(--text-dim);
}
article p { margin-bottom: 1.15em; }
article ul, article ol { margin: .3em 0 1.15em 1.5em; }
article li { margin-bottom: .35em; }
article strong { color: var(--text); font-weight: 600; }
article em { font-style: italic; }
article code {
  font-family: 'Courier New', monospace; font-size: .83em;
  background: var(--code-bg); padding: 1px 5px;
  border-radius: 3px; color: var(--accent);
}
article pre {
  background: var(--code-bg); border: 1px solid var(--border);
  border-radius: 6px; padding: 16px; overflow-x: auto; margin: 1.5em 0;
}
article pre code {
  background: none; padding: 0;
  font-size: .82em; line-height: 1.6; color: var(--text);
}
article blockquote {
  border-left: 3px solid var(--accent);
  margin: 1.5em 0; padding: .5em 0 .5em 1.2em;
  color: var(--text-dim); font-style: italic;
}

/* ── Scene / section break ────────────────────────────── */
.scene-break {
  text-align: center; margin: 2.5em 0;
  color: var(--text-dim); font-size: .8em; letter-spacing: .5em;
}
.scene-break::before { content: '· · ·'; }

/* ── In-page TOC ──────────────────────────────────────── */
.toc {
  background: var(--surface-raised); border: 1px solid var(--border);
  border-radius: 6px; padding: 16px 20px; margin: 0 0 2.5em;
}
.toc-title {
  font-family: var(--font-ui); font-size: 9px; font-weight: 700;
  letter-spacing: .2em; text-transform: uppercase;
  color: var(--text-dim); margin-bottom: 10px;
}
.toc ol { list-style: none; padding: 0; margin: 0; }
.toc li { margin-bottom: 1px; }
.toc a {
  font-family: var(--font-ui); font-size: 12.5px;
  color: var(--text-dim); text-decoration: none;
  display: block; padding: 2px 0;
  transition: color .15s; line-height: 1.4;
}
.toc a:hover { color: var(--accent); }
.toc .t2 { padding-left: 0; }
.toc .t3 { padding-left: 14px; font-size: 12px; }
.toc .t4 { padding-left: 28px; font-size: 11.5px; }

/* ── Chapter prev/next ────────────────────────────────── */
.ch-nav {
  display: flex; justify-content: space-between;
  margin-top: 3em; padding-top: 1.5em;
  border-top: 1px solid var(--border); gap: 12px;
}
.ch-nav a {
  font-family: var(--font-ui); font-size: 12.5px;
  color: var(--text-dim); text-decoration: none;
  padding: 8px 12px; border: 1px solid var(--border);
  border-radius: 4px; transition: color .15s, border-color .15s;
  line-height: 1.35; max-width: 46%;
}
.ch-nav a:hover { color: var(--accent); border-color: var(--accent); }
.ch-nav .nxt { margin-left: auto; text-align: right; }
.ch-nav small {
  display: block; font-size: 10px; letter-spacing: .1em;
  text-transform: uppercase; opacity: .6; margin-bottom: 2px;
}

/* ── Index / landing ──────────────────────────────────── */
.hero {
  padding: 36px 0 28px; border-bottom: 1px solid var(--border);
  margin-bottom: 32px;
}
.hero h1 {
  font-size: 2.1em; font-weight: normal;
  color: var(--text); margin-bottom: 8px; letter-spacing: -.01em;
}
.hero p {
  font-family: var(--font-ui); font-size: 13px;
  color: var(--text-dim); line-height: 1.6;
}
.sec-label {
  font-family: var(--font-ui); font-size: 9px; font-weight: 700;
  letter-spacing: .2em; text-transform: uppercase;
  color: var(--text-dim); margin-bottom: 10px; margin-top: 28px;
  display: block;
}
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(195px, 1fr));
  gap: 9px; margin-bottom: 4px;
}
.card {
  display: block; padding: 13px 15px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 5px; text-decoration: none;
  transition: border-color .15s, background .15s;
}
.card:hover { border-color: var(--accent); background: rgba(196,134,58,.04); }
.card-title { font-size: 14px; color: var(--text); line-height: 1.3; margin-bottom: 2px; }
.card-sub { font-family: var(--font-ui); font-size: 11px; color: var(--text-dim); }

/* ── Chapter metadata ─────────────────────────────────── */
.ch-meta {
  font-family: var(--font-ui); font-size: 11px;
  color: var(--text-dim); letter-spacing: .04em;
  text-align: center; margin-top: 2.5em; padding-bottom: .5em;
}

/* ── Changelog ───────────────────────────────────────── */
.changelog-entry { margin-bottom: 2em; }
.changelog-date {
  font-family: var(--font-ui); font-size: 12px; font-weight: 700;
  color: var(--accent); letter-spacing: .08em;
  margin-bottom: 8px;
}
.changelog-entry ul {
  list-style: none; padding: 0; margin: 0;
}
.changelog-entry li {
  font-size: .9em; color: var(--text-dim);
  padding: 4px 0 4px 16px; line-height: 1.5;
  border-left: 2px solid var(--border);
}

@media print {
  .topbar, .drawer, .overlay, .progress { display: none; }
  .content { padding-top: 0; }
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# JavaScript
# ─────────────────────────────────────────────────────────────────────────────

JS = """\
const menuBtn = document.getElementById('menuBtn');
const drawerClose = document.getElementById('drawerClose');
const drawer = document.getElementById('drawer');
const overlay = document.getElementById('overlay');

function openNav() {
  drawer.classList.add('open');
  overlay.classList.add('open');
  document.body.style.overflow = 'hidden';
}
function closeNav() {
  drawer.classList.remove('open');
  overlay.classList.remove('open');
  document.body.style.overflow = '';
}
menuBtn.addEventListener('click', openNav);
drawerClose.addEventListener('click', closeNav);
overlay.addEventListener('click', closeNav);
drawer.querySelectorAll('a').forEach(a => a.addEventListener('click', closeNav));

const bar = document.querySelector('.progress-bar');
if (bar) {
  function upd() {
    const s = document.documentElement.scrollHeight - window.innerHeight;
    bar.style.width = s > 0 ? (window.scrollY / s * 100) + '%' : '0%';
  }
  window.addEventListener('scroll', upd, { passive: true });
  upd();
}
"""

# ─────────────────────────────────────────────────────────────────────────────
# Page template
# ─────────────────────────────────────────────────────────────────────────────

def page_tmpl(title, breadcrumb, css_path, root, cur, body, extra=""):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{html_lib.escape(title)} — Gearpunk</title>
<link rel="stylesheet" href="{css_path}">
</head>
<body>

<header class="topbar">
  <button class="menu-btn" id="menuBtn" aria-label="Menu">
    <span></span><span></span><span></span>
  </button>
  <a href="{root}index.html" class="site-title">Gearpunk</a>
  <span class="breadcrumb">{breadcrumb}</span>
</header>

<div class="progress"><div class="progress-bar"></div></div>
<div class="overlay" id="overlay"></div>

<nav class="drawer" id="drawer">
  <div class="drawer-head">
    <span class="drawer-title">Navigation</span>
    <button class="drawer-close" id="drawerClose">&#215;</button>
  </div>
  {nav_html(root, cur)}
</nav>

<main class="content">
  <article>
{body}
  </article>
  {extra}
</main>

<script>
{JS}
</script>
</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Page generators
# ─────────────────────────────────────────────────────────────────────────────

def gen_index():
    cards_world = (
        '<a href="bible.html" class="card">'
        '<div class="card-title">Gearpunk Bible</div>'
        '<div class="card-sub">Master worldbuilding reference</div></a>'
        '<a href="demiurge.html" class="card">'
        '<div class="card-title">The Demiurge Protocol</div>'
        '<div class="card-sub">Philosophical companion</div></a>'
    )
    cards_ch = "".join(
        f'<a href="chapters/{slug}.html" class="card">'
        f'<div class="card-title">Ch {num}: {title}</div>'
        f'<div class="card-sub">The Winding Shift</div></a>'
        for slug, title, num in CHAPTERS
    )
    cards_ref = (
        '<a href="voice.html" class="card">'
        '<div class="card-title">Voice &amp; Style Guide</div>'
        '<div class="card-sub">Prose craft reference</div></a>'
    )
    body = f"""\
<div style="background:var(--surface-raised);border:1px solid var(--accent);border-radius:5px;padding:12px 16px;margin-bottom:20px;font-family:var(--font-ui);font-size:13px;color:var(--text-dim);line-height:1.5">
  <strong style="color:var(--accent)">Draft in progress.</strong>
  This is a working draft under active revision. Chapters may change between visits.
</div>
<div class="hero">
  <h1>Gearpunk</h1>
  <p>A worldbuilding project. A hard sci-fi novella in ten chapters.<br>
  A civilization built on motion, biology, and mechanical humility.</p>
</div>
<span class="sec-label">World</span>
<div class="card-grid">{cards_world}</div>
<span class="sec-label">The Winding Shift</span>
<div class="card-grid">{cards_ch}</div>
<span class="sec-label">Reference</span>
<div class="card-grid">{cards_ref}</div>"""
    return page_tmpl("Home", "Gearpunk", "style.css", "", "index.html", body)


def gen_doc(src_path, title, breadcrumb, cur_page, with_toc=True):
    src = src_path.read_text(encoding="utf-8")
    body, headings = md_to_html(src)
    if with_toc:
        body = build_toc(headings) + body
    return page_tmpl(title, breadcrumb, "style.css", "", cur_page, body)


def gen_chapter(slug, title, num):
    src_path = GEARPUNK / "the-winding-shift" / "chapters" / f"{slug}.md"
    src = src_path.read_text(encoding="utf-8")
    body, _ = md_to_html(src)

    # Chapter metadata footer
    mtime = get_file_mtime(src_path)
    wc = get_word_count(src_path)
    meta_parts = []
    if mtime:
        meta_parts.append(f"Last revised: {mtime}")
    if wc:
        meta_parts.append(f"{wc} words")
    meta_html = ""
    if meta_parts:
        meta_html = (
            '<div class="ch-meta">'
            + " &middot; ".join(meta_parts)
            + '</div>'
        )

    idx = num - 1
    prev_html = ""
    if idx > 0:
        ps, pt, pn = CHAPTERS[idx - 1]
        prev_html = (
            f'<a href="{ps}.html">'
            f'<small>&#8592; Previous</small>Ch {pn}: {pt}</a>'
        )
    next_html = ""
    if idx < len(CHAPTERS) - 1:
        ns, nt, nn = CHAPTERS[idx + 1]
        next_html = (
            f'<a href="{ns}.html" class="nxt">'
            f'<small>Next &#8594;</small>Ch {nn}: {nt}</a>'
        )
    ch_nav = f'{meta_html}<nav class="ch-nav">{prev_html}{next_html}</nav>'

    return page_tmpl(
        f"Ch {num}: {title}",
        f"Chapter {num}",
        "../style.css",
        "../",
        f"chapters/{slug}.html",
        body,
        ch_nav,
    )


def gen_changelog():
    entries = []
    for date_str, items in CHANGELOG:
        li = "".join(f"<li>{html_lib.escape(item)}</li>" for item in items)
        entries.append(
            f'<div class="changelog-entry">'
            f'<div class="changelog-date">{date_str}</div>'
            f'<ul>{li}</ul></div>'
        )

    # Word count summary
    total = 0
    rows = []
    for slug, title, num in CHAPTERS:
        p = GEARPUNK / "the-winding-shift" / "chapters" / f"{slug}.md"
        wc = len(p.read_text(encoding="utf-8").split()) if p.exists() else 0
        total += wc
        rows.append(f"<tr><td>Ch {num}: {title}</td><td>{wc:,}</td></tr>")
    rows.append(f'<tr style="border-top:1px solid var(--border);font-weight:600">'
                f'<td>Total</td><td>{total:,}</td></tr>')

    body = f"""\
<h1>Changelog</h1>
<p style="color:var(--text-dim);font-size:.9em;margin-bottom:2em">
What changed and when. This project is a working draft; revisions happen in public.</p>
{"".join(entries)}
<h2 id="word-counts">Current Word Counts</h2>
<table style="width:100%;font-family:var(--font-ui);font-size:13px;border-collapse:collapse">
{"".join(rows)}
</table>
<style>
table td {{ padding: 6px 0; color: var(--text-dim); }}
table td:last-child {{ text-align: right; font-variant-numeric: tabular-nums; }}
</style>"""

    return page_tmpl("Changelog", "Changelog", "style.css", "", "changelog.html", body)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "chapters").mkdir(exist_ok=True)

    def w(path, content, label):
        path.write_text(content, encoding="utf-8")
        print(f"ok {label}")

    w(OUT / "style.css", CSS, "style.css")
    w(OUT / "index.html", gen_index(), "index.html")
    w(OUT / "bible.html",
      gen_doc(GEARPUNK / "gearpunk-bible.md", "Gearpunk Bible", "Bible", "bible.html"),
      "bible.html")
    w(OUT / "demiurge.html",
      gen_doc(GEARPUNK / "demiurge.md", "The Demiurge Protocol", "Demiurge", "demiurge.html"),
      "demiurge.html")
    w(OUT / "voice.html",
      gen_doc(GEARPUNK / "the-winding-shift" / "VOICE.md", "Voice & Style Guide", "Voice", "voice.html"),
      "voice.html")
    w(OUT / "changelog.html", gen_changelog(), "changelog.html")

    for slug, title, num in CHAPTERS:
        w(OUT / "chapters" / f"{slug}.html", gen_chapter(slug, title, num), f"chapters/{slug}.html")

    print(f"\nDone: {6 + len(CHAPTERS)} files -> {OUT}")


if __name__ == "__main__":
    main()
