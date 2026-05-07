"""Shared matplotlib style for project notebooks and analyses.

Call `apply()` once at the top of a notebook (or analysis script) to get consistent fonts,
sizing, and palette across charts. Per-signal colors come from `signal_color()`.
"""

from __future__ import annotations

import matplotlib as mpl
import matplotlib.pyplot as plt

# Single source of truth for per-signal colors. Picked so each signal class has a
# distinguishable hue and so leading vs counter signals read as warm vs cool at a glance.
SIGNAL_COLORS: dict[str, str] = {
    "yoga_studios": "#d62728",
    "specialty_coffee": "#8c564b",
    "wine_bars": "#9467bd",
    "pilates_studios": "#e377c2",
    "auto_repair": "#1f77b4",
    "print_shops": "#17becf",
    "whole_foods_openings": "#2ca02c",
}

CLASS_COLORS: dict[str, str] = {
    "leading": "#d62728",
    "counter": "#1f77b4",
    "anchor": "#2ca02c",
}

DEFAULT_FIGSIZE = (10, 4)
DEFAULT_DPI = 120


def apply() -> None:
    mpl.rcParams.update(
        {
            "figure.figsize": DEFAULT_FIGSIZE,
            "figure.dpi": DEFAULT_DPI,
            "savefig.dpi": DEFAULT_DPI,
            "font.size": 10,
            "axes.titlesize": 11,
            "axes.labelsize": 10,
            "legend.fontsize": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.alpha": 0.3,
            "axes.axisbelow": True,
        }
    )


def signal_color(signal_name: str) -> str:
    """Per-signal color, with a stable fallback so unknown signals don't crash a chart."""
    return SIGNAL_COLORS.get(signal_name, "#7f7f7f")


def class_color(signal_class: str) -> str:
    return CLASS_COLORS.get(signal_class, "#7f7f7f")
