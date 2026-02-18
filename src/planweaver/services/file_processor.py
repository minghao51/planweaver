"""File processing service for context extraction"""
from PyPDF2 import PdfReader
from typing import Dict, Any
import os


class FileProcessorService:
    """Process uploaded files for context extraction"""

    def __init__(self, max_size_mb: int = 10, allowed_types: list = None):
        self.max_size_mb = max_size_mb
        self.allowed_types = allowed_types or [
            ".pdf", ".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml"
        ]

    async def process_file(self, filename: str, content: bytes) -> Dict[str, Any]:
        """Process uploaded file and extract content"""
        # Validate file size
        size_mb = len(content) / (1024 * 1024)
        if size_mb > self.max_size_mb:
            raise ValueError(f"File too large: {size_mb:.2f}MB (max: {self.max_size_mb}MB)")

        # Validate file type
        file_ext = os.path.splitext(filename)[1].lower()
        if file_ext not in self.allowed_types:
            raise ValueError(f"Unsupported file type: {file_ext}")

        # Extract content based on type
        if file_ext == ".pdf":
            text_content = self._extract_pdf(content)
        elif file_ext in [".txt", ".md", ".py", ".js", ".ts", ".json", ".yaml", ".yml"]:
            text_content = content.decode("utf-8", errors="ignore")
        else:
            raise ValueError(f"Unsupported file type: {file_ext}")

        # Limit content size
        max_chars = 10000
        if len(text_content) > max_chars:
            text_content = text_content[:max_chars] + "\n\n... (truncated)"

        # Build summary
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
            import io
            pdf_file = io.BytesIO(content)
            reader = PdfReader(pdf_file)

            text_content = ""
            for page in reader.pages:
                text_content += page.extract_text() + "\n"

            return text_content

        except Exception as e:
            raise ValueError(f"Failed to extract PDF content: {str(e)}")

    def _build_summary(self, filename: str, content: str, file_type: str) -> str:
        """Build file summary for planner"""
        summary = f"## Uploaded File: {filename}\n\n"
        summary += f"**Type:** {file_type}\n"
        summary += f"**Size:** {len(content)} characters\n\n"

        # Preview first 1000 characters
        preview = content[:1000]
        summary += f"### Content Preview:\n\n```\n{preview}\n```\n"

        return summary
