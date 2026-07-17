"""Document parsing and chunking tests."""

from io import BytesIO

import pytest
from docx import Document as DocxDocument

from app.rag.document_processing import (
    DocumentProcessingError,
    chunk_text,
    parse_document,
)


def test_parse_utf8_text() -> None:
    parsed = parse_document(filename="notes.md", data="Привет, Norma".encode())

    assert parsed.file_type == "markdown"
    assert parsed.text == "Привет, Norma"


def test_parse_docx() -> None:
    stream = BytesIO()
    document = DocxDocument()
    document.add_paragraph("Knowledge paragraph")
    document.save(stream)

    parsed = parse_document(filename="knowledge.docx", data=stream.getvalue())

    assert parsed.file_type == "docx"
    assert parsed.text == "Knowledge paragraph"


def test_reject_unsupported_document() -> None:
    with pytest.raises(DocumentProcessingError, match="Unsupported"):
        parse_document(filename="archive.zip", data=b"content")


def test_chunk_text_is_deterministic_and_overlapping() -> None:
    text = "First sentence. Second sentence. Third sentence. Fourth sentence."

    chunks = chunk_text(text, chunk_size=30, overlap=8)

    assert chunks == chunk_text(text, chunk_size=30, overlap=8)
    assert len(chunks) > 1
    assert all(chunks)
