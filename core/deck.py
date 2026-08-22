"""
PowerPoint generation against a company-supplied template.

The point of this module is that generated slide content lands inside the client's
own brand template — their theme, fonts, colours and slide masters — so the deck is
field-ready rather than something a medical writer has to re-style by hand.

python-pptx opens a .pptx or .potx and keeps its theme and slide layouts intact.
We clear any example slides the template ships with, then add our content using
the template's own layouts. Nothing about the brand is reimplemented here; it is
inherited.
"""

from __future__ import annotations

import io
import os
import re
from typing import Any

TEMPLATE_EXTENSIONS = {".pptx", ".potx"}


def is_template(filename: str) -> bool:
    return os.path.splitext(filename)[1].lower() in TEMPLATE_EXTENSIONS


def _require_pptx():
    try:
        from pptx import Presentation  # noqa: F401
        from pptx.util import Pt  # noqa: F401
        return True
    except ImportError:
        return False


def inspect_template(path: str) -> dict[str, Any]:
    """
    Read a template's layouts and dimensions so the UI can show what was uploaded.

    Never raises — a corrupt or unreadable file returns an `error` string instead,
    which the upload list renders next to the file.
    """
    if not _require_pptx():
        return {"error": "PPTX support needs python-pptx — run: pip install -r requirements.txt"}

    try:
        from pptx import Presentation

        presentation = Presentation(path)
        layouts = [layout.name for layout in presentation.slide_layouts]
        width = presentation.slide_width
        height = presentation.slide_height
        ratio = "16:9" if width and height and abs(width / height - 16 / 9) < 0.05 else "4:3"

        theme_fonts = _theme_fonts(presentation)

        return {
            "error": None,
            "layouts": layouts,
            "layout_count": len(layouts),
            "aspect_ratio": ratio,
            "slide_count": len(presentation.slides),
            "major_font": theme_fonts.get("major", ""),
            "minor_font": theme_fonts.get("minor", ""),
        }
    except Exception as exc:
        return {"error": f"Could not read template: {type(exc).__name__}"}


def _theme_fonts(presentation) -> dict[str, str]:
    """Pull the theme's heading/body typefaces so the UI can name the brand fonts."""
    try:
        part = presentation.slide_master.part.part_related_by(
            "http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme"
        )
        xml = part.blob.decode("utf-8", "replace")
        major = re.search(r"<a:majorFont>\s*<a:latin typeface=\"([^\"]*)\"", xml)
        minor = re.search(r"<a:minorFont>\s*<a:latin typeface=\"([^\"]*)\"", xml)
        return {
            "major": major.group(1) if major else "",
            "minor": minor.group(1) if minor else "",
        }
    except Exception:
        return {}


# --------------------------------------------------------------------------
# Layout selection
# --------------------------------------------------------------------------

_TITLE_HINTS = ("title slide", "title", "cover", "portada")
_CONTENT_HINTS = ("title and content", "content", "bullet", "text", "contenido")


def _placeholder_types(layout) -> set[int]:
    types = set()
    for placeholder in layout.placeholders:
        try:
            types.add(int(placeholder.placeholder_format.type))
        except (TypeError, ValueError):
            continue
    return types


def _pick_layouts(presentation) -> tuple[Any, Any]:
    """
    Choose a title layout and a title+body layout from whatever the template offers.

    Custom corporate templates use arbitrary layout names, so we match on name hints
    first and fall back to placeholder structure, then to index.
    """
    layouts = list(presentation.slide_layouts)
    if not layouts:
        raise ValueError("Template contains no slide layouts")

    title_layout = None
    content_layout = None

    for layout in layouts:
        name = (layout.name or "").lower()
        if title_layout is None and any(hint == name for hint in _TITLE_HINTS):
            title_layout = layout
        if content_layout is None and any(hint in name for hint in _CONTENT_HINTS):
            if "title slide" not in name:
                content_layout = layout

    # Structural fallback: a usable content layout has a title plus a body/content
    # placeholder (types 2 = BODY, 7 = OBJECT/content).
    if content_layout is None:
        for layout in layouts:
            types = _placeholder_types(layout)
            if 13 not in types and ({2, 7} & types):
                content_layout = layout
                break

    if title_layout is None:
        title_layout = layouts[0]
    if content_layout is None:
        content_layout = layouts[1] if len(layouts) > 1 else layouts[0]

    return title_layout, content_layout


