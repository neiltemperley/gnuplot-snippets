"""Flexible unrestricted tools for Gnuplot integration with Python."""
import logging
# import pdb  # python debugger. Useful are: pdb.post_mortem() and import pdb; pdb.set_trace() will launch pdb at this spot.
import os
import sys
import inspect
import subprocess
import time
import copy
import re
from datetime import datetime
import pandas as pd
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


def format_dataframe(dataframe: pd.DataFrame, format_dict: dict[str, str] = {}, separator: str = "\t") -> str:
    """Convert a dataframe to neat readable columns also suitable for a Gnuplot datablock or datafile.

    Also useful for visual examination of data.
    Note: This assumes the column names are shorter than or equal to the field widths provided in format_dict.
          So increase the field widths if necessary.
    Note: If no format_dict is provided results are formatted according to pandas with better but imperfect
    alignment of columns to data.
    :param dataframe: pandas 2D dataframe, e.g. with columns: 'column1', 'column2' etc.
    :param format_dict: {'column1':'fmt1', 'column2':'fmt2', ...} where 'column1' etc matches dataframe
    column names exactly and 'fmt1' etc is of the python form but without a width specifier,
    e.g. '.2f', '', 'd'
    :returns: formatted string.
    """
    formatted_df = dataframe.copy()
    # Create map:
    formatted_map = {}
    for col, fmt in format_dict.items():
        formatted_map[col] = lambda x, format=fmt: f"{x:{format}}"
    # Convert data to formatted strings:
    for col, val in dataframe.items():
        if col in formatted_map:  # ignore unknown keys
            formatted_df[col] = dataframe[col].map(formatted_map[col])
        else:
            formatted_df[col] = dataframe[col].map(lambda x: f"{x:}")  # default formats of pandas
    # Format header row to align to columns:
    header = ""
    first_row = formatted_df.iloc[0]
    for col, val in first_row.items():
        header += f"{col:>{len(val)}}\t"
    return header + "\n" + formatted_df.to_csv(header=False, index=False, sep="\t")


def _snippet_source(note=""):
    """Create a string for logging the snippet's source.

    Note: No newline at end.
    :param note: optional note to append.  Any newlines must be followed by the Gnuplot comment char "#"!
    """
    frame = inspect.currentframe().f_back.f_back  # caller's caller.
    filename = frame.f_code.co_filename
    lineno = frame.f_lineno
    funcname = frame.f_code.co_name
    return f"Snippet source is {filename}, {funcname}(), line {lineno}... {note}"


def _flatten_to_tuple_of_strings(*args):
    """Flatten a tuple containing strings and possible nested tuples of strings.

    :returns: tuple of strings
    """

    def _flatten(item):
        """Recursive flatten."""
        if isinstance(item, (list, tuple)):
            for sub in item:
                yield from _flatten(sub)
        else:
            yield str(item)
        return

    tuple_strs = tuple(_flatten(args))
    # Plot elments cannot be empty! Remove any empty strings:
    return tuple(s for s in tuple_strs if s)


