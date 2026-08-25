"""文件校验与解析测试。"""

from __future__ import annotations

import io

from docx import Document
from pypdf import PdfWriter

from app.core.errors import ErrorCode
from app.models.enums import MediaType
from app.services.documents.extractor import extract_text
from app.services.documents.validator import validate_upload


def _make_docx(paragraphs: list[str]) -> bytes:
    doc = Document()
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def _make_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _minimal_text_pdf(text: str) -> bytes:
    content = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode()
    pdf += b"0000000000 65535 f \n"
    for off in offsets:
        pdf += f"{off:010d} 00000 n \n".encode()
    pdf += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return bytes(pdf)


# ---- 校验 ----


def test_validate_docx():
    data = _make_docx(["hi"])
    media_type, err = validate_upload("a.docx", None, len(data), data[:16])
    assert err is None
    assert media_type == MediaType.DOCX


def test_validate_markdown():
    media_type, err = validate_upload("a.md", "text/markdown", 10, b"# hello\n")
    assert err is None
    assert media_type == MediaType.MARKDOWN


def test_validate_rejects_unknown_extension():
    _, err = validate_upload("a.exe", None, 10, b"whatever")
    assert err == ErrorCode.UNSUPPORTED_FILE


def test_validate_rejects_fake_signature():
    _, err = validate_upload("a.pdf", "application/pdf", 10, b"not a pdf at all")
    assert err == ErrorCode.UNSUPPORTED_FILE


def test_validate_rejects_conflicting_mime():
    data = _make_docx(["hi"])
    _, err = validate_upload("a.docx", "application/pdf", len(data), data[:16])
    assert err == ErrorCode.UNSUPPORTED_FILE


def test_validate_rejects_too_large(monkeypatch):
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    _, err = validate_upload("a.md", "text/plain", 2 * 1024 * 1024, b"# hi")
    assert err == ErrorCode.FILE_TOO_LARGE


# ---- 解析 ----


def test_extract_docx():
    text, err = extract_text(MediaType.DOCX, _make_docx(["第一段", "第二段"]))
    assert err is None
    assert "第一段" in text and "第二段" in text


def test_extract_markdown_strips_images():
    text, err = extract_text(
        MediaType.MARKDOWN, "# 标题\n正文 ![alt](http://x/a.png) 结束\n".encode()
    )
    assert err is None
    assert "标题" in text and "![alt]" not in text


def test_extract_empty_markdown():
    _, err = extract_text(MediaType.MARKDOWN, b"   \n  ")
    assert err == ErrorCode.EMPTY_DOCUMENT


def test_extract_scanned_pdf():
    _, err = extract_text(MediaType.PDF, _make_blank_pdf())
    assert err == ErrorCode.SCANNED_PDF_UNSUPPORTED


def test_extract_text_pdf():
    text, err = extract_text(MediaType.PDF, _minimal_text_pdf("HelloWorldThisIsEnoughText"))
    assert err is None
    assert "HelloWorldThisIsEnoughText" in text
