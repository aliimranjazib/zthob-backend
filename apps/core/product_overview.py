"""Load and render client product overview markdown chapters."""

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import markdown
from django.conf import settings

CLIENT_CHAPTERS_DIR = (
    Path(settings.BASE_DIR) / 'docs' / 'product-requirements' / 'client' / 'chapters'
)
CLIENT_PDF_PATH = (
    Path(settings.BASE_DIR) / 'docs' / 'product-requirements' / 'export' / 'Mgask-Product-Overview.pdf'
)

DOCUMENT_TITLE = 'Mgask Product Overview'
DOCUMENT_DESCRIPTION = (
    'A clear guide to the Mgask tailoring platform — who uses it, what each app does, '
    'and how orders flow from customer to delivery.'
)
DOCUMENT_VERSION = '1.0'


@dataclass(frozen=True)
class Chapter:
    number: int
    slug: str
    filename: str
    title: str
    anchor: str
    markdown_source: str
    html_content: str
    headings: list[dict]


@dataclass(frozen=True)
class ProductOverviewDocument:
    title: str
    description: str
    version: str
    last_updated: datetime
    chapters: list[Chapter]

    @property
    def toc(self) -> list[dict]:
        return [
            {
                'number': ch.number,
                'title': ch.title,
                'anchor': ch.anchor,
                'headings': ch.headings,
            }
            for ch in self.chapters
        ]


def _slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'^chapter\s+\d+\s*[—\-]\s*', '', text)
    text = re.sub(r'[^a-z0-9]+', '-', text)
    return text.strip('-') or 'chapter'


def _extract_chapter_title(markdown_source: str, fallback: str) -> str:
    for line in markdown_source.splitlines():
        stripped = line.strip()
        if stripped.startswith('# '):
            return stripped.lstrip('# ').strip()
    return fallback


def _preprocess_mermaid(source: str) -> str:
    """Convert fenced mermaid blocks to HTML divs for browser/PDF rendering."""

    def replace_block(match: re.Match) -> str:
        diagram = match.group(1).strip()
        return f'\n<div class="mermaid">\n{diagram}\n</div>\n'

    return re.sub(r'```mermaid\n([\s\S]*?)```', replace_block, source)


def _render_markdown(source: str) -> str:
    processed = _preprocess_mermaid(source)
    return markdown.markdown(
        processed,
        extensions=['tables', 'fenced_code', 'nl2br', 'sane_lists'],
        output_format='html5',
    )


def _extract_headings(html: str) -> list[dict]:
    headings = []
    for match in re.finditer(r'<h([2-3]) id="([^"]+)">([^<]+)</h\1>', html):
        headings.append({
            'level': int(match.group(1)),
            'anchor': match.group(2),
            'title': match.group(3).strip(),
        })
    return headings


def _add_heading_ids(html: str, chapter_anchor: str) -> str:
    """Add stable IDs to h2/h3 for in-page TOC links."""

    counters: dict[int, int] = {2: 0, 3: 0}

    def replacer(match: re.Match) -> str:
        level = int(match.group(1))
        title = match.group(2).strip()
        counters[level] += 1
        if level == 2:
            counters[3] = 0
        slug = _slugify(title)
        anchor = f'{chapter_anchor}--{slug}' if slug else f'{chapter_anchor}--h{level}-{counters[level]}'
        return f'<h{level} id="{anchor}">{title}</h{level}>'

    return re.sub(r'<h([23])>([^<]+)</h[23]>', replacer, html)


def _chapter_files() -> list[Path]:
    if not CLIENT_CHAPTERS_DIR.is_dir():
        return []
    return sorted(CLIENT_CHAPTERS_DIR.glob('[0-9][0-9]-*.md'))


def _last_updated(files: list[Path]) -> datetime:
    if not files:
        return datetime.now(timezone.utc)
    latest = max(f.stat().st_mtime for f in files)
    return datetime.fromtimestamp(latest, tz=timezone.utc)


def load_product_overview() -> ProductOverviewDocument:
    files = _chapter_files()
    chapters: list[Chapter] = []

    for index, path in enumerate(files, start=1):
        source = path.read_text(encoding='utf-8')
        fallback_title = path.stem.replace('-', ' ').title()
        title = _extract_chapter_title(source, fallback_title)
        anchor = f'chapter-{index:02d}-{_slugify(title)}'
        html = _render_markdown(source)
        html = _add_heading_ids(html, anchor)
        headings = _extract_headings(html)

        chapters.append(Chapter(
            number=index,
            slug=_slugify(title),
            filename=path.name,
            title=title,
            anchor=anchor,
            markdown_source=source,
            html_content=html,
            headings=headings,
        ))

    return ProductOverviewDocument(
        title=DOCUMENT_TITLE,
        description=DOCUMENT_DESCRIPTION,
        version=DOCUMENT_VERSION,
        last_updated=_last_updated(files),
        chapters=chapters,
    )


def get_client_pdf_path() -> Path:
    return CLIENT_PDF_PATH
