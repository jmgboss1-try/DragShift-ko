"""Text recognition (OCR) for scanned PDFs and photos of documents.

macOS:   Apple Vision (the engine behind Live Text) — offline, Korean + English.
Windows: Windows.Media.Ocr (built into Windows 10/11) — offline; Korean needs the Korean language
         pack (Settings → Time & language → Language → Korean), otherwise the user's display language.
Linux:   not available (the OCR menu items are hidden).
"""
from __future__ import annotations

import io
import sys
from dataclasses import dataclass

from PIL import Image

from .util import UserError, sibling

try:
    import pymupdf as fitz
except ImportError:  # pragma: no cover
    import fitz  # type: ignore

LANGS = ["ko-KR", "en-US"]
DPI = 300                 # render scanned pages at this resolution before recognising
MIN_TEXT_CHARS = 10       # a page with fewer real characters than this counts as "scanned"
OCR_FONT = "korea"        # PyMuPDF's built-in CJK font (covers Hangul + Latin) for the hidden layer

# tests (or other platforms later) can plug in their own engine: f(PIL.Image) -> list[Line]
engine = None


@dataclass
class Line:
    text: str
    x0: float   # normalised 0..1, origin top-left
    y0: float
    x1: float
    y1: float
    conf: float = 1.0


# ---------------------------------------------------------------- engines
_VISION = None


def _vision_ok() -> bool:
    global _VISION
    if _VISION is None:
        _VISION = False
        if sys.platform == "darwin":
            try:
                import Vision  # noqa: F401
                import Quartz  # noqa: F401
                _VISION = True
            except Exception:
                pass
    return _VISION


_WINOCR = None


def _winocr_ok() -> bool:
    global _WINOCR
    if _WINOCR is None:
        _WINOCR = False
        if sys.platform == "win32":
            try:
                from winrt.windows.media.ocr import OcrEngine
                _WINOCR = OcrEngine.try_create_from_user_profile_languages() is not None or \
                    bool(list(OcrEngine.available_recognizer_languages))
            except Exception:
                pass
    return _WINOCR


def available() -> bool:
    return engine is not None or _vision_ok() or _winocr_ok()


def windows_languages() -> list[str]:
    try:
        from winrt.windows.media.ocr import OcrEngine
        return [l.language_tag for l in OcrEngine.available_recognizer_languages]
    except Exception:
        return []


def _winocr(im: Image.Image) -> list[Line]:
    import asyncio
    import os
    import tempfile
    try:
        from winrt.runtime import ApartmentType, init_apartment
        init_apartment(ApartmentType.MULTI_THREADED)
    except Exception:
        pass                                   # already initialised on this thread
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.storage import FileAccessMode, StorageFile

    W, H = im.size
    limit = int(OcrEngine.max_image_dimension or 10000)
    scale = min(1.0, limit / max(W, H))
    if scale < 1.0:
        im = im.resize((int(W * scale), int(H * scale)), Image.LANCZOS)
    w, h = im.size
    fd, path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    im.convert("RGB").save(path, "PNG")

    async def run():
        f = await StorageFile.get_file_from_path_async(path)
        stream = await f.open_async(FileAccessMode.READ)
        decoder = await BitmapDecoder.create_async(stream)
        bmp = await decoder.get_software_bitmap_async()
        eng = None
        for tag in ("ko-KR", "ko"):
            lang = Language(tag)
            if OcrEngine.is_language_supported(lang):
                eng = OcrEngine.try_create_from_language(lang)
                break
        eng = eng or OcrEngine.try_create_from_user_profile_languages()
        if eng is None:
            raise UserError("Text recognition isn't available on this computer yet.")
        res = await eng.recognize_async(bmp)
        try:
            stream.close()
        except Exception:
            pass
        out = []
        for line in res.lines:
            words = list(line.words)
            if not words:
                continue
            rs = [wd.bounding_rect for wd in words]
            x0 = min(r.x for r in rs); y0 = min(r.y for r in rs)
            x1 = max(r.x + r.width for r in rs); y1 = max(r.y + r.height for r in rs)
            text = " ".join(wd.text for wd in words).strip()
            if text:
                out.append(Line(text, x0 / w, y0 / h, x1 / w, y1 / h))
        return out

    try:
        return asyncio.run(run())
    finally:
        try:
            os.remove(path)
        except OSError:
            pass


