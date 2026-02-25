"""File processing service for context extraction"""
import os
from io import BytesIO
from typing import Any, Dict

from PyPDF2 import PdfReader

TEXT_FILE_EXTENSIONS = {".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml"}
MAX_CONTENT_CHARS = 10000
PREVIEW_CHARS = 1000


class FileProcessorService:
    """Process uploaded files for context extraction"""

    def __init__(self, max_size_mb: int = 10, allowed_types: list = None):
        self.max_size_mb = max_size_mb
        self.allowed_types = allowed_types or [
            ".pdf", ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml"
        ]
        self._allowed_types_set = set(self.allowed_types)

    def _validate_file(self, filename: str, content: bytes) -> str:
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.max_size_mb:
            raise ValueError(f"File too large: {size_mb:.2f}MB (max: {self.max_size_mb}MB)")

        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in self._allowed_types_set:
            raise ValueError(f"Unsupported file type: {file_ext}")
        return file_ext

    def _extract_text_content(self, file_ext: str, content: bytes) -> str:
        if file_ext == ".pdf":
            return self._extract_pdf(content)
        if file_ext in TEXT_FILE_EXTENSIONS:
            return content.decode("utf-8", errors="ignore")
        raise ValueError(f"Unsupported file type: {file_ext}")

    def _truncate_content(self, text_content: str) -> str:
        if len(text_content) <= MAX_CONTENT_CHARS:
            return text_content
        return text_content[:MAX_CONTENT_CHARS] + "\n\n... (truncated)"

    async def process_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Process uploaded file and extract content"""
        file_ext = self._validate_file(filename, content)
        text_content = self._extract_text_content(file_ext, content)
        text_content = self._truncate_content(text_content)
        summary = self._build_summary(filename, text_content, file_ext)

        return {
            "filename": filename,
            "file_type": file_ext,
            "content": text_content,
            "summary": summary,
            "size_bytes": len(content)
        }

    def _extract_pdf(self, content: bytes) -> str:
        """Extract text from PDF"""
        try:
            pdf_file = BytesIO(content)
            reader = PdfReader(pdf_file)
            return "".join((page.extract_text() or "") + "\n" for page in reader.pages)
        except Exception as e:
            raise ValueError(f"Failed to extract PDF content: {str(e)}") from e

    def _build_summary(self, filename: str, content: str, file_type: str) -> str:
        """Build file summary for planner"""
        summary = f"## Uploaded File: {filename}\n\n"
        summary += f"**Type:** {file_type}\n"
        summary += f"**Size:** {len(content)} characters\n\n"

        preview = content[:PREVIEW_CHARS]
        summary += f"### Content Preview:\n\n```\n{preview}\n```\n"

        return summary
