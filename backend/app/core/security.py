# backend/app/core/security.py

from __future__ import annotations
from typing import Optional
import re
import html
import os

try:
    import magic  # python-magic
except Exception:  # pragma: no cover
    magic = None

MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

FILENAME_SAFE_RE = re.compile(r"^[A-Za-z0-9._-]{1,150}$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InputValidator:
    @staticmethod
    def sanitize_filename(filename: str) -> str:
        # remove paths and keep basename
        base = os.path.basename(filename)
        if not FILENAME_SAFE_RE.match(base):
            # replace unsafe with underscore
            safe = re.sub(r"[^A-Za-z0-9._-]", "_", base)[:150]
            return safe or "file.pdf"
        return base

    @staticmethod
    def validate_pdf_file(file_content: bytes, filename: str) -> tuple[bool, Optional[str]]:
        # size check
        if len(file_content) > MAX_FILE_SIZE_BYTES:
            return False, f"Arquivo maior que {MAX_FILE_SIZE_MB}MB"
        # magic bytes check (PDF starts with %PDF)
        if not file_content.startswith(b"%PDF"):
            # fallback to python-magic when available
            if magic:
                mime = magic.from_buffer(file_content, mime=True)
                if mime != "application/pdf":
                    return False, "Tipo de arquivo inválido, apenas PDF"
            else:
                return False, "Tipo de arquivo inválido, apenas PDF"
        # basic trailer presence
        if b"%%EOF" not in file_content[-2048:]:
            return False, "Arquivo PDF inválido (EOF ausente)"
        # filename sanitization
        safe_name = InputValidator.sanitize_filename(filename)
        if safe_name != filename:
            # not an error, but inform caller
            return True, None
        return True, None

    @staticmethod
    def sanitize_text_input(text: str, max_len: int = 500) -> str:
        text = text or ""
        text = text.strip()[:max_len]
        return html.escape(text)

    @staticmethod
    def validate_email(email: str) -> bool:
        return bool(EMAIL_RE.match(email or ""))

    @staticmethod
    def validate_password_strength(password: str) -> bool:
        return bool(PASSWORD_RE.match(password or ""))

    @staticmethod
    def validate_numeric_id(value: int, min_value: int = 1, max_value: int = 10_000_000) -> bool:
        try:
            ivalue = int(value)
        except Exception:
            return False
        return min_value <= ivalue <= max_value
