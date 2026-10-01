"""Input validation checks."""
import re
from dataclasses import dataclass

from app.config import get_settings

_settings = get_settings()

# Patterns
_URL_RE = re.compile(
    r'https?://[^\s<>"{}|\\^`\[\]]+'
    r'|www\.[^\s<>"{}|\\^`\[\]]+'
    r'|[a-zA-Z0-9.-]+\.(com|org|net|ro|eu|io|dev|app|ai)[^\s]*',
    re.IGNORECASE,
)
_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', re.IGNORECASE)
_CONTROL_CHARS_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f]')


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    message: str | None = None


def validate_input(
    text: str,
    max_chars: int | None = None,
    max_words: int | None = None,
    block_urls: bool | None = None,
    block_emails: bool | None = None,
) -> ValidationResult:
    """Validate user input against configured rules."""
    max_chars = max_chars if max_chars is not None else _settings.guardrail_max_chars
    max_words = max_words if max_words is not None else _settings.guardrail_max_words
    block_urls = block_urls if block_urls is not None else _settings.guardrail_block_urls
    block_emails = block_emails if block_emails is not None else _settings.guardrail_block_emails

    if not text or not text.strip():
        return ValidationResult(False, "Întrebarea nu poate fi goală.")

    text = text.strip()

    if _CONTROL_CHARS_RE.search(text):
        return ValidationResult(False, "Textul conține caractere invalide.")

    if len(text) > max_chars:
        return ValidationResult(False, f"Text prea lung ({len(text)}/{max_chars} caractere).")

    word_count = len(text.split())
    if word_count > max_words:
        return ValidationResult(False, f"Prea multe cuvinte ({word_count}/{max_words}).")

    if block_urls and _URL_RE.search(text):
        return ValidationResult(False, "URL-urile nu sunt permise.")

    if block_emails and _EMAIL_RE.search(text):
        return ValidationResult(False, "Adresele email nu sunt permise.")

    return ValidationResult(True)
