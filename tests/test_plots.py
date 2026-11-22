import pytest
import logging

# from gnuplot_advanced import GnuplotSnippet, GnuplotController, interaction_demo, _flatten_to_tuple_of_strings  # public sees this. Must match gnuplot_advanced/__init__.el
from gnuplot_advanced.core import GnuplotSnippet, GnuplotController, interaction_demo, _flatten_to_tuple_of_strings  # developer deeper access

# ##############################################################
logger = logging.getLogger("test")
logger.setLevel(logging.DEBUG)  # Set default logging level # DEBUG, INFO, WARNING, ERROR
#
# Create a formatter and attach it to the handler
# formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
formatter = logging.Formatter("%(asctime)s: %(levelname)-8s:%(name)-12s:%(lineno)4d: %(message)s")
#
# Output to console:
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

#
# File handler for logging to a file (that keeps growing!):
# file_handler = logging.FileHandler("gnuplot_advanced.log")  # ouput to file
# file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)
# ##############################################################


@pytest.mark.skip(reason="Skip for now")  # decorator directly above function.
def test_flatten_to_tuple_of_strings():
    logger.debug("Args        \t= \"{}\"".format(_flatten_to_tuple_of_strings("Arg1", "Arg2", "Arg3")))
    logger.debug("Tuple       \t= \"{}\"".format(_flatten_to_tuple_of_strings(("Arg1", "Arg2", "Arg3"))))
    logger.debug("Lone String \t= \"{}\"".format(_flatten_to_tuple_of_strings("Arg1")))
    logger.debug("Tuple + Tuple, Lone String \t= \"{}\"".format(_flatten_to_tuple_of_strings(("Arg1", "Arg2", "Arg3") + ("Arg1", "Arg2", "Arg3"), "Arg1")))
    return


# @pytest.mark.skip(reason="Skip for now")  # decorator directly above function.
def test_snippets():
    gs1 = GnuplotSnippet()
    gs1.set_terminal_and_output('set term qt\noutput = ""')
    gs1.preplot("set terminal qt\nset terminal qt")  # test
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
    gs2 = GnuplotSnippet()
    gs2.set_terminal_and_output('set term qt')
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
    gc.preplot(gs1.preplot())
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
    return


@pytest.mark.skip(reason="Skip for now")  # decorator directly above function.
def test_run_script_available():
    # interaction_demo()
    pass


@pytest.mark.skip(reason="Skip for now")  # decorator directly above function.
def test_comment_out_pause():
    # interaction_demo()
    gc = GnuplotController(debug=True)
    gc.preplot('plot sin(x);pause -1 "Hello"; print("Goodbye")\npause mouse "This is a test"\npause 10\n', 'pause -1 "Second Line"')
    gc.close()
    #assert callable(run_script)
    #assert callable(run_script)


# test_snippets()
# if __name__ == "__main__":
#     test_snippets()
