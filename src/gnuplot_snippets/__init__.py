# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""Composable gnuplot snippets for Python.

Typical use::
    from gnuplot_snippets import GnuplotController, GnuplotSnippet, escape_str, format_dataframe, next_datablock_counter
"""
from .snippets import GnuplotSnippets, escape_str, format_dataframe, next_datablock_counter
from .controller import GnuplotController

# __all__ defines the public API for "from gnuplot_snippets import *"
# and signals the public names to IDEs and static tools.
__all__ = [
    "GnuplotController",
    "GnuplotSnippets",
    "escape_str",
    "format_dataframe",
    "next_datablock_counter",
]
