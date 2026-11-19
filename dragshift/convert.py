"""Format conversions. Every function takes a source path and returns a list of
output paths written next to the source."""
from __future__ import annotations

import html
import io
import sys
from pathlib import Path

from PIL import Image, ImageOps

from .util import UserError, sibling

try:  # HEIC / HEIF support
    import pillow_heif
    pillow_heif.register_heif_opener()
    HEIF_OK = True
except Exception:  # pragma: no cover
    HEIF_OK = False

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

IMAGE_TARGETS = ["PNG", "JPG", "WEBP", "HEIC", "TIFF", "AVIF", "BMP", "PDF", "ICO", "GIF"]
PDF_TARGETS = ["JPG", "PNG", "DOCX", "PPTX", "PPTX ✎", "TXT"]
DOCX_TARGETS = ["PDF", "TXT"]
TEXT_TARGETS = ["PDF", "DOCX"]

PIL_FORMAT = {"PNG": "PNG", "JPG": "JPEG", "WEBP": "WEBP", "HEIC": "HEIF", "TIFF": "TIFF",
              "AVIF": "AVIF", "BMP": "BMP", "PDF": "PDF", "ICO": "ICO", "GIF": "GIF"}
NO_ALPHA = {"JPG", "PDF", "BMP"}


# ---------------------------------------------------------------- images
def open_image(path: str | Path) -> Image.Image:
    im = Image.open(path)
    im.seek(0)
    im = ImageOps.exif_transpose(im)  # honour camera rotation
    if im.mode in ("P", "LA", "PA"):
        im = im.convert("RGBA")
    elif im.mode not in ("RGB", "RGBA", "L"):
        im = im.convert("RGB")
    return im


def open_preview(path: str | Path, max_side: int = 1400) -> Image.Image:
    """Fast, reduced-size decode for on-screen previews (JPEG decodes at 1/2, 1/4, 1/8 scale)."""
    im = Image.open(path)
    im.seek(0)
    if im.format == "JPEG":
        im.draft("RGB", (max_side, max_side))
    im = ImageOps.exif_transpose(im)
    if im.mode in ("P", "LA", "PA"):
        im = im.convert("RGBA")
    elif im.mode not in ("RGB", "RGBA", "L"):
        im = im.convert("RGB")
    if max(im.size) > max_side:
        im.thumbnail((max_side, max_side), Image.LANCZOS)
    return im


def open_pdf(path: str | Path):
    doc = fitz.open(path)
    if doc.needs_pass:
        doc.close()
        raise UserError("This PDF is password-protected. Remove the password first.")
    return doc


def flatten(im: Image.Image, bg=(255, 255, 255)) -> Image.Image:
    if im.mode == "RGBA":
        base = Image.new("RGB", im.size, bg)
        base.paste(im, mask=im.split()[3])
        return base
    return im.convert("RGB") if im.mode != "RGB" else im


def save_image(im: Image.Image, out: Path, target: str, quality: int | None = None, exif=None) -> None:
    from .util import CONFIG
    quality = quality or int(CONFIG.get("jpg_quality", 90))
    target = target.upper()
    fmt = PIL_FORMAT[target]
    if target in NO_ALPHA:
        im = flatten(im)
    kw: dict = {}
    if target in ("JPG", "WEBP", "AVIF", "HEIC"):
        kw["quality"] = quality
    if target == "JPG":
        kw.update(optimize=True, progressive=True)
    if target == "PNG":
        kw["optimize"] = True
    if target == "ICO":
        side = min(256, max(im.size))
        im = ImageOps.contain(im.convert("RGBA"), (side, side))
        kw["sizes"] = [(s, s) for s in (16, 24, 32, 48, 64, 128, 256) if s <= side]
    if target == "PDF":
        kw["resolution"] = 150.0
    if exif and target in ("JPG", "WEBP", "PNG", "TIFF"):
        kw["exif"] = exif
    atomic_save(lambda dst: im.save(dst, fmt, **kw), out)


