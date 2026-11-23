# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""Demo file for using GnuplotSnippets and GnuplotController
Note: You must have gnuplot installed on your system as an executable.
Usage: python -m gnuplot_snippets.demo
"""
import logging
import random

import pandas as pd

from gnuplot_snippets import (GnuplotController, GnuplotSnippets, escape_str,
                              next_datablock_counter)

# ##############################################################
logger = logging.getLogger("gnuplot_snippets")
# Output to console:
handler = logging.StreamHandler()
formatter = logging.Formatter(
    "%(asctime)s: %(levelname)-8s:%(name)-12s:%(lineno)4d: %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.ERROR)  # INFO, DEBUG, WARNING, ERROR
# ##############################################################


def velocity(t: float, coeff_a: float, coeff_b: float,
             coeff_c: float) -> float:
    """Dummy car performance."""
    return coeff_a * t**3 + coeff_b * t**2 + coeff_c * t


def acceleration(t: float, coeff_a: float, coeff_b: float,
                 coeff_c: float) -> float:
    """Dummy car performance."""
    return 3 * coeff_a * t**2 + 2 * coeff_b * t + coeff_c


def noisy_velocity(time_start: float, time_end: float, coeff_a: float,
                   coeff_b: float, coeff_c: float,
                   noise_level: float) -> list[tuple[float, float, float]]:
    """Create data time vs noisy velocity and smooth acceleration."""
    data: list[tuple[float, float, float]] = []
    n = 10
    delta_time = (time_end - time_start) / n
    for i in range(n + 1):
        t = i * delta_time
        noise = random.uniform(-noise_level, noise_level)
        vel = velocity(t, coeff_a, coeff_b, coeff_c) + noise
        accel = acceleration(t, coeff_a, coeff_b, coeff_c)
        data.append((t, vel, accel))
    return data


class Transport:
    """DEMO"""

    def __init__(self, name: str, time_start: float, time_end: float,
                 coeff_a: float, coeff_b: float, coeff_c: float,
                 noise_level: float):
        """Set up performance."""
        self.name = name
        self.time_start = time_start
        self.time_end = time_end
        self.coeff_a = coeff_a
        self.coeff_b = coeff_b
        self.coeff_c = coeff_c
        self.noise_level = noise_level
        self.velocity_performance = noisy_velocity(self.time_start,
                                                   self.time_end, self.coeff_a,
                                                   self.coeff_b, self.coeff_c,
                                                   self.noise_level)


class Car(Transport):
    """DEMO"""

    def __init__(self, name: str, time_start: float, time_end: float,
                 coeff_a: float, coeff_b: float, coeff_c: float,
                 noise_level: float):
        super().__init__(name, time_start, time_end, coeff_a, coeff_b, coeff_c,
                         noise_level)

    def gnuplot(self, show_name: bool = False) -> GnuplotSnippets:
        """Gnuplot snippet to plot this class to a pdf file or the screen.
        THIS CONTAINS ALL THE GNUPLOT COMMANDS TO RELEVANT TO PLOTTING A 'CAR'.
        YOU CAN USE THIS AS A TEMPLATE.
        
        The code below demonstrates the wide variety of ways to share the workflow
        and workload between Python and gnuplot.

        :param show_name: If True show the name in the key.
        """
        window_title = "Car Performance"
        pdf_filename = f'zJUNK-DEMOFILE-{self.name}.pdf'

        gs = GnuplotSnippets()

        # Snippet for pdfcairo plotfile-specific settings.
        gs.output_to_file(
            'set terminal pdfcairo enhanced size 5.0,5.0*0.7 lw 2.0',
            'set title',  # clear title
            'set xlabel "Time {/:Italic t} [s]"; set format x "%h"',  # plotfile values
            'set ylabel "Velocity {/:Italic v} [m/s]"; set format y "%0.1f"',
            'set y2label "Acceleration {/Symbol a} [m/s^2]"; set format y2 "%h"',
            filename=pdf_filename,
        )

        # Snippet for screen-specific settings that undo plotfile settings above:
        gs.output_to_screen(
            f'set terminal qt title "{window_title}"',
            # f'set terminal windows title "{window_title}"', # UNCOMMENT FOR WINDOWS
            f'set title "Preview of {escape_str(pdf_filename)}"',
            'set xlabel "Time [s]"; set format x',
            'set ylabel "Velocity [m/s]"; set format y "%0.1f"',
            'set y2label "Acceleration [m/s^2]"; set format y2',
        )

        # Adds a datablock to preplot snippet:
        # Here python generates the curve.  So we use a gnuplot datablock for display.
        # Create a nicely formatted datablock and put it in the preplot snippet:
        datablock_name = f'$DataBlock_CarData{next_datablock_counter()}'  # unique datablock name
        df = pd.DataFrame(
            self.velocity_performance,
            columns=("Time_s", "Velocity_mps",
                     "SmoothedAcceleration_mpsps"))  # type: ignore
        column_formats: dict[str, str] = {
            "Time_s": "9.2f",
            "Velocity_mps": "12.3f",
            "SmoothedAcceleration_mpsps": "26.5g"
        }  # human-readable formatting for datablock without compromising plot precision
        #  OR if we want to treat all columns the same and they are all floats just do: df = df.map("{:15.3f}".format)
        gs.preplot_add_datablock(df,
                                 datablock_name=datablock_name,
                                 column_formats=column_formats)

        # Append more to the preplot snippet.
        # Other settings [using the option of one long string for several gnuplot set commands]:
        # Note: Every call to preplot() must appends more commands to the preplot snippet.
        # This applies to all the snippet methods.
        # To see the preplot snippet: print gs.preplot()
        gs.preplot("""
        # Setting up gnuplot:
        set grid
        set xrange[0:100]
        set yrange[0:*]; set y2range[0:*]
        set ytics nomirror; set y2tics
        set key left top
        """)

        # Append more to the preplot snippet.
        # Define some variables and functions [this time using separate args for the commands]:
        name = self.name + " " if show_name else ""
        gs.preplot(
            # It's usually not a great idea to use gnuplot variables because they might get overwritten by a later snippet!..
            f'gnuplot_coeff_a = {self.coeff_a}',
            f'# print( sprintf("Gnuplot print(): Demo: {self.name}: gnuplot_coeff_a = %.6g", gnuplot_coeff_a) )',  # get gnuplot to report coeff_a value
            f'# fAcceleration(t) = 3.*{self.coeff_a}*t**2 + 2.*{self.coeff_b}*t + {self.coeff_c}',  # you can do this..
            'fVelocity(t,coeff_a,coeff_b,coeff_c) = coeff_a*t**3 + coeff_b*t**2 + coeff_c*t',  # but this is probably safer
            'fAcceleration(t,coeff_a,coeff_b,coeff_c) = 3.*coeff_a*t**2 + 2.*coeff_b*t + coeff_c',
        )

        # Append more to the preplot snippet.
        # Add a gnuplot label to the plot:
        gs.preplot(
            f'eval sprintf("set label \\"{name}Label: coeff_a = {self.coeff_a:.3g}\\" at 2,%f", '
            f'fVelocity(80,{self.coeff_a},{self.coeff_b},{self.coeff_c}))', )

        # Append more to the preplot snippet.
        # Set title:
        gs.preplot(f'set title "Performance Characteristics for {self.name}."')

        # Add plot elements mixing gnuplot datablocks and gnuplot user functions:
        # If python generates the curves, use datablocks.  If you are OK with gnuplot creating the
        # curve use gnuplot functions.
        gs.plot_elements(
            f'{datablock_name} using 1:2 axis x1y1 smooth mcs title "{name}Velocity Spline" with lines',
            f'{datablock_name} using 1:2 axis x1y1 title "{name}Velocity Pts" with points',
            f'{datablock_name} using 1:3 axis x1y2 title "{name}Smooth Acceleration Pts" with points ps 1.3',
            f'fVelocity(x,{self.coeff_a},{self.coeff_b},{self.coeff_c}) axis x1y1 title "{name}Smoothed Velocity" with lines',
            f'fAcceleration(x,{self.coeff_a},{self.coeff_b},{self.coeff_c}) axis x1y2 title "{name}Smooth Acceleration" with lines',
        )
        # Note when plotting we can use Python's array slicing capabilities to just plot some of the above:
        # e.g. gc.plot(gs.plot_elements()[:3])

        # Set/append to the postplot snippet:
        gs.postplot('unset label')  # cleanup commands
        return gs  # gs contains everything to print self.


def main() -> None:
    print("Running gnuplot_snippets demo...")

    # ##############################################################
    # EXAMPLE USAGE
    print(
        """Note: During the demo print messages from Python and gnuplot are interlaced
      and the order may not be predictable.  This can't be avoided and is not usually a problem.
      It's helpful to preceed print statements from each with a tag to indicate
      if it came from your python code or gnuplot script, e.g. "Demo:" or "Gnuplot:"
      so you know the source.
    """)

    # ==============================================================
    # NOTE: The demo does many plots building a single gnuplot scriptfile as
    # it goes.  In this case the snippets were contructed so we don't
    # need a gnuplot 'reset' between plots.

    demo_script_filename = "zDEMO-GNUPLOT-SCRIPTFILE.gp"  # You must choose a safe name for a file here!

    gc = GnuplotController(debug=False, script_filename=demo_script_filename)

    # ==============================================================
    # DEMO 1: USING SNIPPETS
    # --------------------------------------------------------------
    # car1 = Car("Car1", 0, 100, 0.0001, 0.00001, 0.01, 3.0)
    # car2 = Car("Car2", 0, 120, 0.00015, 0.00002, 0.02, 2.0)
    car1 = Car("Car1", 0, 100, 0.00005, 0.000005, 0.005, 1.5)
    car2 = Car("Car2", 0, 120, 0.00007, 0.000001, 0.01, 1.0)
    # Get all snippets for each Car:
    gs_car1 = car1.gnuplot()
    gs_car2 = car2.gnuplot()
    #
    print("==============================================================")
    print("Demo: Plot Car1 to screen:")
    # We send all the relevant preplot info to the controller in the correct sequence:
    gc.preplot(gs_car1.preplot(), gs_car1.output_to_screen(), show_source=True)
    # Plot all the plot elements of Car1:
    gc.plot(gs_car1.plot_elements(), pause=3)  # waits 3s
    # Cleanup
    gc.postplot(gs_car1.postplot())
    #
    print("Demo: Publishing Car1 to file:")
    # Before plotting now send output to file preplot command(s):
    gc.preplot(gs_car1.output_to_file(), show_source=True)
    # Plot to file:
    gc.plot(gs_car1.plot_elements(), show_output=True, pause=0)  # no pause
    # Cleanup:
    gc.postplot(gs_car1.postplot(), 'set output')  # play safe

    print("==============================================================")
    print("Demo: Plot Car2 to screen:")
    gc.preplot(gs_car2.preplot(), gs_car2.output_to_screen(), show_source=True)
    gc.plot(gs_car2.plot_elements(), pause=4)  # waits 4s
    gc.postplot(gs_car2.postplot())

    print("==============================================================")
    print("Demo: Plot both cars to screen:")
    # Plot both Cars on the one graph:
    gs_car1 = car1.gnuplot(show_name=True)
    gs_car2 = car2.gnuplot(show_name=True)

    # Send preplot info for each car and tweak title etc for two cars instead:
    # Note: the command order is the order sent to gnuplot.
    # Thus, as in a normal gnuplot scripts, recent set commands overwrite older ones.
    gc.preplot(gs_car1.preplot(),
               gs_car2.preplot(),
               'set title "Two Cars"',
               'set key left top',
               show_source=True)
    # Plot both cars:
    gc.plot(gs_car1.plot_elements(), gs_car2.plot_elements(),
            pause=-1)  # -1 is wait for keypress
    # Cleanup both cars ready for next demo:
    gc.postplot(gs_car1.postplot(), gs_car2.postplot())

    # ==============================================================
    # DEMO 2: MULTIPLOT:
    # --------------------------------------------------------------
    print("==============================================================")
    print("Demo: Multiplot example:")
    # Multiplot is a more complex case and needs a special methods
    # gc.premultiplot_to_screen() OR gc.premultiplot_to_file() and gc.postmultiplot():
    # Note: Once premultiplot() is called, all 'set terminal' commands in snippets are blocked until an
    # 'unset multiplot' is sent by calling postmultiplot().
    gc.premultiplot_to_screen(
        'set terminal qt size 800,500 title "Multiplot"',
        '# set terminal windows size 800,500 title "Multiplot"',  # uncomment for Windows
        'set multiplot layout 1,2',
        show_source=True)
    # Note: Any 'set terminal ' commands in these snippets are blocked for now.
    gc.preplot(gs_car1.preplot(),
               gs_car1.output_to_screen(),
               'set y2range[0:50]',
               'set title "Car 1"',
               show_source=True)
    gc.plot(gs_car1.plot_elements(), pause=0)  # don't pause
    gc.postplot(gs_car1.postplot())
    #
    gc.preplot(gs_car2.preplot(),
               gs_car2.output_to_screen(),
               'set y2range[0:50]',
               'set title "Car 2"',
               show_source=True)
    gc.plot(gs_car2.plot_elements(), pause=-1)  # stop on last plot
    gc.postplot(gs_car2.postplot())
    #
    gc.postmultiplot()  # turn off multiplotting.

    # ==============================================================
    # DEMO 3: python array slicing to see some curves from plot_elements but not all:
    # --------------------------------------------------------------
    print("==============================================================")
    print("Demo: Plot Car1 - some curves only:")
    title = "Some curves of Car 1\\nPress \\\"m\\\" to try the mouse\\\\_measure functionality."
    gc.preplot(
        gs_car1.preplot(),
        gs_car1.output_to_screen(),
        f'set title "{title}"',  # put this last to override any other titles
        show_source=True)
    # Plot some elements of available plot_elements() list:
    gc.plot(gs_car1.plot_elements()[0],
            gs_car1.plot_elements()[-2:],
            pause="mouse_measure")
    gc.postplot(gs_car1.postplot())

    # ==============================================================
    # DEMO 4 - NO SNIPPETS
    # Note: In this example we skip using GnuplotSnippet and send commands directly with GnuplotController:
    print("==============================================================")
    print("Demo: Demo of raw interface to GnuplotController:")
    title = "Plot without snippets using GnuplotController only."

    # Note: Generally args can be one long gnuplot script string OR one line per arg OR a mix:
    gc.preplot('reset')
    gc.preplot(  # each call to preplot() sends more commands
        """
      set angle degrees
      fSin(x,a) = a*x + sin(x)
      fCos(x,a) = a*x + cos(x)
      set xrange[-30:360*3]
      set xlabel "x [deg]"
      set ylabel "y [-]"
      set label "Hello!" at graph 0.1, graph 0.7
      set key left top
        """,
        f'set title "{title}"',
        show_source=True)
    # One gnuplot <plot-element> per arg:
    gc.plot('fSin(x, 5./1440.)',
            'fCos(x, 4./1440.)',
            'sin(x) with lines lw 2.0 dt 2',
            pause=-1)
    gc.postplot("unset label")

    # ==============================================================
    # DONE!
    gc.close()

    print("\n==============================================================")
    print(
        f'The preceding code has generated one long gnuplot script file "{demo_script_filename}"\n'
        'The file contains useful links back to the python source code.\n\n'
        f'Try running the demo script file directly using "gnuplot {demo_script_filename}"\n'
        "This is very useful for debugging gnuplot commands.\n"
        "Note however, the script has NO prompts, such as \"Press Enter to continue\"!\n"
    )


if __name__ == "__main__":
    main()
