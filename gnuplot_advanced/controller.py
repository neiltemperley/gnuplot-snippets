"""Flexible unrestricted tools for Gnuplot integration with Python."""
import logging
# import pdb  # python debugger. Useful are: pdb.post_mortem() and import pdb; pdb.set_trace() will launch pdb at this spot.
# import os
# import sys
import subprocess
import time
from datetime import datetime

from .snippet import _clean_cmds, _flatten_to_tuple_of_strings, _source

# from pprint import pformat, pprint
# from objexplore import explore  # type: ignore # e.g. explore(object) # VERY GOOD pip install objexplore
# ##############################################################
logger = logging.getLogger("gnuplot_advanced")
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


# ##############################################################
class GnuplotError(Exception):
    """Base class for exceptions in the Gnuplot plotting library."""
    pass


class GnuplotController:
    """Control creation and display of gnuplot plots."""

    def __init__(self, debug: bool = False, script_filename: str = ""):
        """Open Gnuplot as a subprocess."""
        # Start gnuplot process
        self.gnuplot = subprocess.Popen(
            ['gnuplot'],  # don't want -persistent switch!
            stdin=subprocess.PIPE,
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            #text=True,
            universal_newlines=True)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.pause_override = None  # if set to integer overrides pause value
        # Command script:
        self.script = f"# Gnuplot script for debugging or running \"gnuplot script_filename\" in a terminal.\n"
        self.script += f"# Created on {timestamp}\n"
        self.is_debug: bool = debug
        self.script_filename = script_filename

    def cmd(self, gnuplot_str: str, show_source=False):
        """Send the gnuplot command str without checks."""
        cmd_source: str = f'# {_source(is_snippet=False)}\n' if show_source else ""
        self.script += cmd_source + gnuplot_str.rstrip() + "\n"  # ensure a newline termination
        if self.gnuplot.stdin is not None:
            self.gnuplot.stdin.write(gnuplot_str)
            self.gnuplot.stdin.flush()

    def preplot(self, *cmds: str, show_source=False):
        """Send setup commands."""
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        self.cmd(_clean_cmds(cmd_source, *cmds))

    def postplot(self, *cmds: str, show_source=False):
        """Send tidy up commands."""
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        self.cmd(_clean_cmds(cmd_source, *cmds))

    def plot(self, *plot_elements, pause: int | str = 0, plot_and_ranges: str = "plot", show_source=False):
        """Build and send the plot command and pause option to Gnuplot.

        Showing the plot maintains synchronisation between the gnuplot plot window
        and the python terminal during manual interaction.
        Note: (from Gnuplot help), a plot command for Gnuplot looks like this:
          plot {<ranges>} <plot-element> {, <plot-element>, <plot-element>}
        :param plot_elements: Gnuplot "<plot-element> {, <plot-element>, <plot-element>}" 
        :param plot_and_ranges: string containing the "plot {<ranges>}" portion of a Gnuplot plot command 
        :param pause: = "mouse_measure" OR similar to gnuplot pause = -1, 0, N seconds
        """
        if len(plot_elements) == 0:
            raise GnuplotError("Plot elements cannot be empty!")
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        # logger.debug("*plot_elements \t= \"{}\"".format(*plot_elements))
        if self.pause_override is not None:
            pause = self.pause_override
        plot_elements = _flatten_to_tuple_of_strings(plot_elements)
        # Build the gnuplot plot string:
        gnuplot_continue_str = ",  \\\n"  # extra spaces make nicer Gnuplot error messages
        plot_cmd: str = plot_and_ranges + " \\\n"
        for pe in plot_elements:
            plot_cmd += pe.strip() + gnuplot_continue_str
        plot_cmd = cmd_source + plot_cmd.rstrip(gnuplot_continue_str) + "\n"

        if isinstance(pause, int):
            self.cmd(_clean_cmds(plot_cmd).rstrip() + f"\npause {pause}\n")
        else:
            self.cmd(_clean_cmds(plot_cmd))
        if pause:
            # Optionally override original scripted plot workflow:
            user_input = self._wait_for_user(pause).strip().lower()
            if user_input in {"q", "quit", "exit"}:
                print("Python: Quit Gnuplot and Python!")
                self.close()
                # time.sleep(0.5)   # FIXME. Try to prevent emacs hang.
                quit()  # better for interactive
            elif user_input in {"", "c", "continue", "n", "next"}:
                pass  # no change
            elif user_input in {"f", "forward", "ff", "r", "run"}:
                print("Python: Fast forward through all plots!")
                self.pause_override = 0
            else:
                try:
                    new_pause = int(user_input)
                    self.pause_override = new_pause
                    print(f"Python: Sleep for following plots is set to = {self.pause_override}.")
                except ValueError:
                    # No change
                    print("Python: Unrecognised response.  Continuing...")
        return

    def _wait_for_user(self, pause_option):
        """Mimic Gnuplot's pause functionality in Python based on pause option.

        Note:
        Gnuplot can't see keypresses so "pause key" can't be used.
        python can't see  gnuplot mouse clicks so "pause mouse" also won't work.
        These work: "pause -1", "pause 0" etc.
        :param pause_option: "mouse_measure OR Gnuplot pause values -1, 0, 1, 3, etc.
        """
        user_input = ""
        if pause_option == "mouse_measure":
            self.cmd(self._mouse_measurement_cmds())
            # print("Python: Mouse measure commands added to script log.\nRun script from gnuplot manually from a terminal.")
            user_input = input("Python: Mouse Measurements! Next keypress must be in gnuplot window!\n")
        elif pause_option == "mouse":
            print(
                f"Python: Option \"{pause_option}\" to gnuplot pause won't work as expected.\nTo get these to work you must run the script within gnuplot!  Try -1 instead."
            )
            input("Python: Press Enter to continue...\n")  # Wait for keypress
        elif isinstance(pause_option, int):
            if pause_option < 0:
                user_input = input("Python: Press Enter to continue (or 'q' to quit):...\n")
                if self.gnuplot.stdin is not None:
                    self.gnuplot.stdin.write("\n")  # gnuplot needs a char!
                    self.gnuplot.stdin.flush()
            else:
                print(f"Python: Pausing for {pause_option} seconds...")
                time.sleep(pause_option)  # Wait for a specified number of seconds
        else:
            print(f"Python: Invalid pause option = \"{pause_option}\". Try pause=\"mouse_measure\" or Gnuplot standard values: -1, 0, 3, etc. ")
        return user_input

    def close(self):
        """Close the gnuplot window and end the session."""
        # Note: Gnuplot exits on error!
        if self.is_debug:
            print("# GNUPLOT LOG SCRIPT FOR DEBUGGING:")
            print(self.script)
        if self.script_filename:
            print(f"Writing script to \"{self.script_filename}\".")
            # print(f"Writing script to \"{os.path.abspath(self.script_filename)}\".")
            with open(self.script_filename, "w") as f:
                f.write(self.script)
        try:
            if self.gnuplot.stdin is not None:
                self.gnuplot.stdin.write("exit\n")  # End Gnuplot gracefully
                self.gnuplot.stdin.flush()
                self.gnuplot.stdin.close()
            # if self.gnuplot.poll() is None:  # None means the process is still running
        except Exception as e:
            print(f"Error closing gnuplot: {e}")

    def _mouse_measurement_cmds(self) -> str:
        """Gnuplot code that adds the ability to measure deltas and gradients using the mouse on on interactive plot.

        When in use press 'm' or 'g' in plot window to get started or Esc or Return to quit.
        Very cool I think!
        """
        return r"""
            # gnuplot script to do measurements with the mouse. Neil Temperley 2025-04-29
            # Esc or Enter to exit loop
            pause mouse keypress "\nGnuplot: Press 'm' key in plot window to change mouse buttons to measure deltas and gradients,\n otherwise press Esc or Enter in plot window to quit..."
            while (1) {
                if (MOUSE_KEY == 27 || MOUSE_KEY == 10 || MOUSE_KEY == 13) {  # 27 = Esc or Enter to exit
                    print "\nGnuplot: Press enter here (in terminal window) to continue..."
                    break
                }
               # print MOUSE_KEY
               if (MOUSE_KEY == 103 || MOUSE_KEY == 109) { # 103='g', 109='m' key to measure gradient
                    # print MOUSE_KEY
                    pause mouse "\nGnuplot: First point for gradient.."
                    if (exists("MOUSE_BUTTON")) {
                        mx11 = MOUSE_X; my11 = MOUSE_Y; my21 = MOUSE_Y2;
                        print sprintf("\nGnuplot: Mouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
                        # set label 901 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
                        set label 901 sprintf("   Point 1!")
                        set label 901 at MOUSE_X, MOUSE_Y
                        set label 901 point pt 6 ps 3
                        replot
                    } else {
                         print "Gnuplot: No mouse click?"
                    }
                    pause mouse "Gnuplot: Second point for gradient.."
                    if (exists("MOUSE_BUTTON")) {
                        mx12 = MOUSE_X; my12 = MOUSE_Y; my22 = MOUSE_Y2;
                        print sprintf("\nGnuplot: Mouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
                        # set label 902 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
                        set label 902 sprintf("   Point 2!")
                        set label 902 at MOUSE_X, MOUSE_Y
                        set label 902 point pt 6 ps 3
                        replot
                    } else {
                         print "Gnuplot: No mouse click?"
                    }
                    print sprintf("## Gnuplot: Deltas:    deltax  = %9.6g; deltay  = %9.6g; deltay2 = %9.6g;", (mx12-mx11), (my12-my11), (my22-my21))
                    if ((mx12-mx11) != 0.) {
                        print sprintf("## Gnuplot: Gradients: dy1/dx1 = %9.6g; dy2/dx1 = %9.6g;", (my12-my11)/(mx12-mx11), (my22-my21)/(mx12-mx11))
                    }
                    print "Gnuplot: Mouse reset to normal!.."
                }
                pause mouse keypress "\nGnuplot: Press 'm' key in plot window to change mouse buttons to measure deltas and gradients,\n otherwise press Esc or Enter in plot window to quit..."
            }

        """
