"""Flexible unrestricted gnuplot enabler."""
# import functools  # for nctdebug decorator
import logging
# import pdb  # python debugger. Useful are: pdb.post_mortem() and import pdb; pdb.set_trace() will launch pdb at this spot.
import os
import sys
import subprocess
import time
import re
from datetime import datetime
# from pprint import pformat, pprint
# from typing import (
#     Any,  # TYPE_CHECKING, Dict, List, Tuple  #, Any, Dict, Tuple  # , Optional  # https://mypy.readthedo
#     cs.io/en/stable/cheat_sheet_py3.ht
# )

# from objbrowser import browse  # type: ignore # e.g. browse(object) # Best but needs Qt stuff installed
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
#
# File handler for logging to a file (that keeps growing!):
# file_handler = logging.FileHandler("gnuplot_advanced.log")  # ouput to file
# file_handler.setLevel(logging.DEBUG)
# file_handler.setFormatter(formatter)
# logger.addHandler(file_handler)
# ##############################################################
def escape_str(s: str) -> str:
    """Escape underscores for titles.
    :param s: gnuplot title
    :returns: escaped string
    """
    return s.replace('_', '\\\\_')

def _clean_cmds(*setup_cmds, is_keep_format_spaces: bool = True) -> str:
    """Cleans and adds one or more lines to the gnuplot command string.

    Attempts to comment out any "pause XXX" gnuplot commands of user.
#    :param is_keep_format_spaces: DEPRECATED!! keeps LHS whitespace to preserved formatting. Helps visually when printing many commands when debugging.
    :returns: cleaned up command string
    """
    clean_setup_cmds: str = ""
    for cmd in setup_cmds:
        # print(f"cmd = {cmd}")
        # print(f"cmd = {cmd.splitlines()}")
        for line in cmd.splitlines():
            # logger.debug("line     \t= \"{}\"".format(line)) 
            # Replace 'pause -1', 'pause mouse' with '# pause 0' etc.
            new_line = re.sub(r'\bpause\s+(-?\d+|mouse)([^;\n]*)[;]*', r'# pause \1\2\n', line)
            # logger.debug("new_line \t= \"{}\"".format(new_line)) 
            clean_setup_cmds += new_line.rstrip() + "\n"
    return clean_setup_cmds


