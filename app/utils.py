"""Utility functions: formatting, colors, constants."""

# DGB brand colors
COLORS = {
    "primary": "#1351B4",
    "positive": "#168821",
    "neutral": "#636363",
    "negative": "#E52207",
    "background": "#F0F2F5",
}

SENTIMENT_COLORS = {
    "positive": COLORS["positive"],
    "neutral": COLORS["neutral"],
    "negative": COLORS["negative"],
}

DOW_LABELS = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def fmt_number(n: float, decimals: int = 0) -> str:
    """Format number with thousand separators (Brazilian style)."""
    if decimals == 0:
        return f"{int(n):,}".replace(",", ".")
    return f"{n:,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def fmt_pct(n: float, decimals: int = 1) -> str:
    """Format as percentage."""
    return f"{n:+.{decimals}f}%"


def fmt_delta(current: float, previous: float) -> str:
    """Format delta between two values as percentage."""
    if previous == 0:
        return "N/A"
    delta = (current - previous) / previous * 100
    return fmt_pct(delta)
