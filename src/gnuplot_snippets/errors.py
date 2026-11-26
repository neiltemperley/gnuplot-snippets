# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""Flexible unrestricted tools for Gnuplot integration with Python."""


class GnuplotError(Exception):
    """Base class for exceptions in the gnuplot plotting library."""


class GnuplotNotFoundError(GnuplotError, RuntimeError):
    """Raised when the gnuplot executable cannot be found."""
