"""Centralized input validation.

Every validator raises ValidationError with a short, user-friendly message
(no stack traces / internal details) so screens can catch one exception type
and show the message text directly in a dialog or snackbar.
"""


class ValidationError(Exception):
    pass


def require_non_empty(value: str, field_name: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValidationError(f"{field_name} is required.")
    return value


def parse_positive_int(value, field_name: str, allow_zero: bool = True) -> int:
    try:
        parsed = int(str(value).strip())
    except (ValueError, TypeError):
        raise ValidationError(f"{field_name} must be a whole number.")
    if parsed < 0 or (parsed == 0 and not allow_zero):
        raise ValidationError(f"{field_name} must be {'zero or greater' if allow_zero else 'greater than zero'}.")
    return parsed


def parse_price(value, field_name: str = "Price") -> float:
    value = (str(value).strip() if value is not None else "")
    if value == "":
        return 0.0
    try:
        parsed = float(value)
    except ValueError:
        raise ValidationError(f"{field_name} must be a valid number.")
    if parsed < 0:
        raise ValidationError(f"{field_name} cannot be negative.")
    return round(parsed, 2)


def validate_pin_format(pin: str) -> str:
    pin = (pin or "").strip()
    if not pin.isdigit() or not (4 <= len(pin) <= 8):
        raise ValidationError("PIN must be 4 to 8 digits.")
    return pin