def _clean_cmds(*set_cmds) -> str:
    """Clean and add one or more lines to the gnuplot command string.

    Attempts to comment out any "pause XXX" gnuplot commands of user because
    the GnuplotController will handle the pause workflow.
    :returns: cleaned up command string
    """
    clean_set_cmds: str = ""
    for cmd in set_cmds:
        # print(f"cmd = {cmd}")
        # print(f"cmd = {cmd.splitlines()}")
        for line in cmd.splitlines():
            # logger.debug("line     \t= \"{}\"".format(line))
            # Replace 'pause -1', 'pause mouse' with '# pause 0' etc.
            new_line = re.sub(r'\bpause\s+(-?\d+|mouse)([^;\n]*)[;]*', r'# pause \1\2\n', line)
            # logger.debug("new_line \t= \"{}\"".format(new_line))
            clean_set_cmds += new_line.rstrip() + "\n"
    return clean_set_cmds


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

    def cmd(self, gnuplot_str: str):
        """Send the gnuplot command str without checks."""
        self.script += gnuplot_str
        self.gnuplot.stdin.write(gnuplot_str)
        self.gnuplot.stdin.flush()

    def preplot(self, *cmds: str):
        """Send setup commands."""
        self.cmd(_clean_cmds(*cmds))

    def postplot(self, *cmds: str):
        """Send tidy up commands."""
        self.cmd(_clean_cmds(*cmds))

    def plot(self, *plot_elements: str, pause=0, plot_and_ranges: str = "plot"):
        """Build and send the plot command and pause option to Gnuplot.

        Showing the plot maintains synchronisation between the gnuplot plot window
        and the python terminal during manual interaction.
        Note: from Gnuplot help, a plot command for Gnuplot looks like this:
          plot {<ranges>} <plot-element> {, <plot-element>, <plot-element>}
        :param plot_elements: Gnuplot "<plot-element> {, <plot-element>, <plot-element>}" 
        :param plot_and_ranges: string containing "plot {<ranges>}" portion of command 
        :param pause: = "mouse_measure" OR similar to gnuplot pause = -1, 0, N seconds
        """
        # logger.debug("*plot_elements \t= \"{}\"".format(*plot_elements))
        if self.pause_override is not None:
            pause = self.pause_override
        plot_elements = _flatten_to_tuple_of_strings(plot_elements)
        # Build the gnuplot plot string:
        gnuplot_continue_str = ",  \\\n"  # extra spaces make nicer Gnuplot error messages
        pcl = plot_and_ranges + " \\\n"
        for plot_line in plot_elements:
            pcl += plot_line.strip() + gnuplot_continue_str
        pcl = pcl.rstrip(gnuplot_continue_str) + "\n"

        if isinstance(pause, int):
            self.cmd(_clean_cmds(pcl).rstrip() + f"\npause {pause}\n")
        else:
            self.cmd(_clean_cmds(pcl))
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
        gnuplot can't see keypresses so "pause key" can't be used.
        python can't see  gnuplot mouse clicks so "pause mouse" also won't work.
        These work: "pause -1", "pause 0" etc.
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
            self.gnuplot.stdin.write("exit\n")  # Terminate gnuplot gracefully
            self.gnuplot.stdin.flush()
            self.gnuplot.stdin.close()
            #self.gnuplot.wait()
            #self.gnuplot.terminate()
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


def interaction_demo():
    """Test GnuplotController."""
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


