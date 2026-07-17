"""Dependency-free FIT session and lap parsing."""

from .parser import parse_fit_bytes, parse_fit_export

__all__ = ["parse_fit_bytes", "parse_fit_export"]
