"""Flexible unrestricted tools for Gnuplot integration with Python."""
# import pdb  # python debugger. Useful are: pdb.post_mortem() and import pdb; pdb.set_trace() will launch pdb at this spot.
# import os
# import sys
import inspect
import logging
import re

# from numpy import iterable
import pandas as pd
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
def escape_str(s: str) -> str:
    """Escape underscores for Gnuplot titles and labels in "enhanced" terminals.

    When a terminal is "enhanced" underscores signify subscripts.
    Useful for showing a filename correctly in a title.
    :param s: gnuplot title
    :returns: escaped string
    """
    return s.replace('_', '\\\\_')


def format_dataframe(dataframe: pd.DataFrame, format_dict: dict[str, str] = {}) -> str:
    """Convert a dataframe to neat readable columns also suitable for a Gnuplot datablock or datafile.

    Useful for visual examination of data.
    Note: This assumes the column names are shorter than or equal to the field widths provided in format_dict.
          So increase the field widths if necessary.
    Note: If no format_dict is provided numbers are formatted according to pandas with better but imperfect
    alignment of columns to data; OR If the same format for all columns is acceptable, omit format_dict
    and try the equivalent of "df = df.map("{:8.2f}".format)" before calling this method.
    :param dataframe: pandas 2D dataframe, e.g. with columns: 'column1', 'column2' etc.
    :param format_dict: {'column1':'fmt1', 'column2':'fmt2', ...} where 'column1' etc matches dataframe
    column names exactly and 'fmt1' etc is of the python form,
    e.g. '8.2f', '', '5d'.  
    :returns: formatted string.
    """
    formatted_df = dataframe.copy()
    # Create map:
    formatted_map = {}
    for col, fmt in format_dict.items():
        formatted_map[col] = lambda x, format=fmt: f"{x:{format}}"
    # Convert data to formatted strings:
    for col, val in dataframe.items():
        if col in formatted_map:  #... ignore unknown keys
            formatted_df[col] = dataframe[col].map(formatted_map[col])
        else:
            formatted_df[col] = dataframe[col].map(lambda x: f"{x:}")  # default formats of pandas
    # Format header row to align to columns:
    header = ""
    first_row = formatted_df.iloc[0]
    for col, val in first_row.items():
        header += f"{col:>{len(val)}}\t"
    return header + "\n" + formatted_df.to_csv(header=False, index=False, sep="\t")


def _source(note="", is_snippet=True) -> str:
    """Create a string for logging the snippet's or GnuplotController command's source.

    Note: No newline at end.
    :param note: optional note to append.  Any new lines in note must begin with the comment char "#"!
    :param is_snippet: True if called from a GnuplotSnippet method else GnuplotController
    """
    frame = inspect.currentframe().f_back.f_back  # caller's caller. # pyright: ignore
    if frame is not None:
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        funcname = frame.f_code.co_name
        source_type: str = "Snippet" if is_snippet else "GnuplotController command"
        return source_type + f" source is {filename}, {funcname}(), line {lineno}... {note}"
    return f"Souce unknown. {note}"


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
    # Plot elments cannot have an empty string! Remove any empty strings:
    return tuple(s for s in tuple_strs if s)


def _clean_cmds(*set_cmds) -> str:
    """Clean and add one or more lines to the gnuplot command string.

    Attempts to comment out any "pause XXX" gnuplot commands of user because
    the GnuplotController will handle the pause workflow.
    :raises TypeError: if any argument is not a string
    :returns: cleaned up command string always ending with a newline unless empty.
    """
    lines: list[str] = []
    for cmd in set_cmds:
        if not isinstance(cmd, str):
            if type(cmd).__name__ == "GnuplotSnippet":
                raise TypeError(
                    f"Expected string, got {type(cmd).__name__}: {cmd!r}.\nPerhaps you sent a snippets object to preplot()? To add a snippet use the snippets' append() method."
                )
            else:
                raise TypeError(f"Expected a string; got {type(cmd).__name__}: {cmd!r}.")
        for line in cmd.splitlines():
            # logger.debug("line     \t= \"{}\"".format(line))
            # Replace 'pause -1', 'pause mouse' with '# pause 0' etc.
            new_line = re.sub(r'\bpause\s+(-?\d+|mouse)([^;\n]*)[;]*', r'# pause \1\2\n', line)
            # logger.debug("new_line \t= \"{}\"".format(new_line))
            lines.append(new_line.rstrip())
    return "\n".join(lines) + "\n" if len(lines) > 0 else ""