def atomic_save(write, out):
    """Write to a hidden temp file, then rename: Explorer never shows a half-written file."""
    import os
    if not isinstance(out, (str, Path)):
        write(out)  # in-memory buffer
        return
    out = Path(out)
    tmp = out.with_name(f".~{out.name}.part")
    try:
        write(tmp)
        os.replace(tmp, out)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def image_to(src: str | Path, target: str) -> list[Path]:
    target = target.upper()
    im = open_image(src)
    out = sibling(src, ext="." + target.lower())
    save_image(im, out, target)
    return [out]


def images_to_single_pdf(srcs: list[str | Path]) -> list[Path]:
    pages = [flatten(open_image(s)) for s in srcs]
    out = sibling(srcs[0], "Combined", ".pdf")
    pages[0].save(out, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    return [out]


# ---------------------------------------------------------------- PDF
def pdf_to_images(src: str | Path, target: str, dpi: int | None = None) -> list[Path]:
    from .util import CONFIG
    dpi = dpi or int(CONFIG.get("pdf_dpi", 200))
    target = target.upper()
    outs = []
    with open_pdf(src) as doc:
        n = doc.page_count
        for i, page in enumerate(doc):
            pix = page.get_pixmap(dpi=dpi, alpha=False)
            im = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            label = f"page {i + 1}" if n > 1 else ""
            out = sibling(src, label, "." + target.lower())
            save_image(im, out, target)
            outs.append(out)
    return outs


def pdf_to_txt(src: str | Path) -> list[Path]:
    from . import ocr
    with open_pdf(src) as doc:
        parts = []
        for page in doc:
            if ocr.available() and ocr.page_is_scanned(page):
                parts.append(ocr.lines_text(ocr.page_lines(page)))   # scanned page: read it
            else:
                parts.append(page.get_text("text"))
        text = "\n\f\n".join(parts)
    out = sibling(src, ext=".txt")
    out.write_text(text, encoding="utf-8")
    return [out]


def _font_family(name: str) -> str:
    name = name.split("+", 1)[-1]                      # drop subset prefix "ABCDEF+"
    for suf in ("-BoldItalic", "-BoldOblique", "-Bold", "-Italic", "-Oblique", "-Regular", "-Medium",
                "-Light", "-SemiBold", "-Semibold", "-Black", "-Heavy", "-Thin", "-ExtraBold", ",Bold"):
        if name.endswith(suf):
            return name[: -len(suf)]
    return name


def pdf_to_pptx(src: str | Path, editable: bool = False, dpi: int | None = None) -> list[Path]:
    """One slide per page.

    editable=False: the page as a full-slide picture, its text in the speaker notes.
    editable=True:  the page without its text as the background picture, and the text laid back on
                    top as editable text boxes in the same places (fonts may be substituted).
    """
    from pptx import Presentation
    from pptx.dml.color import RGBColor
    from pptx.enum.text import MSO_AUTO_SIZE
    from pptx.util import Emu, Pt
    from . import ocr
    from .util import CONFIG
    dpi = dpi or int(CONFIG.get("pdf_dpi", 200))
    EMU_PER_PT = 12700
    MAX, MIN = 51206400, 914400          # PowerPoint's slide size limits (56 in / 1 in)
    prs = Presentation()
    with open_pdf(src) as doc:
        if doc.page_count == 0:
            raise UserError("This PDF has no pages.")
        r0 = doc[0].rect
        w, h = r0.width * EMU_PER_PT, r0.height * EMU_PER_PT
        k = min(1.0, MAX / max(w, h))
        if min(w * k, h * k) < MIN:
            k = MIN / min(w, h)
        prs.slide_width, prs.slide_height = Emu(int(w * k)), Emu(int(h * k))
        sw, sh = prs.slide_width, prs.slide_height
        blank = prs.slide_layouts[6]
        for pno, page in enumerate(doc):
            # fit (letterbox) pages whose shape differs from the first one
            pr = page.rect.width / page.rect.height
            if pr >= sw / sh:
                pw, ph = sw, int(sw / pr)
            else:
                pw, ph = int(sh * pr), sh
            ox, oy = (sw - pw) // 2, (sh - ph) // 2
            s = pw / page.rect.width                     # EMU per PDF point on this slide
            slide = prs.slides.add_slide(blank)
            blocks = []
            render = page
            tmp = None
            scanned_lines = None
            if editable and ocr.available() and ocr.page_is_scanned(page):
                page_im = ocr.page_image(page)
                scanned_lines = [ln for ln, _ in ocr.page_lines(page, page_im)]
            elif editable:
                info = page.get_text("dict", flags=fitz.TEXTFLAGS_TEXT)
                tmp = fitz.open()
                tmp.insert_pdf(doc, from_page=pno, to_page=pno)
                bp = tmp[0]
                for b in info["blocks"]:
                    if b.get("type") != 0:
                        continue
                    lines = [ln for ln in b["lines"] if abs(ln["dir"][1]) < 0.05 and
                             "".join(sp["text"] for sp in ln["spans"]).strip()]
                    if not lines:
                        continue
                    for ln in lines:
                        bp.add_redact_annot(fitz.Rect(ln["bbox"]), fill=False)
                    blocks.append(lines)
                bp.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                                    graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                                    text=fitz.PDF_REDACT_TEXT_REMOVE)
                render = bp
            pix = render.get_pixmap(dpi=dpi, alpha=False)
            slide.shapes.add_picture(io.BytesIO(pix.tobytes("png")), Emu(ox), Emu(oy), Emu(pw), Emu(ph))
            if tmp is not None:
                tmp.close()
            for ln in scanned_lines or []:
                # scanned page: cover the printed words with their background colour, type them on top
                W, H = page_im.size
                pad = (ln.y1 - ln.y0) * 0.12
                bg, fg = ocr.colours(page_im, ((ln.x0 - pad / 3) * W, (ln.y0 - pad) * H,
                                               (ln.x1 + pad / 3) * W, (ln.y1 + pad) * H))
                left, top = ox + (ln.x0 - pad / 3) * pw, oy + (ln.y0 - pad) * ph
                tb = slide.shapes.add_textbox(Emu(int(left)), Emu(int(top)),
                                              Emu(max(1, int((ln.x1 - ln.x0 + pad * 2 / 3) * pw))),
                                              Emu(max(1, int((ln.y1 - ln.y0 + pad * 2) * ph))))
                tb.fill.solid()
                tb.fill.fore_color.rgb = RGBColor(*bg)
                tf = tb.text_frame
                tf.word_wrap = False
                tf.auto_size = MSO_AUTO_SIZE.NONE
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                run = tf.paragraphs[0].add_run()
                run.text = ln.text
                run.font.size = Pt(max(1, round((ln.y1 - ln.y0) * ph * 0.95 / EMU_PER_PT, 1)))
                run.font.color.rgb = RGBColor(*fg)
            if scanned_lines is not None:
                text = "\n".join(ln.text for ln in scanned_lines)
                if text:
                    slide.notes_slide.notes_text_frame.text = text
                continue
            for lines in blocks:
                x0 = min(ln["bbox"][0] for ln in lines) - page.rect.x0
                y0 = min(ln["bbox"][1] for ln in lines) - page.rect.y0
                x1 = max(ln["bbox"][2] for ln in lines) - page.rect.x0
                y1 = max(ln["bbox"][3] for ln in lines) - page.rect.y0
                tb = slide.shapes.add_textbox(Emu(int(ox + x0 * s)), Emu(int(oy + y0 * s)),
                                              Emu(max(1, int((x1 - x0) * s * 1.04))), Emu(max(1, int((y1 - y0) * s))))
                tf = tb.text_frame
                tf.word_wrap = False
                tf.auto_size = MSO_AUTO_SIZE.NONE
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                pitch = ((lines[-1]["bbox"][1] - lines[0]["bbox"][1]) / (len(lines) - 1)) if len(lines) > 1 else None
                for i, ln in enumerate(lines):
                    para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
                    para.space_before = para.space_after = Pt(0)
                    if pitch:
                        para.line_spacing = Pt(max(1, pitch * s / EMU_PER_PT))
                    for sp in ln["spans"]:
                        if not sp["text"]:
                            continue
                        run = para.add_run()
                        run.text = sp["text"].replace("\xa0", " ")
                        f = run.font
                        f.size = Pt(max(1, round(sp["size"] * s / EMU_PER_PT, 1)))
                        f.bold = bool(sp["flags"] & 16) or "Bold" in sp["font"]
                        f.italic = bool(sp["flags"] & 2)
                        c = sp.get("color", 0)
                        f.color.rgb = RGBColor((c >> 16) & 255, (c >> 8) & 255, c & 255)
                        fam = _font_family(sp["font"])
                        if fam:
                            f.name = fam
            text = page.get_text("text").strip()
            if text:
                slide.notes_slide.notes_text_frame.text = text
    out = sibling(src, "editable" if editable else "", ext=".pptx")
    prs.save(str(out))
    return [out]


