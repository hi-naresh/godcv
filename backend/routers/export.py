"""ATS-friendly PDF export.

The frontend sends pre-rendered HTML (the same markup the on-screen preview
displays) plus the user's font/spacing settings. This route post-processes the
HTML to insert dot-leader spans between role titles and dates — so the PDF text
stream reads as a single continuous line per role rather than two columns —
then renders to a tagged PDF/UA-1 PDF via WeasyPrint when supported.

Dot count per line is computed from real glyph widths via Pillow against the
actual font WeasyPrint will use, so the date sits flush with the right margin
regardless of font size or content length. The frontend mirrors the same
calculation (see useMarkdown.ts) using canvas measureText so the preview
matches the exported PDF byte-for-byte at the role-line level.
"""
import io
import os
import re
from functools import lru_cache

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from PIL import ImageFont

from backend.db.models import ExportRequest

router = APIRouter(prefix="/api/export", tags=["export"])


# Match a <p> whose first content is <strong>...</strong> (whitespace) <em>...</em>.
# `[^<]+` is sufficient because role/date text never contains nested HTML in
# the marked.js output for this resume schema.
_ROLE_LINE_HEAD_RE = re.compile(
    r"<p>\s*(<strong>[^<]+</strong>)\s+(<em>[^<]+</em>)"
)

# Split paragraphs where role line is followed by <br> + stack/coursework line.
_ROLE_WITH_TRAILING_RE = re.compile(
    r"(<p>\s*<strong>[^<]+</strong>\s+<em>[^<]+</em>)<br\s*/?>\s*(.*?</p>)",
    re.DOTALL,
)


def _split_role_paragraphs(html: str) -> str:
    """Split <p>role + <br/> + stack</p> into two adjacent <p>s."""
    return _ROLE_WITH_TRAILING_RE.sub(r"\1</p><p>\2", html)


# Page geometry. Single-page margin matches the frontend's --page-margin (6mm
# in style.css) so the auto-fitted font size from the on-screen preview
# transfers cleanly into the backend layout.
_A4_WIDTH_PT = 595.276
_MM_TO_PT = 2.83465
_PAGE_MARGIN_MM = {"single": 6.0, "multi": 14.0}
# CSS px → PDF pt conversion. CSS spec defines 1px = 1/96in; PDF uses 1pt = 1/72in.
_PX_TO_PT = 0.75