class GnuplotSnippet():
    """Save gnuplot command snippets to later combine for plotting.

    FIXME XXXX
    The goal is to provide flexible unrestricted access to all gnuplot's capabilities from python.
    These methods require you to know how to create valid gnuplot commands.

    Helper class for constructing and managing Gnuplot command snippets for use
    with a GnuplotController. Supports publishing to file or screen, multiplot
    workflows, and custom terminal/output setup.

    Typical usage (see individual methods for details):

        # Initialize snippets with a class method
        gs = GnuplotSnippet()

        # Define scaled axes for undistorted 2D plot
        gs.preplot(
            '# Set variables for axis scaling:',
            'if (!exists("XMIN") || !exists("XRANGE")) { XMIN=0.0; XRANGE=1.0 }',
            'if (!exists("YMIN") || !exists("YRANGE")) { YMIN=0.0; YRANGE=1.5 }',
            'set xrange [XMIN:XMIN+XRANGE]; set yrange [YMIN:YMIN+YRANGE]',
            'set size ratio YRANGE/XRANGE',
        )

        # Set terminal for export (e.g., LaTeX-compatible PDF)
        gs.preplot_to_file(
            'set terminal cairolatex color pdf size 5.0,(5.0*YRANGE/XRANGE) lw 2.0',
            'figure.tex'
        )

        # Optional extras (labels, format)
        gs.preplot_to_file_extras(
            'set xlabel "$x$ [-]"; set format x "$%G$"',
            'set ylabel "$y$ [-]"; set format y "$%G$"',
        )

        # return gs #  when done.

        # Outside the class
        gs = object.gnuplot()  # get the snippet from the object
    
        gc = GnuplotController()
        # Run the actual plotting sequence
        gc.preplot(
            gs.preplot(),
            gs.preplot_to_file(),
            gs.preplot_to_file_extras()
        )
        gc.plot(gs.plot_elements(), pause=0)  # Export to file
        gc.postplot(gs.postplot())

        # Switch back to screen display
        gc.preplot(gs.preplot_to_screen())
        gc.plot(gs.plot_elements(), pause=-1)  # replot
        gc.postplot(gs.postplot())
    
        gc.close()

    Notes:
        - `preplot_to_file()` is ignored during active multiplot sessions.
        - Use `preplot()` for geometry setup and scaling.
        - Use `preplot_to_screen()` to switch from file output back to interactive display.
    
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
        self.__preplot: str = f'# {comment}\n' if comment else ""  # set and unset commands to process before plotting
        self.__plot_elements: tuple = ()  # plot elements for the next plot command in a more convenient form for altering.
        self.__postplot: str = ""  # set and unset commands to process after plotting
        self.__preplot_to_screen = ""  # set terminal and related commands for screen
        self.__preplot_to_file = ""  # set terminal and related commands for publishing to a file
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
        Note: You can't change the terminal in multiplot mode. So we must protect against
        multiple set terminal's from different sources.
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
        snippet_source = f'# {_source()}' if set_cmds and show_source else ""
        return self.preplot(
            snippet_source,
            'output = ""\n',  # take some precautions
            _clean_cmds(*set_cmds),  # set terminal and output
            show_source=False)

    def preplot_to_file(self, set_terminal_cmd: str | None = None, filename: str | None = None, *cmds: str, show_source: bool = True) -> str:
        """Save and/or get command to 'set output "filename"' and 'set terminal...' used for printing/publishing.

        Optionally includes extra Gnuplot commands specific to publishing to a file, (e.g. labels,  axis formatting).

        See class docstring for usage examples.
        
        Usage: Example published in LaTeX using GnuplotSnippet gs:
         gs.preplot_to_file('set terminal cairolatex color pdf size 5.0,5.0*0.7 lw 2.0',
                    'filename.tex', 'set title', # clear title
                    'set xlabel "$x$ [-]"; set format x "$%G$"',
                    'set ylabel "$y$ [-]"; set format y "$%G$"',)
        
        :param set_terminal_cmd: Gnuplot command string to set terminal.
        :param filename: Output file name.
        :param cmds: Additional Gnuplot command lines specific to publishing, e.g. 'set xlabel "$x$ [-]"; set format x "$%G$"',
        :param show_source: If True, prepend a comment with caller of this method's details.
        :returns: Preplot command string to direct output to file.
        """
        if (set_terminal_cmd is None) != (filename is None):
            raise ValueError("Either both 'set_terminal_cmd' and 'filename' must be provided, or neither.")

        if set_terminal_cmd and filename:
            snippet_source = f'# {_source()}\n' if show_source else ""
            extra_cmds = _clean_cmds(*cmds) if cmds else ""
            self.__preplot_to_file = (snippet_source + f'if(!GPVAL_MULTIPLOT) {{\n  set output "{filename}"\n  {set_terminal_cmd}\n}}\n{extra_cmds}')
        return self.__preplot_to_file

    def preplot_to_screen(self, set_terminal_cmd: str | None = None, *cmds: str, show_source: bool = True) -> str:
        """Save and/or get commands to 'unset output' and 'set terminal ...' for the screen.

        You can ignore using this if you are happy with the screen default.

        :param set_terminal_cmd: Gnuplot command string to set terminal.
        :param cmds: Additional Gnuplot command lines specific to screen view.
        :param show_source: If True, prepend a comment with caller of this method's details.
        :returns: Preplot command string to direct output to screen.
        """
        if set_terminal_cmd:
            snippet_source = f'# {_source()}\n' if show_source else ""
            extra_cmds = _clean_cmds(*cmds) if cmds else ""
            # Multiplot doesn't want to see new terminal definitions
            self.__preplot_to_screen = snippet_source + f'if(!GPVAL_MULTIPLOT) {{\n  set output\n  {set_terminal_cmd}\n}}\n{extra_cmds}'
        return self.__preplot_to_screen

    def preplot(self, *set_cmds, reset: bool = False, show_source: bool = True) -> str:
        """Append one or more lines to the preplot snippet to be sent to gnuplot before plotting.

        For example, all gnuplot "set" and "unset" commands: title, ranges, labels, arrows etc.
        :param set_cmds: one or more set/unset commands or datablock definitions
        :param reset: if true clear preplot snippet before appending.  Usually not required.
        :param show_source: bool when True prepend a comment indicating caller details of this method.
        :returns: preplot snippet of all commands
        """
        snippet_source = f'# {_source()}\n' if set_cmds and show_source else ""
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
        snippet_source = f'# {_source()}\n' if show_source else ""
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
        snippet_source = f'# {_source()}\n' if show_source else ""
        separator = "\t"  # data separator
        self.__preplot += snippet_source + f'set datafile separator "{separator}"\n'
        content = format_dataframe(dataframe, format_dict=format_dict)
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
        snippet_source = f'# {_source()}\n' if (post_plot_cmds or defaults) and show_source else ""
        if reset:
            self.__postplot = ""  # clear
        default_cmds = ""
        if defaults:
            default_cmds = 'unset label; unset arrow; unset multiplot; set output\n'
        self.__postplot += snippet_source + default_cmds + _clean_cmds(*post_plot_cmds)
        return self.__postplot

    def append(self, *snippets):
        """Append a list, tuple or single snippet onto self.

        Handles append(snippet), append([s1, s2, ...]), append((s1, s2, ...))
        or append(s1, s2, ...).
        Useful when adding several GnuplotSnippets from different objects into this one.
        """
        if len(snippets) == 1 and isinstance(snippets[0], (list, tuple)):
            items = snippets[0]  # a list or tuple of snippets was passed
        else:
            items = snippets  # multiple arguments or a single snippet
        for sn in items:
            self.preplot(sn.preplot(), show_source=False)
            self.plot_elements(sn.plot_elements())
            self.postplot(sn.postplot(), show_source=False)
        return self


#    interaction_demo()
# if __name__ == 'main':
#     interaction_demo()
