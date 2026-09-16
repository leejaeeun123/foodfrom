#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
FOODFROM 디자인 시스템 사이트 빌드

docs/*.md 를 읽어 dist/ 에 정적 HTML 을 생성한다.
마크다운이 원본이고 HTML 은 결과물이다. dist/ 를 직접 고치지 말 것.

    python build.py

의존성: markdown-it-py  (python -m pip install markdown-it-py)
"""

import html
import re
import shutil
import zipfile
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).parent
DOCS = ROOT / "docs"
SRC = ROOT / "src"
ASSETS = ROOT / "assets"
DIST = ROOT / "dist"

# 탭 순서 = 사이트 내비게이션 순서
PAGES = [
    # (md 파일,      출력 파일,      탭 이름,   글립,  한 줄 설명)
    ("Brand.md",   "index.html",   "BRAND",   "眼", "어떻게 생겼는가"),
    ("BX.md",      "bx.html",      "BX",      "言", "뭐라고 말하는가"),
    ("Product.md", "product.html", "PRODUCT", "物", "무엇을 파는가"),
    ("UX.md",      "ux.html",      "UX",      "手", "어떻게 사는가"),
]

SITE_TITLE = "FOODFROM"
SITE_SUB = "Design System — 꾸미지 않은 제대로 고른 맛"


# ---------------------------------------------------------------- 커스텀 펜스

def fence_swatch(body):
    """컬러 스와치. `이름 | HEX | 토큰 | 설명` 한 줄에 하나."""
    cells = []
    for line in body.strip().splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        name = parts[0] if len(parts) > 0 else ""
        hexv = parts[1] if len(parts) > 1 else "#000000"
        token = parts[2] if len(parts) > 2 else ""
        desc = parts[3] if len(parts) > 3 else ""
        border = ";border-bottom:1px solid var(--line)" if hexv.upper() in ("#FFFFFF", "#FFFBEB") else ""
        cells.append(
            '<div class="sw">'
            f'<div class="chipcolor" style="background:{html.escape(hexv)}{border}"></div>'
            '<div class="meta">'
            f'<div class="nm">{html.escape(name)}</div>'
            f'<div class="hex">{html.escape(hexv)}</div>'
            f'<div class="tok">{html.escape(token)}{" · " + html.escape(desc) if desc else ""}</div>'
            "</div></div>"
        )
    return '<div class="swatches">' + "".join(cells) + "</div>"


def fence_dodont(body):
    """Do / Don't 2열. `DO 내용` 또는 `DONT 내용`."""
    do, dont = [], []
    for line in body.strip().splitlines():
        s = line.strip()
        if not s:
            continue
        if s.upper().startswith("DONT"):
            dont.append(s[4:].strip())
        elif s.upper().startswith("DO"):
            do.append(s[2:].strip())
    def ul(items):
        return "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"
    return (
        '<div class="dd">'
        f'<div class="do"><h5>Do</h5>{ul(do)}</div>'
        f'<div class="dont"><h5>Don\'t</h5>{ul(dont)}</div>'
        "</div>"
    )


def fence_compare(body):
    """기존 / 개정 2열. 첫 줄이 `기존 | 개정` 헤더, 이후 `왼쪽 | 오른쪽`."""
    lines = [l for l in body.strip().splitlines() if l.strip()]
    if not lines:
        return ""
    head = [p.strip() for p in lines[0].split("|")]
    left_h = head[0] if head else "기존"
    right_h = head[1] if len(head) > 1 else "개정"
    left, right = [], []
    for line in lines[1:]:
        parts = [p.strip() for p in line.split("|")]
        if parts and parts[0]:
            left.append(parts[0])
        if len(parts) > 1 and parts[1]:
            right.append(parts[1])
    def ul(items):
        return "<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>"
    return (
        '<div class="compare">'
        f'<div class="old"><h5>{html.escape(left_h)}</h5>{ul(left)}</div>'
        f'<div class="new"><h5>{html.escape(right_h)}</h5>{ul(right)}</div>'
        "</div>"
    )


def fence_gallery(body):
    """이미지 그리드. `경로 | 캡션` 한 줄에 하나. 첫 줄이 `cols: 2` 면 열 수 지정."""
    lines = [l for l in body.strip().splitlines() if l.strip()]
    cls = "three"
    if lines and lines[0].lower().startswith("cols:"):
        n = lines[0].split(":", 1)[1].strip()
        cls = {"1": "wide", "2": "two", "3": "three"}.get(n, "three")
        lines = lines[1:]
    figs = []
    for line in lines:
        parts = [p.strip() for p in line.split("|")]
        src = parts[0]
        cap = parts[1] if len(parts) > 1 else ""
        figs.append(
            f'<figure><img src="{html.escape(src)}" alt="{html.escape(cap)}" loading="lazy">'
            + (f"<figcaption>{inline(cap)}</figcaption>" if cap else "")
            + "</figure>"
        )
    return f'<div class="gal {cls}">' + "".join(figs) + "</div>"


def fence_spec(body):
    """인라인 스펙 칩. `라벨 | 값` 한 줄에 하나."""
    chips = []
    for line in body.strip().splitlines():
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split("|")]
        label = parts[0]
        value = parts[1] if len(parts) > 1 else ""
        chips.append(f"<b>{html.escape(label)} <em>{html.escape(value)}</em></b>")
    return '<div class="spec">' + "".join(chips) + "</div>"


def fence_todo(body):
    """결정 대기 체크리스트."""
    items = "".join(
        f"<li>{inline(l.strip())}</li>" for l in body.strip().splitlines() if l.strip()
    )
    return f'<ul class="todo">{items}</ul>'


def fence_postmark(body):
    """원형 소인 배지. 세 줄: 윗 링 텍스트 / 중앙 / 아랫 링 텍스트."""
    lines = [l.strip() for l in body.strip().splitlines() if l.strip()]
    top = lines[0] if len(lines) > 0 else ""
    mid = lines[1] if len(lines) > 1 else ""
    bot = lines[2] if len(lines) > 2 else ""
    return (
        '<div class="postmark">'
        f'<span class="t">{html.escape(top)}</span>'
        f'<span class="m">{html.escape(mid)}</span>'
        f'<span class="t">{html.escape(bot)}</span>'
        "</div>"
    )


def fence_letter(body):
    """편지 블록. 마지막 `From.` 줄은 서명으로 크게."""
    lines = body.strip().split("\n")
    sig = ""
    if lines and lines[-1].strip().startswith("From."):
        sig = lines[-1].strip()
        lines = lines[:-1]
    paras = []
    for block in "\n".join(lines).split("\n\n"):
        block = block.strip()
        if block:
            paras.append("<p>" + "<br>".join(inline(l) for l in block.split("\n")) + "</p>")
    out = "".join(paras)
    if sig:
        out += f'<span class="from">{html.escape(sig)}</span>'
    return f"<blockquote>{out}</blockquote>"


FENCES = {
    "swatch": fence_swatch,
    "dodont": fence_dodont,
    "compare": fence_compare,
    "gallery": fence_gallery,
    "spec": fence_spec,
    "todo": fence_todo,
    "postmark": fence_postmark,
    "letter": fence_letter,
}


# ---------------------------------------------------------------- 마크다운

md = MarkdownIt("commonmark", {"html": True, "typographer": False}).enable("table")


def inline(text):
    """한 줄짜리 인라인 마크다운(굵게, 코드, 링크)만 렌더."""
    return md.renderInline(text)


def _fence_renderer(self, tokens, idx, options, env):
    token = tokens[idx]
    info = (token.info or "").strip().lower()
    if info in FENCES:
        return FENCES[info](token.content) + "\n"
    # 일반 코드 블록
    return (
        "<pre><code>" + html.escape(token.content) + "</code></pre>\n"
    )


md.add_render_rule("fence", _fence_renderer)


def render_body(text):
    out = md.render(text)
    # 표는 가로 스크롤 컨테이너로 감싼다
    out = out.replace("<table>", '<div class="tblwrap"><table>').replace(
        "</table>", "</table></div>"
    )
    # `## 01 · Logo` → 섹션 번호를 분리해 세리프로
    def h2(m):
        num, rest = m.group(1), m.group(2)
        return f'<h2><span class="num">{num}</span>{rest}</h2>'
    out = re.sub(r"<h2>(\d{2})\s*·\s*(.+?)</h2>", h2, out)
    # `[상태: 확정]` 인라인 배지
    def badge(m):
        label = m.group(1).strip()
        cls = "ok" if label in ("확정", "있음") else ("wip" if label in ("미정", "미작성", "재작업") else "")
        return f'<span class="badge {cls}">{html.escape(label)}</span>'
    out = re.sub(r"\[상태:\s*([^\]]+)\]", badge, out)
    return out


# ---------------------------------------------------------------- 문서 파싱

FRONT_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.S)


def parse_doc(path):
    raw = path.read_text(encoding="utf-8")
    meta = {}
    m = FRONT_RE.match(raw)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        raw = raw[m.end():]

    # 첫 H1 = 문서 제목
    title = ""
    tm = re.match(r"#\s+(.+?)\n", raw)
    if tm:
        title = tm.group(1).strip()
        raw = raw[tm.end():]

    # H1 바로 뒤 인용구 = 리드 문장
    lead = ""
    lm = re.match(r"\s*>\s*(.+?)\n(?:\n|$)", raw)
    if lm:
        lead = lm.group(1).strip()
        raw = raw[lm.end():]

    return meta, title, lead, raw


def collect_sections(body_md):
    """`## 01 · Logo` 형태의 H2 를 목차용으로 뽑는다."""
    out = []
    for m in re.finditer(r"^##\s+(.+?)\s*$", body_md, re.M):
        heading = m.group(1).strip()
        nm = re.match(r"(\d{2})\s*·\s*(.+)", heading)
        if nm:
            out.append((nm.group(1), nm.group(2)))
        else:
            out.append(("", heading))
    return out


# ---------------------------------------------------------------- 템플릿

def build_tabs(current_out):
    links = []
    for _, out, name, glyph, _ in PAGES:
        cur = ' aria-current="page"' if out == current_out else ""
        links.append(
            f'<a href="{out}"{cur}><span class="gl">{glyph}</span>{name}</a>'
        )
    return "".join(links)


def build_toc(sections):
    if not sections:
        return ""
    items = []
    for num, name in sections:
        anchor = slug(f"{num}-{name}")
        n = f'<span class="n">{num}</span>' if num else ""
        items.append(f'<li><a href="#{anchor}">{n} {html.escape(name)}</a></li>')
    return (
        '<nav class="toc"><div class="wrap"><ol>' + "".join(items) + "</ol></div></nav>"
    )


def slug(text):
    s = re.sub(r"[^\w가-힣\s·-]", "", text).strip().lower()
    s = re.sub(r"[\s·]+", "-", s)
    return s or "section"


def anchor_h2(body_html, sections):
    """렌더된 H2 에 목차와 같은 id 를 붙인다."""
    it = iter(sections)

    def repl(m):
        try:
            num, name = next(it)
        except StopIteration:
            return m.group(0)
        return f'<h2 id="{slug(f"{num}-{name}")}"' + m.group(1)

    return re.sub(r"<h2(>|\s)", lambda m: repl(m), body_html, count=len(sections)) \
        if sections else body_html


TEMPLATE = """<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{title} — FOODFROM Design System</title>
<meta name="description" content="{desc}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&family=Instrument+Serif:ital@0;1&display=swap" rel="stylesheet">
<link rel="stylesheet" href="style.css">
</head>
<body>

<header>
  <div class="wrap">
    <h1 class="brandline">FOODFROM<em>.</em></h1>
    <p class="sub">{sitesub}</p>
  </div>
</header>

<nav class="tabs"><div class="wrap">{tabs}</div></nav>

<div class="wrap">
  <div class="dlbar">
    <a class="dl" href="docs/{mdfile}" download>↓ {mdfile}</a>
    <a class="dl ghost" href="foodfrom-docs.zip" download>↓ 문서 전체 zip</a>
    <span class="dlnote">{glyph} {tagline}</span>
  </div>
</div>

<main>
<section><div class="wrap">
  <div class="sechead"><h2 style="font-size:32px">{title}</h2></div>
  {leadhtml}
</div></section>

{toc}

<section><div class="wrap">
{body}
</div></section>
</main>

<footer><div class="wrap">
  <div class="sig">From. 푸드프롬</div>
  <p>이 페이지는 <code>docs/{mdfile}</code> 에서 자동 생성됩니다. HTML 을 직접 고치지 마세요.</p>
  <p>{version}</p>
</div></footer>

</body>
</html>
"""


# ---------------------------------------------------------------- 빌드

def build():
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    # 정적 파일
    shutil.copy(SRC / "style.css", DIST / "style.css")
    if ASSETS.exists():
        shutil.copytree(ASSETS, DIST / "assets")

    # 다운로드용 MD 원본
    (DIST / "docs").mkdir()
    for mdfile, *_ in PAGES:
        src = DOCS / mdfile
        if src.exists():
            shutil.copy(src, DIST / "docs" / mdfile)

    # 문서 묶음 zip
    with zipfile.ZipFile(DIST / "foodfrom-docs.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for mdfile, *_ in PAGES:
            src = DOCS / mdfile
            if src.exists():
                z.write(src, mdfile)

    built = []
    for mdfile, outfile, name, glyph, tagline in PAGES:
        path = DOCS / mdfile
        if not path.exists():
            print(f"  건너뜀 — {mdfile} 없음")
            continue

        meta, title, lead, body_md = parse_doc(path)
        sections = collect_sections(body_md)
        body_html = anchor_h2(render_body(body_md), sections)

        page = TEMPLATE.format(
            title=html.escape(title or name),
            desc=html.escape(meta.get("description", lead)),
            sitesub=html.escape(SITE_SUB),
            tabs=build_tabs(outfile),
            toc=build_toc(sections),
            body=body_html,
            leadhtml=f'<p class="seclede" style="margin-left:0">{inline(lead)}</p>' if lead else "",
            mdfile=mdfile,
            glyph=glyph,
            tagline=html.escape(tagline),
            version=html.escape(meta.get("version", "")),
        )
        (DIST / outfile).write_text(page, encoding="utf-8")
        built.append(f"  {outfile:<14} ← {mdfile:<12} ({len(sections)}개 섹션)")

    print("빌드 완료 → dist/")
    print("\n".join(built))


if __name__ == "__main__":
    build()
