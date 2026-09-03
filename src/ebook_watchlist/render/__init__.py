"""Renderers for the Digest model. One model in, several formats out (ADR 15)."""

from .html import render_html
from .text import render_text

__all__ = ["render_html", "render_text"]
