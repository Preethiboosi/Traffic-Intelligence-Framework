"""
utils.py — Shared display and formatting utilities.
"""


def format_pct(value: float, decimals: int = 1) -> str:
    """Format a 0–1 float as a percentage string."""
    return f"{value * 100:.{decimals}f}%"


def recommendation_color(recommendation: str) -> str:
    """Hex color for a SCALE / MONITOR / PAUSE recommendation."""
    return {
        "PAUSE":   "#EF4444",
        "MONITOR": "#F59E0B",
        "SCALE":   "#10B981",
    }.get(recommendation, "#6B7280")


def flag_color(flag_severity: str) -> str:
    """Hex color for flag severity."""
    return {
        "severe":  "#EF4444",
        "warning": "#F59E0B",
        "none":    "#10B981",
    }.get(flag_severity, "#9CA3AF")


def score_label(score: float) -> str:
    """Simple text badge for a quality score."""
    if score >= 75:
        return "Strong"
    if score >= 45:
        return "Acceptable"
    return "Weak"