def pdf_to_docx(src: str | Path) -> list[Path]:
    """Text blocks become paragraphs, embedded images are kept, one Word page per PDF page."""
    from docx import Document
    from docx.enum.text import WD_BREAK
    from docx.shared import Inches

    d = Document()
    with open_pdf(src) as doc:
        for pno, page in enumerate(doc):
            if pno:
                d.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
            items = []
            for b in page.get_text("dict")["blocks"]:
                y = b["bbox"][1]
                if b.get("type") == 0:
                    lines = []
                    size = 11.0
                    bold = False
                    for ln in b["lines"]:
                        spans = ln["spans"]
                        if spans:
                            size = max(size, max(s["size"] for s in spans)) if not lines else size
                            bold = bold or any("Bold" in s["font"] for s in spans)
                        lines.append("".join(s["text"] for s in spans))
                    txt = " ".join(l.strip() for l in lines).strip()
                    if txt:
                        items.append((y, "text", (txt, size, bold)))
                elif b.get("type") == 1 and b.get("image"):
                    items.append((y, "img", (b["image"], b["bbox"])))
            items.sort(key=lambda t: t[0])
            for _, kind, data in items:
                if kind == "text":
                    txt, size, bold = data
                    if size >= 16:
                        d.add_heading(txt, level=1 if size >= 20 else 2)
                    else:
                        p = d.add_paragraph()
                        r = p.add_run(txt)
                        r.bold = bold and len(txt) < 120
                else:
                    raw, bbox = data
                    width_in = min(6.5, max(0.5, (bbox[2] - bbox[0]) / 72))
                    try:
                        d.add_picture(io.BytesIO(raw), width=Inches(width_in))
                    except Exception:
                        pass
    out = sibling(src, ext=".docx")
    d.save(out)
    return [out]


