# -*- coding: utf-8 -*-
"""agent-ctx-guard — public surface."""

from .core import (
    CtxFolder,
    GENESIS_HASH,
    _canonical,
    _sha256,
    default_summary,
)

__version__ = "0.1.0"

__all__ = [
    "CtxFolder",
    "default_summary",
    "__version__",
]