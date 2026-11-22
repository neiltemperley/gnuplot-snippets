"""Module setup."""

__version__ = "0.1.0"

# User can then do "from gnuplot_advanced import GnuplotController, GnuplotSnippet"
from .snippet import GnuplotSnippet, escape_str, format_dataframe, next_datablock_counter
from .controller import GnuplotController

# __all__ signals to IDEs and static tools what is available to the public.
__all__ = [
    "GnuplotController",
    "GnuplotSnippet",
    "escape_str",
    "format_dataframe",
    "next_datablock_counter",
]