def _clear_slides(presentation) -> None:
    """Drop any example slides shipped with the template, keeping masters/layouts."""
    xml_slides = presentation.slides._sldIdLst
    for slide_id in list(xml_slides):
        rid = slide_id.get(
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
        )
        if rid:
            presentation.part.drop_rel(rid)
        xml_slides.remove(slide_id)


def _set_text(placeholder, text: str) -> None:
    placeholder.text_frame.text = text


def _fill_bullets(placeholder, bullets: list[tuple[int, str]]) -> None:
    """Write bullets at their indent levels, reusing the template's own list styling."""
    frame = placeholder.text_frame
    frame.clear()
    if not bullets:
        frame.text = ""
        return

    level, text = bullets[0]
    frame.paragraphs[0].text = text
    frame.paragraphs[0].level = level

    for level, text in bullets[1:]:
        paragraph = frame.add_paragraph()
        paragraph.text = text
        paragraph.level = level


# --------------------------------------------------------------------------
# Markdown → slides
# --------------------------------------------------------------------------


def parse_slides(markdown: str) -> list[dict[str, Any]]:
    """
    Split a generated deck draft into slides.

    Every level-2 heading (`## …`) starts a slide; the lines beneath it become
    bullets. A leading `# …` line is treated as the deck title.
    """
    deck_title = ""
    slides: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for raw in (markdown or "").split("\n"):
        line = raw.rstrip()
        stripped = line.strip()

        if not stripped or stripped.startswith("---"):
            continue

        if stripped.startswith("## "):
            current = {"title": _plain(stripped[3:]), "bullets": []}
            slides.append(current)
            continue

        if stripped.startswith("# "):
            deck_title = _plain(stripped[2:])
            continue

        if current is None:
            continue

        if stripped.startswith("### "):
            current["bullets"].append((0, _plain(stripped[4:])))
        elif stripped.startswith(("- ", "* ", "• ")):
            current["bullets"].append((1, _plain(stripped[2:])))
        else:
            current["bullets"].append((0, _plain(stripped)))

    return [{"deck_title": deck_title}] + slides if slides else []


def _plain(text: str) -> str:
    """Strip the Markdown emphasis that PowerPoint's own styling should own."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
    text = re.sub(r"`(.+?)`", r"\1", text)
    text = re.sub(r"^\*\*|\*\*$", "", text)
    return text.strip()


# --------------------------------------------------------------------------
# Build
# --------------------------------------------------------------------------


def build_deck(
    markdown: str,
    template_path: str | None,
    title: str,
    subtitle: str = "",
    max_bullets_per_slide: int = 8,
) -> tuple[bytes | None, str]:
    """
    Render `markdown` into a .pptx, using `template_path` for branding when given.

    Returns (bytes, note). On failure `bytes` is None and `note` explains why, so the
    caller can surface it rather than dropping the download silently.
    """
    if not _require_pptx():
        return None, "PPTX export needs python-pptx — run: pip install -r requirements.txt"

    from pptx import Presentation

    note = ""
    try:
        if template_path and os.path.exists(template_path):
            presentation = Presentation(template_path)
            _clear_slides(presentation)
        else:
            presentation = Presentation()
            note = "No brand template selected — generated with the default PowerPoint theme."
    except Exception as exc:
        presentation = Presentation()
        note = (f"Could not open the brand template ({type(exc).__name__}) — "
                "generated with the default theme instead.")

    try:
        title_layout, content_layout = _pick_layouts(presentation)
        parsed = parse_slides(markdown)

        # Title slide
        slide = presentation.slides.add_slide(title_layout)
        if slide.shapes.title:
            _set_text(slide.shapes.title, title)
        for placeholder in slide.placeholders:
            if placeholder.placeholder_format.idx != 0 and subtitle:
                _set_text(placeholder, subtitle)
                break

        # Content slides
        for entry in parsed[1:]:
            bullets = entry["bullets"]
            chunks = [bullets[i:i + max_bullets_per_slide]
                      for i in range(0, len(bullets), max_bullets_per_slide)] or [[]]

            for index, chunk in enumerate(chunks):
                slide = presentation.slides.add_slide(content_layout)
                heading = entry["title"] if index == 0 else f"{entry['title']} (cont.)"
                if slide.shapes.title:
                    _set_text(slide.shapes.title, heading)

                body = None
                for placeholder in slide.placeholders:
                    if placeholder.placeholder_format.idx != 0:
                        body = placeholder
                        break
                if body is not None:
                    _fill_bullets(body, chunk)

        buffer = io.BytesIO()
        presentation.save(buffer)
        return buffer.getvalue(), note
    except Exception as exc:
        return None, f"Deck generation failed: {type(exc).__name__}: {exc}"
