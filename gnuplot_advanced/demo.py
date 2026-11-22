"""Demo file for using GnuplotSnippets and GnuplotController"""
import logging
import random
import pandas as pd
from gnuplot_advanced.snippet import escape_str
from gnuplot_advanced import GnuplotController, GnuplotSnippet

# from pprint import pformat, pprint
# from objexplore import explore  # type: ignore # e.g. explore(object) # VERY GOOD pip install objexplore
# # ##############################################################
# logger = logging.getLogger("gnuplot_advanced")
# logger.setLevel(logging.DEBUG)  # Set default logging level # DEBUG, INFO, WARNING, ERROR
# #
# # Create coeff_a formatter and attach it to the handler
# # formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
# formatter = logging.Formatter("%(asctime)s: %(levelname)-8s:%(name)-12s:%(lineno)4d: %(message)s")
# #
# # Output to console:
# console_handler = logging.StreamHandler()
# console_handler.setLevel(logging.DEBUG)
# console_handler.setFormatter(formatter)
# logger.addHandler(console_handler)

# ##############################################################

_gnuplot_datablock_counter: int = 0  # very useful to ensure unique datablock names.


def next_datablock_counter() -> int:
    """Global counter for Gnuplot datablock names to ensure unique names.
    Very useful to add to your code."""
    global _gnuplot_datablock_counter
    _gnuplot_datablock_counter += 1
    return _gnuplot_datablock_counter


def velocity(time: float, coeff_a: float, coeff_b: float, coeff_c: float) -> float:
    """Dummy performance."""
    return coeff_a * time**3 + coeff_b * time**2 + coeff_c * time


def acceleration(time: float, coeff_a: float, coeff_b: float, coeff_c: float) -> float:
    """Dummy performance."""
    return coeff_a * time**2 + coeff_b * time + coeff_c


def noisy_velocity(time_start: float, time_end: float, coeff_a: float, coeff_b: float, coeff_c: float, noise_level: float) -> list[tuple[float, float, float]]:
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
    """Demo car."""

    def __init__(self, name: str, time_start: float, time_end: float, coeff_a: float, coeff_b: float, coeff_c: float, noise_level: float):
        """Set up performance."""
        self.name = name
        self.time_start = time_start
        self.time_end = time_end
        self.coeff_a = coeff_a
        self.coeff_b = coeff_b
        self.coeff_c = coeff_c
        self.noise_level = noise_level
        self.velocity_performance = noisy_velocity(self.time_start, self.time_end, self.coeff_a, self.coeff_b, self.coeff_c, self.noise_level)


class Car(Transport):
    """Car."""

    def __init__(self, name: str, time_start: float, time_end: float, coeff_a: float, coeff_b: float, coeff_c: float, noise_level: float):
        super().__init__(name, time_start, time_end, coeff_a, coeff_b, coeff_c, noise_level)

    def gnuplot(self, show_name: bool = False) -> GnuplotSnippet:
        """Plot coeff_a car differently to other kinds of transport.

        The code below demonstrates the wide variety of ways to share the workflow and workload between Python and
        Gnuplot.  I'd avoid making the Gnuplot code too complex.

        :param show_name: If True show the name in the key.
        """
        window_title = "Car Performance"
        latex_filename = f'zJUNK-DEMOFILE-{self.name}.tex'
        gs = GnuplotSnippet()
        # Plotfile specific settings
        gs.preplot_to_file(
            f'set terminal cairolatex color pdf size 5.0,5.0*0.7 lw 2.0',
            latex_filename,
            'set title',  # clear title
            'set xlabel "Time $t$ [s]"; set format x "$%h$"',  # plotfile values
            'set ylabel "Velocity $v$ [m/s]"; set format y "$%0.1f$"',
            'set y2label "Acceleration $\\\\alpha$ [m/s^2]"; set format y2 "$%h$"',
        )
        # Terminal specific settings that undo plotfile settings above:
        gs.preplot_to_screen(
            f'set terminal qt title "{window_title}"',
            f'set title "{escape_str(latex_filename)}"',
            'set xlabel "Time [s]"; set format x',  # reset to screen values
            'set ylabel "Velocity [m/s]"; set format y "%0.1f"',
            'set y2label "Acceleration [m/s^2]"; set format y2',
        )
        # Create nicely formatted datablock:
        datablock_name = f'$DataBlock_Car{next_datablock_counter()}'  # unique datablock name
        df = pd.DataFrame(self.velocity_performance, columns=("Time_s", "Velocity_mps", "SmoothedAcceleration_mpsps"))  # pyright: ignore
        format_dict = {
            "Time_s": "9.2f",
            "Velocity_mps": "12.3f",
            "SmoothedAcceleration_mpsps": "26"
        }  # human-readable formatting for datablock without compromising plot precision
        #  OR if we want to treat all columns the same just do: df = df.map("{:15.3f}".format)
        gs.preplot_add_datablock(df, datablock_name=datablock_name, format_dict=format_dict)
        # Other settings:
        gs.preplot("""
        # Setting up Gnuplot:
        set grid
        set xrange[0:100]
        set yrange[*:*]; set y2range[*:*]
        set ytics nomirror
        set y2tics
        set key left top
        """)
        # Define some variables and functions:
        name = self.name + " " if show_name else ""
        gs.preplot(
            # Usually not a great idea to use Gnuplot variables because they might get overwritten by a later snippet!..
            f'gnuplot_coeff_a = {self.coeff_a}',
            f'print( sprintf("Gnuplot: Demo: {self.name}: gnuplot_coeff_a = %.6g", gnuplot_coeff_a) )',  # get Gnuplot to report coeff_a value
            f'# fVelocity(t) = {self.coeff_a}*t**2 + {self.coeff_b}*t + {self.coeff_c}',  # your can do this
            'fVelocity(t,coeff_a,coeff_b,coeff_c) = coeff_a*t**3 + coeff_b*t**2 + coeff_c*t',  # but this is probably safer
            'fAcceleration(t,coeff_a,coeff_b,coeff_c) = coeff_a*t**2 + coeff_b*t + coeff_c')
        # Add a label:
        gs.preplot(f'eval sprintf("set label \\"{name}Label: coeff_a = {self.coeff_a:.3g}\\" at 2,%f", \
        fVelocity(80,{self.coeff_a},{self.coeff_b},{self.coeff_c}))', )  #  'show label')
        gs.preplot(f'set title "Performance Characteristics for {self.name}."')
        #
        # Plot elements mixing data and functions:
        gs.plot_elements(
            f'{datablock_name} using 1:2 axis x1y1 smooth mcs title "{name}Velocity Spline" with lines',
            f'{datablock_name} using 1:2 axis x1y1 title "{name}Velocity Pts" with points',
            f'{datablock_name} using 1:3 axis x1y2 title "{name}Smooth Acceleration Pts" with points ps 1.3',
            f'fVelocity(x,{self.coeff_a},{self.coeff_b},{self.coeff_c}) axis x1y1 title "{name}Smoothed Velocity" with lines',
            f'fAcceleration(x,{self.coeff_a},{self.coeff_b},{self.coeff_c}) axis x1y2 title "{name}Smooth Acceleration" with lines',
        )
        # Note when plotting we can use Pythons array slicing capabilities to just plot some of the above:
        # e.g. gc.plot(gs.plot_elements()[:3])
        gs.postplot('unset label')  # cleanup commands
        return gs  # gs contains everything to print self.


