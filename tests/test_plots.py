import pytest

from gnuplot_advanced import Gnuplot, GnuplotController, interaction_demo  # public sees this. Must match gnuplot_advanced/__init__.el
# from gnuplot_advanced.core import Gnuplot, GnuplotController, interaction_demo  # developer deeper access

def test_run_script_available():
    # interaction_demo()
    pass


def test_comment_out_pause():
    # interaction_demo()
    gc = GnuplotController(debug=True)
    gc.preplot('plot sin(x);pause -1 "Hello"; print("Goodbye")\npause mouse "This is a test"\npause 10\n',
               'pause -1 "Second Line"')
    gc.close()
    #assert callable(run_script)