def _cgimage(im: Image.Image):
    import Quartz
    from Foundation import NSData
    buf = io.BytesIO()
    im.convert("RGB").save(buf, "PNG")
    raw = buf.getvalue()
    data = NSData.dataWithBytes_length_(raw, len(raw))
    src = Quartz.CGImageSourceCreateWithData(data, None)
    return Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)


def _vision(im: Image.Image) -> list[Line]:
    import Vision
    cg = _cgimage(im)

    def run(langs):
        req = Vision.VNRecognizeTextRequest.alloc().init()
        req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
        req.setUsesLanguageCorrection_(True)
        if langs:
            req.setRecognitionLanguages_(langs)
        handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, {})
        res = handler.performRequests_error_([req], None)
        ok = res[0] if isinstance(res, tuple) else bool(res)
        return req.results() if ok else None

    results = run(LANGS)
    if results is None:              # older macOS without Korean: fall back to the default languages
        results = run(None)
    if results is None:
        raise UserError("Text recognition failed on this Mac.")
    out = []
    for obs in results:
        cands = obs.topCandidates_(1)
        if not cands:
            continue
        c = cands[0]
        text = str(c.string()).strip()
        if not text:
            continue
        bb = obs.boundingBox()       # normalised, origin bottom-left
        x, y, w, h = bb.origin.x, bb.origin.y, bb.size.width, bb.size.height
        out.append(Line(text, x, 1 - (y + h), x + w, 1 - y, float(c.confidence())))
    return out