class GnuplotController:
    def __init__(self, debug: bool = False, script_filename: str = ""):
        # Start gnuplot process
        self.gnuplot = subprocess.Popen(
            ['gnuplot'], # don't want -persistent switch!
            stdin=subprocess.PIPE,
            #stdout=subprocess.PIPE,
            #stderr=subprocess.PIPE,
            #text=True,
            universal_newlines=True
        )
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        # Command script:
        self.script = f"# Gnuplot script for debugging or running \"gnuplot script_filename\" in a terminal.\n"
        self.script += f"# Created on {timestamp}\n"
        self.is_debug: bool = debug
        self.script_filename = script_filename

    def _cmd(self, gnuplot_str: str):
        """Send the gnuplot command str without checks."""
        self.script += gnuplot_str
        self.gnuplot.stdin.write(gnuplot_str)
        self.gnuplot.stdin.flush()

    def preplot(self, *cmds: str):
        """Send setup commands."""
        self._cmd(_clean_cmds(*cmds))
         # Capture and print the output from stdout and stderr
        #self._capture_output()

    def postplot(self, *cmds: str):
        """Send tidy up commands."""
        self._cmd(_clean_cmds(*cmds))
         # Capture and print the output from stdout and stderr
        # self._capture_output()

    def plot(self, plot_str: str, pause=0):
        """Send the plot command and pause option to Gnuplot.

        This maintains synchronisation between the gnuplot plot window
        and the python terminal.
        :param plot_str: well formed gnuplot plot string
        :param pause: = "mouse_measure" OR similar to gnuplot pause = -1, 0, N seconds
        """
        if isinstance(pause, int):
            self._cmd(_clean_cmds(plot_str).rstrip() + f"\npause {pause}\n")
        else:
            self._cmd(_clean_cmds(plot_str))
         # Capture and print the output from stdout and stderr
        # self._capture_output()
        # Wait for the user depending on the pause option
        if pause:
            self._wait_for_user(pause)

    def _wait_for_user(self, pause_option):
        """Mimic Gnuplot's pause functionality in Python based on pause option.

        Note:
        gnuplot can't see keypresses so "pause key" can't be used.
        python can't see  gnuplot mouse clicks so "pause mouse" also won't work.
        These work: "pause -1", "pause 0" etc."""
        if pause_option == "mouse_measure":
                self._cmd(self._mouse_measurement_cmds())
                # print("Python: Mouse measure commands added to script log.\nRun script from gnuplot manually from a terminal.")
                input("Python: Mouse Measurements! Next keypress must be in gnuplot window!\n")
        elif pause_option == "mouse":
            print(f"Python: Option \"{pause_option}\" to gnuplot pause won't work as expected.\nTo get these to work you must run the script within gnuplot!  Try -1 instead.")
            input("Python: Press Enter to continue...\n")  # Wait for keypress
        elif isinstance(pause_option, int):
            if pause_option < 0:
                input("Python: Press Enter to continue...\n")
                self.gnuplot.stdin.write("\n") # gnuplot needs a char!
                self.gnuplot.stdin.flush()
            else:
                print(f"Python: Pausing for {pause_option} seconds...")
                time.sleep(pause_option)  # Wait for a specified number of seconds
        else:
            print(f"Python: Invalid pause option = \"{pause_option}\".")
        return

    def close(self):
        if self.is_debug:
            print("# GNUPLOT LOG SCRIPT FOR DEBUGGING:")
            print(self.script)
        if self.script_filename:
            print(f"Writing script to \"{self.script_filename}\".")
            # print(f"Writing script to \"{os.path.abspath(self.script_filename)}\".")
            with open(self.script_filename, "w") as f:
                f.write(self.script)
        # Gnuplot exits on error!
        # if self.gnuplot.poll() is None:  # None means the process is still running
        """Properly close Gnuplot."""
        try:
            self.gnuplot.stdin.write("exit\n")   # Terminate gnuplot gracefully
            self.gnuplot.stdin.flush()
            self.gnuplot.stdin.close()
            #self.gnuplot.wait()
            #self.gnuplot.terminate()
        except Exception as e:
            print(f"Error closing gnuplot: {e}")


    def _mouse_measurement_cmds(self) -> str:
        """gnuplot code that adds the ability to measure deltas and gradients using the mouse on on interactive plot.
        Very cool.

        When in use press 'm' or 'g' in plot window to get started or Esc or Return to quit."""
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
                        set label 901 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
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
                        set label 902 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
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

def interaction_demo():
    """Simple test of GnuplotController."""
    logger.debug("test() \t= \"{}\"".format("GnuplotController"))
    logger.info("test()  \t= \"{}\"".format("GnuplotController"))
    gc = GnuplotController(debug=True)
    gc.preplot('print "hello"')
    gc.plot("plot x*sin(x)", pause=-1)  # Gnuplot will wait for keypress
    gc.postplot('pause 3 "These will be commented out!"; pause 0 "But let\'s see!"')  # pause not allowed in here!
    gc.preplot('print "goodbye"')
    gc.plot("plot x**2*sin(x)", pause="bad_choice")  # Gnuplot will wait for keypress
    gc.plot("plot x**3*sin(x)", pause="mouse_measure")
    gc.plot("plot x**4*sin(x)", pause=3)
    gc.close()
    return