# ---------------------------------------------------------------- DOCX
def _docx_paragraph_html(p) -> str:
    parts = []
    for r in p.runs:
        t = html.escape(r.text)
        if not t:
            continue
        if r.bold:
            t = f"<b>{t}</b>"
        if r.italic:
            t = f"<i>{t}</i>"
        if r.underline:
            t = f"<u>{t}</u>"
        parts.append(t)
    body = "".join(parts) or "&nbsp;"
    style = (p.style.name or "").lower() if p.style is not None else ""
    if style.startswith("heading"):
        lvl = "".join(c for c in style if c.isdigit()) or "1"
        lvl = str(min(int(lvl), 6))
        return f"<h{lvl}>{body}</h{lvl}>"
    if style == "title":
        return f"<h1>{body}</h1>"
    if "list" in style:
        return f"<p>&bull; {body}</p>"
    return f"<p>{body}</p>"


def docx_to_html(src: str | Path) -> str:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    d = Document(src)
    out = []
    for child in d.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            out.append(_docx_paragraph_html(Paragraph(child, d)))
        elif tag == "tbl":
            t = Table(child, d)
            rows = []
            for row in t.rows:
                cells = "".join(f"<td>{html.escape(c.text)}</td>" for c in row.cells)
                rows.append(f"<tr>{cells}</tr>")
            out.append("<table>" + "".join(rows) + "</table>")
    return "\n".join(out)