def recognize(im: Image.Image) -> list[Line]:
    """Lines of text in reading order (top to bottom, left to right)."""
    if engine is not None:
        lines = engine(im)
    elif _vision_ok():
        lines = _vision(im)
    elif _winocr_ok():
        lines = _winocr(im)
    else:
        raise UserError("Text recognition isn't available on this computer yet.")
    if not lines:
        return []
    h = sorted(l.y1 - l.y0 for l in lines)[len(lines) // 2] or 0.01
    return sorted(lines, key=lambda l: (round(((l.y0 + l.y1) / 2) / (h * 0.6)), l.x0))


# ---------------------------------------------------------------- helpers
def page_is_scanned(page) -> bool:
    return len("".join(page.get_text("text").split())) < MIN_TEXT_CHARS


def page_image(page, dpi: int = DPI) -> Image.Image:
    pix = page.get_pixmap(dpi=dpi, alpha=False)
    return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def page_lines(page, im: Image.Image | None = None) -> list[tuple[Line, "fitz.Rect"]]:
    """OCR one page; returns each line with its rectangle in (unrotated) page coordinates."""
    im = im or page_image(page)
    r = page.rect                      # rotated (visible) page rect, origin top-left
    out = []
    for ln in recognize(im):
        vis = fitz.Rect(r.x0 + ln.x0 * r.width, r.y0 + ln.y0 * r.height,
                        r.x0 + ln.x1 * r.width, r.y0 + ln.y1 * r.height)
        out.append((ln, vis * page.derotation_matrix))
    return out


def lines_text(lines) -> str:
    """Join recognised lines; lines on the same row are joined with spaces."""
    rows, last = [], None
    for ln, _ in lines:
        mid = (ln.y0 + ln.y1) / 2
        if last is not None and abs(mid - last[0]) < (last[1] * 0.5):
            rows[-1] += " " + ln.text
        else:
            rows.append(ln.text)
        last = (mid, ln.y1 - ln.y0)
    return "\n".join(rows)


_FONT = None


def add_hidden_text(page, lines):
    """Invisible, selectable/searchable text over a scanned page (render mode 3).

    The font is embedded so the widths used for fitting match the widths PDF readers use."""
    global _FONT
    if _FONT is None:
        _FONT = fitz.Font(OCR_FONT)
    page.insert_font(fontname="ocrkr", fontbuffer=_FONT.buffer)
    for ln, rect in lines:
        vis = rect * page.rotation_matrix  # back to visible coordinates for sizing
        h = vis.height
        size = max(1.0, h * 0.85)
        width = _FONT.text_length(ln.text, fontsize=size) or 1
        sx = max(0.2, min(5.0, vis.width / width))
        origin = fitz.Point(vis.x0, vis.y1 - h * 0.18) * page.derotation_matrix
        page.insert_text(origin, ln.text, fontname="ocrkr", fontsize=size, render_mode=3,
                         rotate=page.rotation, morph=(origin, fitz.Matrix(sx, 1)))


# ---------------------------------------------------------------- actions
def ocr_pdf(src) -> list:
    """Scanned PDF -> searchable PDF (same look) + TXT. Pages that already have text are kept as-is."""
    from .convert import open_pdf
    texts, found = [], False
    with open_pdf(src) as doc:
        out_doc = fitz.open()
        out_doc.insert_pdf(doc)
    for pno, page in enumerate(out_doc):
        if page_is_scanned(page):
            lines = page_lines(page)
            if lines:
                found = True
                add_hidden_text(page, lines)
            texts.append(lines_text(lines))
        else:
            texts.append(page.get_text("text").strip())
            found = found or bool(texts[-1])
    if not found:
        out_doc.close()
        raise UserError("No text was found.")
    pdf = sibling(src, "OCR", ".pdf")
    try:
        out_doc.subset_fonts()        # keep only the glyphs used (embedded CJK font is large)
    except Exception:
        pass
    out_doc.save(str(pdf), garbage=3, deflate=True)
    out_doc.close()
    txt = sibling(src, "OCR", ".txt")
    txt.write_text("\n\n\f\n".join(texts).strip() + "\n", encoding="utf-8")
    return [pdf, txt]


def ocr_image(src) -> list:
    """Photo / scan image -> TXT."""
    from .convert import open_image
    im = open_image(src).convert("RGB")
    W, H = im.size
    lines = [(ln, fitz.Rect(ln.x0 * W, ln.y0 * H, ln.x1 * W, ln.y1 * H)) for ln in recognize(im)]
    if not lines:
        raise UserError("No text was found.")
    txt = sibling(src, "OCR", ".txt")
    txt.write_text(lines_text(lines) + "\n", encoding="utf-8")
    return [txt]


def colours(im: Image.Image, box) -> tuple[tuple, tuple]:
    """(background, text) colours of a text line in a page image: border median vs. far pixels."""
    x0, y0, x1, y1 = [int(v) for v in box]
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(im.width, max(x0 + 1, x1)), min(im.height, max(y0 + 1, y1))
    crop = im.crop((x0, y0, x1, y1)).convert("RGB")
    px = list(crop.getdata())
    w, h = crop.size
    border = [crop.getpixel((x, 0)) for x in range(w)] + [crop.getpixel((x, h - 1)) for x in range(w)] + \
             [crop.getpixel((0, y)) for y in range(h)] + [crop.getpixel((w - 1, y)) for y in range(h)]

    def med(seq):
        return tuple(sorted(c[i] for c in seq)[len(seq) // 2] for i in range(3))
    bg = med(border)
    far = [c for c in px if sum(abs(c[i] - bg[i]) for i in range(3)) > 120]
    fg = med(far) if len(far) > 5 else ((0, 0, 0) if sum(bg) > 380 else (255, 255, 255))
    return bg, fg