# Font search paths. We need both regular and bold weights for accurate
# title/date measurement. The order matches WeasyPrint's font resolution
# preference: Georgia → Times New Roman → Liberation Serif → DejaVu Serif.
_FONT_CANDIDATES = {
    "serif_bold": [
        "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
        "/Library/Fonts/Georgia Bold.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    ],
    "serif_regular": [
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
        "/Library/Fonts/Georgia.ttf",
        "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    ],
}


@lru_cache(maxsize=2)
def _font_path(kind: str) -> str | None:
    for p in _FONT_CANDIDATES[kind]:
        if os.path.isfile(p):
            return p
    return None


@lru_cache(maxsize=64)
def _font_at(kind: str, size_pt_x100: int) -> ImageFont.FreeTypeFont | None:
    """Cache one ImageFont per (kind, size). size is x100 to make int-keyed."""
    path = _font_path(kind)
    if path is None:
        return None
    return ImageFont.truetype(path, size=size_pt_x100 / 100.0)


def _measure_pt(text: str, kind: str, size_pt: float, letter_spacing_pt: float = 0.0) -> float:
    """Measure rendered text width in PDF points, with optional letter spacing.

    Uses font.getlength() (sub-pixel precision) rather than getbbox() (integer
    bounding box) — at small font sizes getbbox rounds dot-width up by 0.5pt
    which compounds across many dots into noticeable misalignment.
    """
    font = _font_at(kind, round(size_pt * 100))
    if font is None:
        # No font file found — fall back to empirical formula.
        approx_em = 0.55 if "bold" in kind else 0.50
        width_pt = len(text) * approx_em * size_pt
    else:
        width_pt = float(font.getlength(text))
    if letter_spacing_pt > 0 and len(text) > 1:
        width_pt += (len(text) - 1) * letter_spacing_pt
    return width_pt


def _inject_dot_leaders(html: str, font_size_px: float, page_mode: str) -> str:
    """Insert a precisely-calibrated dot-leader between strong and em on role lines.

    All measurements come from Pillow against the actual Georgia font file at
    the same point size WeasyPrint will use, so the date lands flush with the
    right margin (within sub-pt precision) regardless of font_size, page_mode,
    or content length. Marked aria-hidden so tag-aware ATS parsers skip the
    decorative dots.
    """
    font_size_pt = font_size_px * _PX_TO_PT
    margin_pt = _PAGE_MARGIN_MM[page_mode] * _MM_TO_PT
    content_width_pt = _A4_WIDTH_PT - 2 * margin_pt

    # Dot-leader CSS: font-size: 0.9em, letter-spacing: 0.15em (relative to its
    # own font-size, per CSS spec).
    dot_size_pt = font_size_pt * 0.9
    dot_ls_pt = dot_size_pt * 0.15
    single_dot_width_pt = _measure_pt("·", "serif_regular", dot_size_pt, 0) + dot_ls_pt

    # Two literal whitespace chars between strong/dot-leader/em add ~0.5em each.
    space_pad_pt = _measure_pt(" ", "serif_regular", font_size_pt) * 2
    # Tiny safety so the date doesn't kiss the right edge.
    safety_pt = font_size_pt * 0.12

    pattern = re.compile(
        r"<p>\s*<strong>([^<]+)</strong>\s+<em>([^<]+)</em>\s*</p>"
    )

    def _replace(m: "re.Match[str]") -> str:
        title = m.group(1)
        date = m.group(2)
        title_pt = _measure_pt(title, "serif_bold", font_size_pt)
        date_pt = _measure_pt(date, "serif_bold", font_size_pt)
        gap_pt = content_width_pt - title_pt - date_pt - space_pad_pt - safety_pt
        dot_count = max(6, int(gap_pt / single_dot_width_pt))
        dots = "·" * dot_count
        return (
            f'<p class="role-line">'
            f"<strong>{title}</strong>"
            f' <span class="dot-leader" aria-hidden="true">{dots}</span> '
            f"<em>{date}</em></p>"
        )

    return pattern.sub(_replace, html)


def _build_css(font_size: float, line_spacing: float, page_mode: str) -> str:
    """Print CSS that mirrors the on-screen preview but with inline dot-leader dates.

    Dots are #e8e8e8 — visible enough to escape "hidden text" anti-fraud heuristics
    (which look for text matching the page background), invisible enough at small
    font sizes to read as clean whitespace.
    """
    page_margin = "6mm" if page_mode == "single" else "14mm"
    return f"""
    @page {{ size: A4; margin: {page_margin}; }}
    html {{ font-family: Georgia, "Times New Roman", serif; }}
    body {{
      font-size: {font_size}px; line-height: {line_spacing};
      color: #111; margin: 0; padding: 0;
    }}
    h1 {{ font-size: 1.15rem; font-weight: 800; margin: .5rem 0 .3rem; }}
    h2 {{ font-size: 1.05rem; font-weight: 800; margin: .5rem 0 .3rem; }}
    h3 {{ font-size: .95rem; font-weight: 700; margin: .5rem 0 .3rem; }}
    p {{ margin: .2rem 0; }}
    ul, ol {{ margin: .2rem 0 .2rem 1.1rem; }}
    li {{ margin: .1rem 0; }}
    strong {{ font-weight: 700; }}
    a {{ color: #0066cc; text-decoration: underline; }}
    hr {{ border: 0; border-top: 1px solid #bbb; margin: .3rem 0; }}

    .cv-head {{ margin-bottom: .3rem; }}
    .name {{ font-size: 2.0rem; font-weight: 800; line-height: 1.05; }}
    .role {{ font-weight: 600; margin: .15rem 0; }}
    .meta {{ color: #666; font-size: .95em; }}
    .meta a {{ color: #0066cc; }}

    /* Role/date line: pure inline layout. Dot-leader length is calibrated
       per-line server-side (see _inject_dot_leaders) so the line ends near the
       right margin. No flex/table/absolute positioning — those don't behave
       predictably in WeasyPrint for this pattern. The dots are real text in
       the PDF stream so ATS extractors see one continuous run per role. */
    p.role-line {{
      margin: .25rem 0 .15rem;
    }}
    p.role-line > em {{
      font-style: normal;
      font-weight: 700;
      white-space: nowrap;
    }}
    p.role-line > .dot-leader {{
      color: #e8e8e8;
      letter-spacing: .15em;
      font-weight: 400;
      font-size: .9em;
    }}
    """


def _wrap_html(body_html: str, css: str, lang: str, title: str | None) -> str:
    title_tag = f"<title>{title}</title>" if title else "<title>Resume</title>"
    return (
        f'<!doctype html><html lang="{lang}"><head>'
        f'<meta charset="utf-8">{title_tag}'
        f"<style>{css}</style></head><body>{body_html}</body></html>"
    )


_MIN_FONT_SIZE = 7.5
_FONT_SHRINK_STEP = 0.4
_FONT_SHRINK_MAX_ATTEMPTS = 16


def _render_pdf_bytes(html_str: str) -> tuple[bytes, int]:
    """Render HTML to PDF and return (pdf_bytes, page_count). PDF/UA when supported."""
    from weasyprint import HTML

    doc = HTML(string=html_str).render()
    page_count = len(doc.pages)
    try:
        pdf_bytes = doc.write_pdf(pdf_variant="pdf/ua-1")
    except (TypeError, ValueError):
        pdf_bytes = doc.write_pdf()
    return pdf_bytes, page_count


def _render_single_page(
    body_html: str,
    line_spacing: float,
    initial_font_size: float,
    document_lang: str,
    document_title: str | None,
) -> tuple[bytes, float, int]:
    """Iteratively shrink font size until content fits on one A4 page.

    Returns (pdf_bytes, final_font_size, attempts). The frontend already
    auto-fits against its own layout, but the backend's CSS box differs
    slightly (different fonts on the page, dot-leader spans add a sliver
    of width). This loop is the safety net for those edge cases.
    """
    font_size = initial_font_size
    pdf_bytes = b""
    last_doc_html = ""
    for attempt in range(1, _FONT_SHRINK_MAX_ATTEMPTS + 1):
        body_with_dots = _inject_dot_leaders(body_html, font_size, "single")
        css = _build_css(font_size, line_spacing, "single")
        full_html = _wrap_html(body_with_dots, css, document_lang, document_title)
        last_doc_html = full_html
        pdf_bytes, page_count = _render_pdf_bytes(full_html)
        if page_count <= 1:
            return pdf_bytes, font_size, attempt
        if font_size - _FONT_SHRINK_STEP < _MIN_FONT_SIZE:
            break
        font_size = round(font_size - _FONT_SHRINK_STEP, 2)
    # Couldn't fit even at minimum font; return the last (smallest) render.
    pdf_bytes, _ = _render_pdf_bytes(last_doc_html)
    return pdf_bytes, font_size, _FONT_SHRINK_MAX_ATTEMPTS


@router.post("/pdf")
async def export_pdf(request: ExportRequest):
    try:
        import weasyprint  # noqa: F401  (also raises ImportError if libs missing)
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail=(
                "WeasyPrint not installed. Install with `pip install weasyprint` "
                "(macOS also needs `brew install pango`). Falling back to browser print."
            ),
        )

    body = _split_role_paragraphs(request.html)

    if request.page_mode == "single":
        pdf_bytes, final_size, attempts = _render_single_page(
            body, request.line_spacing, request.font_size,
            request.document_lang, request.document_title,
        )
        if attempts > 1:
            import logging
            logging.getLogger("godcv.export").info(
                "single-page auto-shrink: %.2fpx → %.2fpx (%d attempts)",
                request.font_size, final_size, attempts,
            )
    else:
        body = _inject_dot_leaders(body, request.font_size, request.page_mode)
        css = _build_css(request.font_size, request.line_spacing, request.page_mode)
        full_html = _wrap_html(body, css, request.document_lang, request.document_title)
        pdf_bytes, _ = _render_pdf_bytes(full_html)

    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", request.filename) or "resume.pdf"
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
