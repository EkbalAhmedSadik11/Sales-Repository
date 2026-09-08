"""Display formatting helpers shared across screens/widgets."""

from datetime import datetime


def format_date(iso_str: str, fmt: str = "%d %B %Y") -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return iso_str
    return dt.strftime(fmt)


def format_datetime(iso_str: str, fmt: str = "%d %b %Y, %I:%M %p") -> str:
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str)
    except ValueError:
        return iso_str
    return dt.strftime(fmt)


def format_price(value: float, symbol: str = "৳") -> str:
    try:
        return f"{symbol}{float(value):,.2f}"
    except (TypeError, ValueError):
        return f"{symbol}0.00"


def format_signed_quantity(qty: int) -> str:
    return f"+{qty}" if qty > 0 else str(qty)


def next_product_code(last_code: str) -> str:
    """Generate the next sequential product code, e.g. P001 -> P002."""
    if not last_code:
        return "P001"
    prefix = "".join(c for c in last_code if c.isalpha()) or "P"
    digits = "".join(c for c in last_code if c.isdigit())
    width = len(digits) if digits else 3
    number = int(digits) + 1 if digits else 1
    return f"{prefix}{number:0{width}d}"