class Gnuplot():
    '''Build all setup and plot strings prior to plotting using gnuplot.

    The goal is to provide flexible unrestricted access to all gnuplot's capabilities from python.
    These methods require you to know how to create valid gnuplot commands.
    Usage: Call these to assemble gnuplot command strings
     this_object.preplot_miscellaneous("# e.g. function definitions go here")
     this_object.add_dataframe_to_preplot_miscellaneous(dataframe, "$ValidDataBlockName") # use if required
     this_object.preplot_set_cmds("# e.g. set title, xrange etc")
     this_object.plot_cmd_lines('# Assemble lines minus the plot command e.g. "$ValidDataBlockName using 2:3" OR "sin(x)" go here')
     this_object.postplot_cmds("# Any post plot commands go here e.g. mouse interaction go here")
    When all is send the output of each of the following methods to gnuplot:
     this_object.preplot_miscellaneous()
     this_object.preplot_set_cmds()
     this_object.show_plot()
     this_object.postplot_cmds()
    '''

    def __init__(self) -> None:
        """Initialise.
        """
        self.__preplot_set_cmds: str = ""  # set and unset commands to process before plotting
        self.__plot_cmd_lines: str = ""  # lines for the next plot command.
        self.__plot_cmd_lines_tuple: tuple = ()  # lines for the next plot command in a more convenient form for altering.
        self.__postplot_cmds: str = ""  # process these after plotting, e.g. mouse commands, cleanup.
        self.__preplot_miscellaneous: str = ""  # miscellaneous strings to process before plotting, e.g. function definitions.
        # self.preplot_set_cmds(*setup_cmds)
        return

    def __repr__(self) -> str:
        '''Create object string for printing/debugging.'''
        s: str = ''
        s += 'preplot_miscellaneous = """\n{}"""\n'.format(self.__preplot_miscellaneous)
        s += 'preplot_set_cmds = """\n{}"""\n'.format(self.__preplot_set_cmds)
        s += 'plot_lines = """\n{}"""\n'.format(self.__plot_cmd_lines)
        s += 'plot_lines_tuple = """\n{}"""\n'.format(self.__plot_cmd_lines_tuple)
        s += 'postplot_cmds = """\n{}"""\n'.format(self.__postplot_cmds)
        # s += ' = """{}"""\n'.format()
        return s

    def show_all_cmds(self, gnuplot_plot_type: str = "plot"):
        """You can cut and paste this output to a manual gnuplot session for testing."""
        s: str = ''
        s += self.preplot_miscellaneous()
        s += self.preplot_set_cmds()
        s += self.show_plot(gnuplot_plot_type=gnuplot_plot_type) + "\n"
        s += self.postplot_cmds()
        return s

    # def _clean_cmds(self, *setup_cmds, is_keep_format_spaces: bool = True) -> str:
    #     """Cleans one or more lines to the gnuplot command string.

    #     :param is_keep_format_spaces: keeps LHS whitespace to preserved formatting. Helps visually when printing many commands when debugging.
    #     :returns: cleaned up command string
    #     """
    #     clean_setup_cmds: str = ""
    #     # Ignore empty lines
    #     for cmd in setup_cmds:
    #         cmds = StringIO(cmd).readlines()  # type: ignore # mypy ignores this!
    #         for c in cmds:
    #             if is_keep_format_spaces:
    #                 clean_setup_cmds += c.rstrip() + "\n"
    #             else:
    #                 clean_setup_cmds += c.strip() + "\n"
    #     return clean_setup_cmds

    def preplot_miscellaneous(self, *preplot_cmds, is_keep_format_spaces: bool = True) -> str:
        '''Append one or more lines to the gnuplot pre plot command string that you'll send to gnuplot before plotting.
        e.g. gnuplot function definitions and datablocks.

        :param preplot_cmds: one or more lines for the plot command
        :param is_keep_format_spaces: bool makes it easier to read strings when debugging.
        :returns: preplot_miscellaneous string

        '''
        self.__preplot_miscellaneous += _clean_cmds(*preplot_cmds, is_keep_format_spaces=is_keep_format_spaces)
        return self.__preplot_miscellaneous

    def preplot_set_cmds(self, *setup_cmds) -> str:
        '''Append one or more lines to the gnuplot setup command string that you'll send to gnuplot before plotting.
        e.g. all gnuplot "set" and "unset" commands: title, ranges, labels, arrows etc.

        :param setup_cmds: one or more lines for the plot command
        :returns: setup lines string
        '''
        self.__preplot_set_cmds += _clean_cmds(*setup_cmds, is_keep_format_spaces=False)
        return self.__preplot_set_cmds

    def add_dataframe_to_preplot_miscellaneous(self, dataframe, datablock_name: str = "$DataBlock1") -> str:
        """Converts a pandas dataframe to a datablock and appends it to the setup string (that is sent to gnuplot before
        plotting).  The resulting datablock is available for gnuplot to use for plotting. When creating the plot lines
        you must refer to the datablock by the valid gnuplot datablock name you used here!

        :param dataframe: pandas dataframe
        :param datablock_name: str unique valid gnuplot datablock name. Default is "$DataBlock1".
        Use this same name when creating the plot lines!
        :returns: preplot_miscellaneous string

        """
        content = dataframe.to_csv(header=False, index=False, sep='\t')  # no header or extra index column!
        self.__preplot_miscellaneous += '{} << EOD\n{}EOD\n'.format(datablock_name, content)
        return self.__preplot_miscellaneous

    def flatten_to_tuple_of_strings(self, *args):
        """Flattens a tuple containing strings and possible nested tuples of strings.

        :returns: tuple of strings
        """

        def _flatten(item):
            """Recursive flatten."""
            if isinstance(item, (list, tuple)):
                for sub in item:
                    yield from _flatten(sub)
            else:
                yield str(item)

        return tuple(_flatten(args))

    def plot_cmd_lines_new(self, *plot_cmd_lines):
        """Append one or more lines to the tuple that will become the gnuplot plot string.

        If you are using a gnuplot data block you must use the same
        valid gnuplot name you used when calling add_dataframe_to_preplot_miscellaneous(),
        e.g. this_object.add_dataframe_to_preplot_miscellaneous(dataframe, "$DataBlock1") and here
        this_object.plot_lines('$DataBlock1 using 2:3 title "Some title"')
        Accepts either:
           - Multiple arguments: show_plot_new(line1, line2)
           - A single tuple of lines:     show_plot_new((line1, line2))
        :param plot_lines: one or more lines for the plot command
        :returns: complete tuple of plot cmd lines
        """
        # print("### show_plot_new(): Before...")
        # print(self.__plot_cmd_lines_tuple)
        # print(plot_cmd_lines)
        self.__plot_cmd_lines_tuple += self.flatten_to_tuple_of_strings(plot_cmd_lines)
        # print("### show_plot_new(): After...")
        # print(self.__plot_cmd_lines_tuple)
        return self.__plot_cmd_lines_tuple

    def reset_plot_cmd_lines_new(self, *plot_cmd_lines) -> None:
        """Clear plot lines then optionally add new ones.

        :param plot_lines: one or more lines for the plot command
        :returns: gnuplot plot lines string
        """
        self.__plot_cmd_lines_tuple = ()  # clear
        self.plot_cmd_lines_new(*plot_cmd_lines)
        return

    def show_plot_new(self, *plot_cmd_lines, gnuplot_plot_type: str = "plot") -> str:
        """Create a complete plot string with "plot" at the beginning and all plot cmd lines with optionally appended extra lines.

        The additional *plot_cmd_lines arg can be a tuple e.g. from plot_cmd_lines() or
        multiple args with one plot_cmd_line line per arg.

        Accepts either:
           - Multiple arguments: show_plot_new(line1, line2)
           - A single tuple of lines:     show_plot_new((line1, line2))
        :param plot_lines: one or more lines for the plot command
        :returns: returns all lines as a gnuplot string with the "plot " at the beginning.
        """
        self.plot_cmd_lines_new(plot_cmd_lines)  # add lines
        gnuplot_continue_str = ",  \\\n"
        pcl = gnuplot_plot_type + " "
        for plot_line in self.__plot_cmd_lines_tuple:
            pcl += plot_line.strip() + gnuplot_continue_str
        pcl = pcl.rstrip(gnuplot_continue_str) + "\n"
        return pcl

    def plot_cmd_lines(self, *plot_cmd_lines) -> str:
        """Append one or more lines to the gnuplot plot string. If you are using a gnuplot data block you must use the same
        valid gnuplot name you used when calling add_dataframe_to_preplot_miscellaneous(),
        e.g. this_object.add_dataframe_to_preplot_miscellaneous(dataframe, "$DataBlock1") and here
        this_object.plot_lines('$DataBlock1 using 2:3 title "Some title"')

        :param plot_lines: one or more lines for the plot command
        :returns: gnuplot plot lines string
        """
        gnuplot_continue_str = ",  \\\n"
        pcl = ""
        for plot_line in plot_cmd_lines:
            pcl += plot_line.strip() + gnuplot_continue_str
        pcl = pcl.rstrip(gnuplot_continue_str)
        if pcl:
            if self.__plot_cmd_lines:
                # Append comma, continuation, newline
                self.__plot_cmd_lines = self.__plot_cmd_lines.rstrip() + gnuplot_continue_str
            self.__plot_cmd_lines += pcl + "\n"
        return self.__plot_cmd_lines

    def reset_plot_cmd_lines(self, *plot_lines) -> None:
        """Clear plot lines ready for next plot and optionally add new ones.
        :param plot_lines: one or more lines for the plot command
        :returns: gnuplot plot lines string
        """
        self.__plot_cmd_lines = ""  # clear
        self.plot_cmd_lines(*plot_lines)
        return

    def show_plot(self, *append_plot_cmd_lines, gnuplot_plot_type: str = "plot") -> str:
        """Create plot command string to send to gnuplot to plot all lines
        created with this_object.add_plot_lines()

        :param append_plot_cmd_lines: Extra plot lines to optionally fappend.
        :param gnuplot_plot_type: str: Gnuplot plot command string, e.g. , plot or splot
        :returns: plot command string to send to gnuplot
        """
        self.plot_cmd_lines(*append_plot_cmd_lines)
        return gnuplot_plot_type + " " + self.__plot_cmd_lines

    def postplot_cmds(self, *post_plot_cmds, is_keep_format_spaces: bool = True) -> str:
        '''Append one or more lines to the gnuplot post plot command string that is sent to gnuplot after plotting.
        Usually after the last multiplot. e.g. mouse control or cleanup.

        :param post_plot_cmds: one or more lines to send after plotting, e.g. mouse control or cleanup
        :returns: post plot command string
        '''
        self.__postplot_cmds += _clean_cmds(*post_plot_cmds, is_keep_format_spaces=is_keep_format_spaces)
        return self.__postplot_cmds

    # def append_mouse_measurement_postplot_cmds(self) -> None:
    #     """This adds the ability to measure deltas and gradients usinig the mouse on on interactive plot. Very cool."""
    #     # self.postplot_cmds(r"""
    #     #     # Esc or Enter to exit loop
    #     #     pause mouse keypress "\nPress 'g' key in plot window to change mouse buttons to measure deltas and gradients else Esc or Enter to quit..."
    #     #     while (1) {
    #     #         if (MOUSE_KEY == 27 || MOUSE_KEY == 10 || MOUSE_KEY == 13) {  # 27 = Esc or Enter to exit
    #     #             print "\nPress enter here (in terminal window) to terminate plot window..."
    #     #             break
    #     #         }
    #     #         if (MOUSE_KEY == 103) { # 103 = 'g' key to measure gradient
    #     #             # print MOUSE_KEY
    #     #             pause mouse "\nFirst point for gradient.."
    #     #             if (exists("MOUSE_BUTTON")) {
    #     #                 mx11 = MOUSE_X; my11 = MOUSE_Y; my21 = MOUSE_Y2;
    #     #                 print sprintf("\nMouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
    #     #                 set label 901 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
    #     #                 set label 901 at MOUSE_X, MOUSE_Y
    #     #                 set label 901 point pt 6 ps 3
    #     #                 replot
    #     #             } else {
    #     #                  print "No mouse click?"
    #     #             }
    #     #             pause mouse "Second point for gradient.."
    #     #             if (exists("MOUSE_BUTTON")) {
    #     #                 mx12 = MOUSE_X; my12 = MOUSE_Y; my22 = MOUSE_Y2;
    #     #                 print sprintf("\nMouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
    #     #                 set label 902 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
    #     #                 set label 902 at MOUSE_X, MOUSE_Y
    #     #                 set label 902 point pt 6 ps 3
    #     #                 replot
    #     #             } else {
    #     #                  print "No mouse click?"
    #     #             }
    #     #             print sprintf("## Deltas:    deltax  = %9.6g; deltay  = %9.6g; deltay2 = %9.6g;", (mx12-mx11), (my12-my11), (my22-my21))
    #     #             if ((mx12-mx11) != 0.) {
    #     #                 print sprintf("## Gradients: dy1/dx1 = %9.6g; dy2/dx1 = %9.6g;", (my12-my11)/(mx12-mx11), (my22-my21)/(mx12-mx11))
    #     #             }
    #     #             print "Mouse reset to normal!.."
    #     #         }
    #     #         pause mouse keypress "\nPress 'g' key in plot window to change mouse buttons to measure deltas and gradients else Esc or Enter to quit..."
    #     #     }
    #     # """, is_keep_format_spaces=True)
    #     return

    # def mouse_measurement_cmds(self) -> str:
    #     """This adds the ability to measure deltas and gradients usinig the mouse on on interactive plot. Very cool."""
    #     return r"""
    #         # Esc or Enter to exit loop
    #         pause mouse keypress "\nPress 'g' key in plot window to change mouse buttons to measure deltas and gradients else Esc or Enter to quit..."
    #         while (1) {
    #             if (MOUSE_KEY == 27 || MOUSE_KEY == 10 || MOUSE_KEY == 13) {  # 27 = Esc or Enter to exit
    #                 print "\nPress enter here (in terminal window) to terminate plot window..."
    #                 break
    #             }
    #             if (MOUSE_KEY == 103) { # 103 = 'g' key to measure gradient
    #                 # print MOUSE_KEY
    #                 pause mouse "\nFirst point for gradient.."
    #                 if (exists("MOUSE_BUTTON")) {
    #                     mx11 = MOUSE_X; my11 = MOUSE_Y; my21 = MOUSE_Y2;
    #                     print sprintf("\nMouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
    #                     set label 901 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
    #                     set label 901 at MOUSE_X, MOUSE_Y
    #                     set label 901 point pt 6 ps 3
    #                     replot
    #                 } else {
    #                      print "No mouse click?"
    #                 }
    #                 pause mouse "Second point for gradient.."
    #                 if (exists("MOUSE_BUTTON")) {
    #                     mx12 = MOUSE_X; my12 = MOUSE_Y; my22 = MOUSE_Y2;
    #                     print sprintf("\nMouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
    #                     set label 902 sprintf("   Mouse button %d\n   clicked here!", MOUSE_BUTTON)
    #                     set label 902 at MOUSE_X, MOUSE_Y
    #                     set label 902 point pt 6 ps 3
    #                     replot
    #                 } else {
    #                      print "No mouse click?"
    #                 }
    #                 print sprintf("## Deltas:    deltax  = %9.6g; deltay  = %9.6g; deltay2 = %9.6g;", (mx12-mx11), (my12-my11), (my22-my21))
    #                 if ((mx12-mx11) != 0.) {
    #                     print sprintf("## Gradients: dy1/dx1 = %9.6g; dy2/dx1 = %9.6g;", (my12-my11)/(mx12-mx11), (my22-my21)/(mx12-mx11))
    #                 }
    #                 print "Mouse reset to normal!.."
    #             }
    #             pause mouse keypress "\nPress 'g' key in plot window to change mouse buttons to measure deltas and gradients else Esc or Enter to quit..."
    #         }
    #     """

    # def pause(self, pygnuplot, gnuplot_pause: Any = -1, message: str = "", is_mouse_measure: bool = False) -> None:
    #     """Make gnuplot pause work from python.

    #     :param pygnuplot: the cmd() function of pygnuplot that sends a string to gnuplot
    #     :param gnuplot_pause: seconds to pause, else -1 to wait for return, else "mouse" etc.
    #     :param message: Optional message
    #     :param is_mouse_measure: If true, pause with no prompts to user because gnuplot (mouse measurement) code will manage prompts.
    #     :returns: None

    #     """
    #     if gnuplot_pause == -1 or is_mouse_measure:
    #         # Halt the code so we can interact with the plot:
    #         if is_mouse_measure:
    #             pygnuplot(self.mouse_measurement_cmds())
    #             input()  # Mouse message code will display prompts instead.
    #         else:
    #             input("Press enter here (in terminal window) to terminate plot window...")
    #     else:
    #         pygnuplot('pause {} {}'.format(gnuplot_pause, '"' + message + '"'))
    #     return


if __name__ == 'main':
     interaction_demo()
