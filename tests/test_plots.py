# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""Usage:
 python -m tests.test_plots
 # OR but beware pytest mucks up interaction!
 pytest -s 
"""
import logging

import pytest
from gnuplot_snippets import (GnuplotController, GnuplotSnippets)
import gnuplot_snippets
from gnuplot_snippets.snippets import (_flatten_to_tuple_of_strings)
from gnuplot_snippets.demo import main as demo

logger = logging.getLogger("gnuplot_snippets")


def enable_debug_logging(level=logging.DEBUG):
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s: %(levelname)-8s:%(name)-12s:%(lineno)4d: %(message)s"
        ))
    log = logging.getLogger("gnuplot_snippets")
    log.addHandler(handler)
    log.setLevel(level)


# @pytest.mark.skip(reason="Skip for now")
def test_flatten_to_tuple_of_strings():
    enable_debug_logging(level=logging.DEBUG)
    logger.debug("Args        \t= \"{}\"".format(
        _flatten_to_tuple_of_strings("Arg1", "Arg2", "Arg3")))
    logger.debug("Tuple       \t= \"{}\"".format(
        _flatten_to_tuple_of_strings(("Arg1", "Arg2", "Arg3"))))
    logger.debug("Lone String \t= \"{}\"".format(
        _flatten_to_tuple_of_strings("Arg1")))
    logger.debug("Tuple + Tuple, Lone String \t= \"{}\"".format(
        _flatten_to_tuple_of_strings(
            ("Arg1", "Arg2", "Arg3") + ("Arg1", "Arg2", "Arg3"), "Arg1")))
    assert True
    return


# @pytest.mark.skip(reason="Skip for now")  # decorator directly above function.
def test_snippets():
    gs1 = GnuplotSnippets()
    gs1.output_to_screen("set term qt")
    gs1.preplot("""
    set angle degrees
    set xrange[0:360]
    set xlabel "x"
    """)
    gs1.plot_elements('sin(x)')
    gs1.postplot(defaults=True)
    logger.debug("gs1.plot_elements \t= \"{}\"".format(gs1.plot_elements()))
    # print(f"gss = {gs1}")
    #
    gs2 = GnuplotSnippets()
    gs2.output_to_screen('set term qt')
    gs2.preplot("""
    set angle degrees
    set xrange[0:360]
    set xlabel "x"
    """)
    gs2.plot_elements('0.5*cos(x)')
    gs2.postplot(defaults=True)
    # print(f"gss2 = {gs2}")
    #
    gc = GnuplotController(debug=True)
    gc.preplot(gs1.output_to_screen(), gs1.preplot())
    print(f"gs1.plot_elements() = {gs1.plot_elements()}")
    gc.plot(gs1.plot_elements(), plot_and_ranges="plot", pause=-1)
    gc.postplot(gs1.postplot())
    #
    gc.plot(gs2.plot_elements(), pause=3)
    gc.postplot(gs2.postplot())
    #
    gc.preplot("set yrange[-3:3]")
    gc.plot(gs1.plot_elements() + gs2.plot_elements(), "tan(x)", pause=2)
    gc.close()
    assert True
    return


#@pytest.mark.skip(reason="Skip for now")
def test_demo():
    demo()  # demo file provided with code
    pass


@pytest.mark.skip(reason="Skip for now")
def test_comment_out_pause():
    # interaction_demo()
    gc = GnuplotController(debug=True)
    gc.preplot(
        'plot sin(x);pause -1 "Hello"; print("Goodbye")\npause mouse "This is a test"\npause 10\n',
        'pause -1 "Second Line"')
    gc.close()
    assert True


@pytest.mark.skip(reason="Skip for now")
def test_GnuplotController_example():
    """Cut and paste from example in code:"""
    with GnuplotController(script_filename="debug.gp") as gc:
        gc.preplot('set title "sine curve"', 'set angle degrees',
                   'set xrange [-360:360]')
        gc.plot("sin(x)", pause=-1)


@pytest.mark.skip(reason="Skip for now")
def test_GnuplotController_plot_example():
    """Cut and paste from example in code:"""
    gc = GnuplotController()
    gc.preplot('set title "Some curves"', 'set angle degrees')
    # gc.plot(gs1.plot_elements(), gs2.plot_elements(), pause=-1) # e.g. with GnuplotSnippets gs1 and gs2
    gc.plot("sin(x)", "cos(x)", pause=4)  # without GnuplotSnippets
    gc.plot("sin(x)", "tan(x)", plot_and_ranges="plot [-70:70]",
            pause=5)  # without GnuplotSnippets
    gc.preplot("unset angle")
    # ..other GnuplotController commands
    gc.close()


#@pytest.mark.skip(reason="Skip for now")
def test_gnuplot_error():
    try:
        with GnuplotController(
                script_filename="zTEST-GNUPLOT_ERROR_script.gp") as gc:
            gc.preplot("set angle junk")
            gc.close()
    except Exception as e:
        print(type(e).__name__, e)
    assert True


# ##############################################################
if __name__ == "__main__":
    """Run with
        python -m tests.test_plots
    to just test these methods."""
    enable_debug_logging(level=logging.DEBUG)
    #
    test_GnuplotController_example()
    test_GnuplotController_plot_example()
    # test_snippets()
    test_gnuplot_error()
