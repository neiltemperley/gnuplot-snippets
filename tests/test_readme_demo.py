# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""
Test the code given in the README.md
Usage:
 python -m tests.test_readme_demo
 # OR but beware pytest mucks up interaction!
 pytest -s 
"""
import logging

from gnuplot_snippets import GnuplotController, GnuplotSnippets

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


# ##############################################################


class Car:

    def __init__(self, name, a, b, c):
        self.name, self.a, self.b, self.c = name, a, b, c

    def gnuplot(self) -> GnuplotSnippets:
        gs = GnuplotSnippets()
        # Append to output_to_screen() snippet:
        gs.output_to_screen(
            'set terminal qt title "Car Performance"',
            'set xlabel "Time [s]"; set format x',
            'set ylabel "Velocity [m/s]"; set format y "%0.1f"',
            'set y2label "Acceleration [m/s^2]"; set format y2',
            'set ytics nomirror; set y2tics',
            show_source=True)  # add source marker to script file
        gs.preplot('fVelocity(t,a,b,c) = a*t**3 + b*t**2 + c*t',
                   'fAcceleration(t,a,b,c) = 3.*a*t**2 + 2.*b*t + c',
                   f'set title "Performance for {self.name}"',
                   show_source=True)
        gs.plot_elements(
            f'fVelocity(x,{self.a},{self.b},{self.c}) title "{self.name}" with lines',
            f'fAcceleration(x,{self.a},{self.b},{self.c}) axis x1y2 title "{self.name} Acceleration" with lines',
        )
        gs.postplot('unset label')
        return gs


# @pytest.mark.skip(reason="Skip for now")
def test_quick_example():
    gc = GnuplotController(script_filename="my_script.gp")
    gs = Car("Car1", 0.01, 0.0001, 0.1).gnuplot()

    # Note: Args to gc.preplot() are snippets or gnuplot commands.
    #       gs.preplot() returns the preplot() snippet string.
    gc.preplot(gs.preplot(), "set xrange[0:15]", "set y2range[0:*]",
               gs.output_to_screen())
    gc.plot(gs.plot_elements(), pause=4)  # wait 4s

    # Change title and repeat plot with interactive measurement:
    gc.preplot(
        'set title "Interactive Demo. \\nClick in this window, press \'m\' key, then click two points."'
    )
    gc.plot(gs.plot_elements(), pause="mouse_measure")  # interactive
    gc.postplot(gs.postplot())
    gc.close()


# ##############################################################
if __name__ == "__main__":
    """Run with
        python -m tests.test_readme_demo
    to just test these methods."""
    enable_debug_logging(level=logging.DEBUG)
    test_quick_example()
    #
