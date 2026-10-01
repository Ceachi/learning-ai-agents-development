"""Guardrails module - Input validation and prompt injection detection."""
from dataclasses import dataclass

from .input_validation import ValidationResult, validate_input
from .prompt_injection import InjectionResult, ThreatLevel, check_injection


@dataclass(frozen=True, slots=True)
class GuardResult:
    """Combined guardrail check result."""

    safe: bool
    message: str | None = None
    validation: ValidationResult | None = None
    injection: InjectionResult | None = None


def guard(text: str, use_llm_injection: bool = True) -> GuardResult:
    """Run all guardrail checks on input text."""
    validation = validate_input(text)
    if not validation.valid:
        return GuardResult(
            safe=False,
            message=validation.message,
            validation=validation,
        )

    injection = check_injection(text, use_llm=use_llm_injection)
    if not injection.safe:
        return GuardResult(
            safe=False,
            message=injection.message,
            validation=validation,
            injection=injection,
        )

    return GuardResult(safe=True, validation=validation, injection=injection)


__all__ = [
    "GuardResult",
    "InjectionResult",
    "ThreatLevel",
    "ValidationResult",
    "check_injection",
    "guard",
    "validate_input",
]