# ##############################################################
# Example usage
# ==============================================================
car1 = Car("Car1", 0, 100, 0.0001, 0.0001, 0.1, 8.0)
car2 = Car("Car2", 0, 120, 0.00015, 0.0002, 0.2, 8.0)
# Get snippets for each Car:
gs_car1 = car1.gnuplot()
gs_car2 = car2.gnuplot()
gc = GnuplotController(debug=True, script_filename="zDEMO-GNUPLOT-SCRIPTFILE.gp")
#
print("Python: Plot Car1 by itself:")
gc.preplot(gs_car1.preplot(), gs_car1.preplot_to_screen(), show_source=True)
gc.plot(gs_car1.plot_elements(), pause=3)
gc.postplot(gs_car1.postplot())
print("Python: Publishing Car1:")
gc.preplot(gs_car1.preplot_to_file(), show_source=True)
gc.plot(gs_car1.plot_elements(), show_output=True, pause=0)
gc.postplot(gs_car1.postplot(), 'set output')  # play safe
#
print("Python: Plot Car2 by itself:")
gc.preplot(gs_car2.preplot(), gs_car2.preplot_to_screen(), show_source=True)
gc.plot(gs_car2.plot_elements(), pause=1)
gc.postplot(gs_car2.postplot())

# Plot both Cars on the one graph:
gs_car1 = car1.gnuplot(show_name=True)
gs_car2 = car2.gnuplot(show_name=True)
gc.preplot(gs_car1.preplot(),
           gs_car2.preplot(),
           'set title "Two Cars"',
           'set key left top',
           'print("Gnuplot: Plot both Cars on the one graph:")',
           show_source=True)
gc.plot(gs_car1.plot_elements(), gs_car2.plot_elements(), pause=-1)
gc.postplot(gs_car1.postplot(), gs_car2.postplot())
# ==============================================================
# Multiplot:
print("Python: Multiplot example:")
gc.premultiplot('set terminal qt size 800,500 title "Multiplot"', 'set multiplot layout 1,2', show_source=True)
gc.preplot(gs_car1.preplot(), gs_car1.preplot_to_screen(), 'set y2range[0:2]', show_source=True)
gc.plot(gs_car1.plot_elements(), pause=0)
gc.postplot(gs_car1.postplot())
#
gc.preplot(gs_car2.preplot(), gs_car2.preplot_to_screen(), 'set y2range[0:2]', show_source=True)
gc.plot(gs_car2.plot_elements(), pause=-1)  # stop on last plot
gc.postplot(gs_car2.postplot())
#
gc.postmultiplot()
# ==============================================================
# Diagnostic Multiplot: (see what gets sent to the file)
print("Python: Diagnotic Multiplot reveals LaTeX commands:")
gc.premultiplot(
    'set terminal qt size 800,500 title "Diagnostic Multiplot"',
    'set multiplot layout 1,2',
)
# For a diagnostic on screen we see xlabel etc as would be sent to a file
gc.preplot(gs_car1.preplot(), gs_car1.preplot_to_file())
gc.plot(gs_car1.plot_elements(), pause=0)
gc.postplot(gs_car1.postplot())
#
gc.preplot(gs_car2.preplot(), gs_car2.preplot_to_file())
gc.plot(gs_car2.plot_elements(), pause=-1)  # stop on last plot
gc.postplot(gs_car2.postplot())
#
gc.postmultiplot()
# ==============================================================
# Demo array slicing to see some curves but not all:
print("Python: Plot Car1 some curves only:")
gc.preplot(gs_car1.preplot(), gs_car1.preplot_to_screen(), 'print("Gnuplot: Plot Car1 some curves only:")', show_source=True)
gc.plot(gs_car1.plot_elements()[0], gs_car1.plot_elements()[-2:], pause=3)
gc.postplot(gs_car1.postplot())
#
gc.close()