class GnuplotSnippets():
    """Save gnuplot command snippets to later combine for plotting.

    FIXME XXXX
    The goal is to provide flexible unrestricted access to all gnuplot's capabilities from python.
    These methods require you to know how to create valid gnuplot commands.
    Usage: Call these to assemble gnuplot command strings
     this_object.preplot_miscellaneous("# e.g. function definitions go here")
     this_object.add_dataframe_to_preplot_miscellaneous(dataframe, "$ValidDataBlockName") # use if required
     this_object.preplot_set_cmds("# e.g. set title, xrange etc")
     this_object.plot_elements('# Assemble lines minus the plot command e.g. "$ValidDataBlockName using 2:3" OR "sin(x)" go here')
     this_object.postplot_cmds("# Any post plot commands go here e.g. mouse interaction go here")
    When all is send the output of each of the following methods to gnuplot:
     this_object.preplot_miscellaneous()
     this_object.preplot_set_cmds()
     this_object.show_plot()
     this_object.postplot_cmds()
    """

    def __init__(self, comment: str = "") -> None:
        """Initialise all snippets to empty.

        :param comment: Use this to indicate the python source class or method.
        Note: If its multiline each line must begin with Gnuplot comment char "# ".
        """
        # These are gnuplot command snippets
        self.__terminal: str = ""  # set terminal and terminal-related commands
        self.__preplot: str = f'# {comment}\n' if comment else ""  # set and unset commands to process before plotting
        self.__plot_elements: tuple = ()  # plot elements for the next plot command in a more convenient form for altering.
        self.__postplot: str = ""  # set and unset commands to process after plotting
        return

    def __str__(self) -> str:
        """Create object string for printing/debugging."""
        s: str = ''
        s += '### preplot       \t= \n{}\n'.format(self.__preplot)
        s += '### plot_elements \t= \n{}\n'.format(self.__plot_elements)
        s += '### postplot      \t= \n{}\n'.format(self.__postplot)
        # s += ' = """{}"""\n'.format()
        return s

    def set_terminal_and_output(self, *set_cmds, show_source: bool = True) -> str:
        """Append set terminal and output commands to the preplot snippet.

        Sets termimal with some safety.
        Note: You may want to include set xlabel and xformat here based on your terminal choice.
        Usage: gs.set_terminal_and_output('set terminal qt size 1400,700 position 300,150 title "{}"'.format("Window Title")
        :param set_cmds: one or more commands relating to set terminal.
        :param show_source: bool when True prepend a comment indicating caller details of this method.
        :returns: pre plot command string
        """
        # Add some internal gnuplot protection against multiple terminals.
        # This is overkill...
        # return self.preplot(
        #     'unset terminal\noutput = ""\n',  # take some precautions
        #     f'if (!exists("terminal_type")) {{ terminal_type="Terminal{id}"  # only set term once!',
        #     '  print terminal_type',
        #     '  ' + _clean_cmds(*set_cmds),  # set terminal and output
        #     '}')
        # if not title == "":
        #     set_cmd += f' title "{title}"'  # append title
        snippet_source = f'# {_snippet_source()}' if set_cmds and show_source else ""
        return self.preplot(
            snippet_source,
            'output = ""\n',  # take some precautions
            _clean_cmds(*set_cmds),  # set terminal and output
            show_source=False)

    def preplot(self, *set_cmds, reset: bool = False, show_source: bool = True) -> str:
        """Append one or more lines to the preplot snippet to be sent to gnuplot before plotting.

        For example, all gnuplot "set" and "unset" commands: title, ranges, labels, arrows etc.
        :param set_cmds: one or more set/unset commands or datablock definitions
        :param reset: if true clear preplot snippet before appending.  Usually not required.
        :param show_source: bool when True prepend a comment indicating caller details of this method.
        :returns: preplot snippet of all commands
        """
        snippet_source = f'# {_snippet_source()}\n' if set_cmds and show_source else ""
        if reset:
            self.__preplot = ""  # clear
        self.__preplot += snippet_source + _clean_cmds(*set_cmds)
        return self.__preplot

    def add_datablock_to_preplot(self, dataframe: pd.DataFrame, datablock_name: str = "$DataBlock1") -> str:
        """Convert a pandas dataframe to a datablock and append it to the preplot snippet.

        For more sophisticated plots, e.g. with contours, you'll need to write your data a gnuplot-compatible
        formatted file and use the filename in the plot element.
        :param dataframe: pandas DataFrame
        :param datablock_name: str unique valid gnuplot datablock name.  Default is "$DataBlock1".  Use this same name
            when creating the plot_elements()!

        :returns: preplot snippet
        """
        show_source = True
        warning_str = "# DEPRECATED GNUPLOT SNIPPETS METHOD!  Use preplot_add_datablock().\n"
        snippet_source = f'# {_snippet_source()}\n' if show_source else ""
        separator = "\t"  # data separator
        self.__preplot += warning_str + snippet_source + f'set datafile separator "{separator}"\n'
        content = dataframe.to_csv(header=True, index=False, sep=f"{separator}")  # no extra index column!
        self.__preplot += f'{datablock_name} << EOD\n# {content}EOD\n'  # Note: '#' is to comment out the column header
        # self.__preplot += f'DataBlock{id} = "{datablock_name}"\n'
        return self.__preplot

    def preplot_add_datablock(self,
                              dataframe: pd.DataFrame,
                              datablock_name: str = "$DataBlock1",
                              format_dict: dict[str, str] = {},
                              show_source: bool = True) -> str:
        """Convert a pandas dataframe to a datablock and append it to the preplot snippet.

        For more sophisticated plots, e.g. with contours, you'll need to write your data a gnuplot-compatible
        formatted file and use the filename in the plot element.
        :param dataframe: pandas DataFrame
        :param datablock_name: str unique valid gnuplot datablock name.  Default is "$DataBlock1".  Use this same name
            when creating the plot_elements()!
        :param format_dict: {} used to optionally format the block to be more human readable.
        :param show_source: bool when True prepend a comment indicating caller details of this method.

        :returns: preplot snippet
        """
        snippet_source = f'# {_snippet_source()}\n' if show_source else ""
        separator = "\t"  # data separator
        self.__preplot += f'set datafile separator "{separator}"\n'
        content = format_dataframe(dataframe, format_dict=format_dict, separator=separator)
        # content = dataframe.to_csv(header=True, index=False, sep=f"{separator}")  # no extra index column!
        self.__preplot += f'{datablock_name} << EOD\n# {content}EOD\n'  # Note: '#' is to comment out the column header
        return self.__preplot

    def plot_elements(self, *plot_elements, reset: bool = False) -> tuple[str]:
        """Append one or more plot elements lines to the gnuplot plot string.
        
        Note: from Gnuplot help, a plot command for Gnuplot looks like this:
           plot {<ranges>} <plot-element> {, <plot-element>, <plot-element>}
        Accepts either:
           - Multiple element strings as arguments: plot_elements(plot_element1, plot_element2)
           - Tuples of plot element strings: plot_elements((plot_element1, plot_element2))
        :param plot_elements: one or more Gnuplot plot elements
        :param reset: if true clear plot elements before appending.
        :returns: tuple of plot_elements
        """
        if reset:
            self.__plot_elements = ()  # clear
        self.__plot_elements += _flatten_to_tuple_of_strings(plot_elements)
        return self.__plot_elements

    # def plot(self, *plot_elements) -> tuple[str]:
    #     """Append args as gnuplot plot command lines to snippet.  These minus "plot" at the beginning.

    #     Note the GnuplotController.plot() takes these lines, and builds a valid gnuplot plot string with "plot "
    #     at the begining, like this 'plot "self.__plot_elements[0]",\\n "self.__plot_elements[1]"'
    #     The additional *plot_elements arg can be a tuple e.g. from plot_elements() or
    #     multiple args with one plot_cmd_line line per arg.

    #     Accepts either:
    #        - Multiple arguments: plot(line1, line2)
    #        - A single tuple of lines: plot((line1, line2))
    #     :param plot_elements: one or more lines for the plot command with "plot" at the beginning.
    #     :returns: returns all lines as a tuple  without the "plot " at the beginning.
    #     """
    #     self.__plot_elements += _flatten_to_tuple_of_strings(plot_elements)
    #     return self.__plot_elements

    def postplot(self, *post_plot_cmds, defaults: bool = False, reset: bool = False, show_source: bool = True) -> str:
        """Append one or more post_plot_cmds to the postplot snippet to be sent to gnuplot after plotting.
        
        Usually "unset" commands: labels, arrows, multiplot etc.
        Examples to consider: "unset format x; unset xdata; unset x2tics; unset x2mtics; unset y2mtics;"
        :param post_plot_cmds: one or more commands to send after plotting.
        :param defaults: = True to use fairly safe typical commands.
        :param reset: if true clear postplot snippet before appending.  Usually not required.
        :param show_source: bool when True prepend a comment indicating caller details of this method.
        :returns: post plot command string
        """
        snippet_source = f'# {_snippet_source()}\n' if (set_cmds or defaults) and show_source else ""
        if reset:
            self.__postplot = ""  # clear
        default_cmds = ""
        if defaults:
            default_cmds = 'unset label; unset arrow; unset multiplot; output = ""\n'
        self.__postplot += snippet_source + default_cmds + _clean_cmds(*post_plot_cmds)
        return self.__postplot


#    interaction_demo()
# if __name__ == 'main':
#     interaction_demo()
