__version__ = "0.1.0"

# This line defines what in core.py that is available to the public user
# User can then do "from gnuplot_advanced import GnuplotController"
from .core import GnuplotController, Gnuplot, escape_str, interaction_demo

# __all__ signals to IDEs and static tools what is available to the public.
__all__ = ["GnuplotController", "Gnuplot", "escape_str", "interaction_demo"] #"run_script"] # , "generate_temp_script"]