def docx_to_txt(src: str | Path) -> list[Path]:
    from docx import Document
    d = Document(src)
    lines = [p.text for p in d.paragraphs]
    for t in d.tables:
        for row in t.rows:
            lines.append("\t".join(c.text for c in row.cells))
    out = sibling(src, ext=".txt")
    out.write_text("\n".join(lines), encoding="utf-8")
    return [out]


def _word_to_pdf(src: Path, out: Path) -> bool:
    """Use Microsoft Word (if installed) for a perfect-fidelity export."""
    if sys.platform != "win32":
        return False
    try:
        import win32com.client  # type: ignore
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        try:
            doc = word.Documents.Open(str(src.resolve()), ReadOnly=True)
            doc.SaveAs(str(out.resolve()), FileFormat=17)  # wdFormatPDF
            doc.Close(False)
        finally:
            word.Quit()
        return out.exists()
    except Exception:
        return False


CSS = """
* { font-family: sans-serif; }
body { font-size: 11pt; line-height: 1.35; }
h1 { font-size: 20pt; } h2 { font-size: 16pt; } h3 { font-size: 13pt; }
p { margin: 0 0 6pt 0; }
pre { font-family: monospace; font-size: 9.5pt; white-space: pre-wrap; }
table { border-collapse: collapse; margin: 6pt 0; }
td { border: 1px solid #888; padding: 3pt 5pt; font-size: 10pt; }
"""


def html_to_pdf(body_html: str, out: Path) -> None:
    story = fitz.Story(html=body_html, user_css=CSS)
    writer = fitz.DocumentWriter(str(out))
    mediabox = fitz.paper_rect("letter")
    where = mediabox + (54, 54, -54, -54)
    more = True
    while more:
        dev = writer.begin_page(mediabox)
        more, _ = story.place(where)
        story.draw(dev)
        writer.end_page()
    writer.close()


def docx_to_pdf(src: str | Path) -> list[Path]:
    src = Path(src)
    out = sibling(src, ext=".pdf")
    if not _word_to_pdf(src, out):
        html_to_pdf(docx_to_html(src), out)
    return [out]


# ---------------------------------------------------------------- text
def read_text(src: str | Path) -> str:
    raw = Path(src).read_bytes()
    for enc in ("utf-8-sig", "utf-16", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def text_to_pdf(src: str | Path) -> list[Path]:
    out = sibling(src, ext=".pdf")
    html_to_pdf(f"<pre>{html.escape(read_text(src))}</pre>", out)
    return [out]


def text_to_docx(src: str | Path) -> list[Path]:
    from docx import Document
    d = Document()
    for line in read_text(src).splitlines():
        d.add_paragraph(line)
    out = sibling(src, ext=".docx")
    d.save(out)
    return [out]


# ---------------------------------------------------------------- dispatch
def targets_for(cat: str, src_ext: str) -> list[str]:
    src_ext = src_ext.lower().lstrip(".")
    same = {"jpeg": "JPG", "jpg": "JPG", "tif": "TIFF", "tiff": "TIFF", "heif": "HEIC"}
    cur = same.get(src_ext, src_ext.upper())
    if cat == "image":
        t = [x for x in IMAGE_TARGETS if x != cur]
        if not HEIF_OK:
            t = [x for x in t if x != "HEIC"]
        return t
    return {"pdf": PDF_TARGETS, "docx": DOCX_TARGETS, "text": TEXT_TARGETS}.get(cat, [])


def convert(src: str | Path, cat: str, target: str) -> list[Path]:
    target = target.upper()
    if cat == "image":
        return image_to(src, target)
    if cat == "pdf":
        if target in ("JPG", "PNG"):
            return pdf_to_images(src, target)
        if target == "TXT":
            return pdf_to_txt(src)
        if target == "DOCX":
            return pdf_to_docx(src)
        if target == "PPTX":
            return pdf_to_pptx(src)
        if target == "PPTX ✎":
            return pdf_to_pptx(src, editable=True)
    if cat == "docx":
        return docx_to_pdf(src) if target == "PDF" else docx_to_txt(src)
    if cat == "text":
        return text_to_pdf(src) if target == "PDF" else text_to_docx(src)
    raise ValueError(f"Can't convert {cat} to {target}")
