"""Flexible unrestricted tools for Gnuplot integration with Python."""
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

_gnuplot_datablock_counter: int = 0  # used to ensure unique datablock names.


def next_datablock_counter() -> int:
    """Get and increment global counter to ensure unique Gnuplot datablock names.
    Very useful to add to your code."""
    global _gnuplot_datablock_counter
    _gnuplot_datablock_counter += 1
    return _gnuplot_datablock_counter


def escape_str(s: str) -> str:
    """Escape underscores for Gnuplot titles and labels in "enhanced" terminals.

    When a terminal is "enhanced" underscores signify subscripts.
    Useful for showing a filename correctly in a title.
    :param s: gnuplot title
    :returns: escaped string
    """
    return s.replace('_', '\\\\_')


def format_dataframe(dataframe: pd.DataFrame, formatter: dict[str, str] = {}) -> str:
    """Convert a dataframe to neat readable columns also suitable for a Gnuplot datablock or datafile.

    Useful for visual examination of data.
    Note: This assumes the column names are shorter than or equal to the field widths provided in formatter.
          So increase the field widths if necessary.
    Note: If no formatter is provided numbers are formatted according to pandas with better but imperfect
    alignment of columns to data; OR If the same format for all columns is acceptable, omit formatter
    and try the equivalent of "df = df.map("{:8.2f}".format)" before calling this method.
    :param dataframe: pandas 2D dataframe, e.g. with columns: 'column1', 'column2' etc.
    :param formatter: {'column1':'fmt1', 'column2':'fmt2', ...} where 'column1' etc matches dataframe
    column names exactly and 'fmt1' etc is of the python form,
    e.g. '8.2f', '', '5d'.  
    :returns: formatted string.
    """
    if dataframe.empty:
        return ""
    formatted_df = dataframe.copy()
    # Create map:
    formatted_map = {}
    for col, fmt in formatter.items():
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
    """Create a string for logging the GnuplotSnippet's or GnuplotController command's source.

    Note: No newline at end.
    :param note: optional note to append.  Any new lines in note must begin with the comment char "#"!
    :param is_snippet: True if called from a GnuplotSnippet method else GnuplotController
    :returns: Source string to write to Gnuplot script file.
    """
    frame = inspect.currentframe().f_back.f_back  # caller's caller. # pyright: ignore
    if frame is not None:
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        funcname = frame.f_code.co_name
        source_type: str = "GnuplotSnippet" if is_snippet else "GnuplotController"
        return source_type + f" Source: {filename}: {lineno}: {funcname}()... {note}"
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


def _check_cmd(cmd):
    """Check cmd is a string."""
    if not isinstance(cmd, str):
        if type(cmd).__name__ == "GnuplotSnippet":
            raise TypeError(
                f"Expected string, got {type(cmd).__name__}: {cmd!r}.\nPerhaps you sent a snippets object to preplot()? To add a snippet use the snippets' append() method."
            )
        else:
            raise TypeError(f"Expected a string; got {type(cmd).__name__}: {cmd!r}.")
    return


def _clean_cmds(*set_cmds) -> str:
    """Clean and add one or more lines to the gnuplot command string.

    Attempts to comment out any "pause XXX" gnuplot commands of user because
    the GnuplotController will handle the pause workflow.
    :raises TypeError: if any argument is not a string
    :returns: cleaned up command string always ending with a newline unless empty.
    """
    lines: list[str] = []
    for cmd in set_cmds:
        _check_cmd(cmd)
        # if not isinstance(cmd, str):
        #     if type(cmd).__name__ == "GnuplotSnippet":
        #         raise TypeError(
        #             f"Expected string, got {type(cmd).__name__}: {cmd!r}.\nPerhaps you sent a snippets object to preplot()? To add a snippet use the snippets' append() method."
        #         )
        #     else:
        #         raise TypeError(f"Expected a string; got {type(cmd).__name__}: {cmd!r}.")
        for line in cmd.splitlines():
            # logger.debug("line     \t= \"{}\"".format(line))
            # Replace 'pause -1', 'pause mouse' with '# pause 0' etc.
            new_line = re.sub(r'\bpause\s+(-?\d+|mouse)([^;\n]*)[;]*', r'# pause \1\2\n', line)
            # logger.debug("new_line \t= \"{}\"".format(new_line))
            lines.append(new_line.rstrip())
    return "\n".join(lines) + "\n" if len(lines) > 0 else ""


class GnuplotSnippet():
    """Save gnuplot command snippets to later combine for plotting.

    Helper class for constructing and managing Gnuplot command snippets for use
    with a GnuplotController. Supports datablocks, datafiles, publishing to file or screen, multiplot
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
        gs.output_to_file(
                    set_terminal_cmd='set terminal cairolatex color pdf size 5.0,5.0*0.7 lw 2.0',
                    filename='output_filename.tex',
                    'set xlabel "$x$ [-]"; set format x "$%G$"',
                    'set ylabel "$y$ [-]"; set format y "$%G$"',
        )

        # return gs #  when done.

        # Outside the class
        gs = object.gnuplot()  # get the snippet from some class object of yours
    
        gc = GnuplotController()
        # Run the actual plotting sequence
        gc.preplot(
            gs.preplot(),
            gs.output_to_file(),
        )
        gc.plot(gs.plot_elements(), pause=0)  # Export to file
        gc.postplot(gs.postplot())
        #
        # Switch back to screen display
        gc.preplot(gs.output_to_screen())
        gc.plot(gs.plot_elements(), pause=-1)  # re plot the above to screen
        gc.postplot(gs.postplot())
        #
        gc.close()

    Notes:
        - `gc.preplot(gs.output_to_file())` and `gc.preplot(gs.output_to_screen())` are ignored during
          active multiplot sessions.
        - Use `gs.preplot()` for functions  and set commands.
        - Use `gc.preplot(gs.output_to_screen())` to switch from file output back to interactive display.
    
    Usage: Call these to assemble gnuplot command strings
     gs.preplot("# e.g. function definitions go here")
     gs.preplot_add_dataframe(dataframe, "$ValidDataBlockName") # use if required
     gs.preplot("# e.g. set title, xrange etc")
     gs.plot_elements('# Assemble lines minus the plot command e.g. "$ValidDataBlockName using 2:3" OR "sin(x)" go here')
     gs.postplot("# Any post plot commands go here e.g. mouse interaction go here")
    """

    def __init__(self, comment: str = "", debug: bool = False) -> None:
        """Initialise all snippets to empty.

        :param comment: Comment to write to the script.
        Note: If its multiline each line must begin with Gnuplot comment char "# ".
        :param debug: If True get Gnuplot to print some helpful output.
        """
        # These are Gnuplot command snippets:
        self.__preplot: str = f'# {comment}\n' if comment else ""  # set and unset commands to process before plotting
        self.__plot_elements: tuple = ()  # plot elements for the next plot command in a more convenient form for altering.
        self.__postplot: str = ""  # set and unset commands to process after plotting
        self.__preplot_to_screen: str = ""  # set terminal and related commands for screen
        self.__preplot_to_file: str = ""  # set terminal and related commands for publishing to a file
        #
        self.is_debug: bool = debug  # do some extra printouts from Gnuplot
        return

    def __str__(self) -> str:
        """Create object string for printing/debugging."""
        s: str = ''
        s += '### preplot to file   \t=\n{}\n'.format(self.__preplot_to_screen)
        s += '### preplot to screen \t=\n{}\n'.format(self.__preplot_to_file)
        s += '### preplot           \t=\n{}\n'.format(self.__preplot)
        s += '### plot_elements     \t=\n{}\n'.format(self.__plot_elements)
        s += '### postplot          \t=\n{}\n'.format(self.__postplot)
        # s += ' = """{}"""\n'.format()
        return s

    def output_to_file(self, *set_cmds: str, filename: str | None = None, show_source: bool = True) -> str:
        """Save and/or get 'set terminal ...' and related commands for printing/publishing.

        Optionally includes extra Gnuplot commands specific to publishing to a file, (e.g. labels,  axis formatting).

        - To set the terminal the first arg must be "set terminal ....", then other related screen-related args can follow.
        - The last arg is the filename, e.g. filename='output_filename.tex'
        - With no args returns the Gnuplot commands to direct output to a file.
        
        Usage Example: Publishing in LaTeX:
         gs = GnuplotSnippet()
         gs.output_to_file(
                    'set terminal cairolatex color pdf size 5.0,5.0*0.7 lw 2.0',
                    'set title', # clear title
                    'set xlabel "$x$ [-]"; set format x "$%G$"',
                    'set ylabel "$y$ [-]"; set format y "$%G$"',
                    filename='output_filename.tex')
         gs.plot_elements('cos(x)', 'sin(x)')
        # Later do this...
         gc = GnuplotController() 
         gc.preplot(gs.output_to_file(), gs.preplot())
         gc.plot(gs.plot_elements())  # write plot to file
         # gc.postplot(gs.postplot()) # [You may need to add this to clean up LaTeX specific settings.]
         gc.preplot(gs.output_to_screen()) # explicitly direct output to screen
         gc.plot(gs.plot_elements(), pause=-1) # show plot on screen
         gc.close()
        #
        :param set_cmds: "set terminal ..." then any additional Gnuplot command lines specific to publishing, e.g. 'set xlabel "$x$ [-]"; set format x "$%G$"',
        :param filename: Output file name.
        :param show_source: If True, prepend a comment with caller of this method's details.
        :returns: Preplot command string to direct output to file.
        """
        if not set_cmds:
            return self.__preplot_to_file
        cmds = list(set_cmds)  # make it mutable so we can isolate the "set terminal ..."
        set_terminal_cmd = cmds.pop(0)
        _check_cmd(set_terminal_cmd)  # simple validity check.
        if (set_terminal_cmd is None) != (filename is None):
            raise ValueError("Either both a first arg 'set terminal...' command and 'filename' must be provided, or neither.")
        debug_output = ""
        if self.is_debug and filename and set_terminal_cmd:
            escaped_filename = filename.replace('"', '\\"')
            escaped_cmd = set_terminal_cmd.replace('"', '\\"')
            debug_output = f'  print("GnuplotSnippet DEBUG: Setting output to: {escaped_filename}")\n  print("GnuplotSnippet DEBUG: {escaped_cmd}")\n'
        if set_terminal_cmd and filename:
            snippet_source = f'# {_source()}\n' if show_source else ""
            extra_cmds = _clean_cmds(*cmds) if cmds else ""
            # Multiplot doesn't want to see any new terminal definitions
            self.__preplot_to_file = (snippet_source +
                                      f'if(!GPVAL_MULTIPLOT) {{\n  set output "{filename}"\n  {set_terminal_cmd}\n{debug_output}}}\n{extra_cmds}')
        return self.__preplot_to_file

    def output_to_screen(self, *set_cmds: str, show_source: bool = True) -> str:
        """Save and/or get 'set terminal ...' and related commands for screen output

        - To set the terminal the first arg must be "set terminal ....", then other related screen-related args can follow.
        - With no args returns the Gnuplot commands to direct output to screen..
        
        This will also clear the output with "set output".
        
        Usage Example: 
         gs = GnuplotSnippet()
         gs.output_to_screen("set terminal qt size 800,800", show_source=True)
         gs.plot_elements('cos(x)', 'sin(x)')
         # Later do this...
         gc = GnuplotController() 
         gc.preplot(gs.output_to_screen(), gs.preplot()) # explicitly direct output to screen
         gc.plot(gs.plot_elements(), pause=-1)
         gc.close()
         #
        You can ignore using this method if you are happy with the system screen default.
        :param set_cmds: "set terminal ..." then any additional Gnuplot command lines specific to screen view.
        :param show_source: If True, prepend a comment with caller of this method's details.
        :returns: Preplot command string to direct output to screen.
        """
        if not set_cmds:
            return self.__preplot_to_screen
        cmds = list(set_cmds)  # make it mutable so we can isolate the "set terminal ..."
        set_terminal_cmd = cmds.pop(0)
        _check_cmd(set_terminal_cmd)  # simple validity check.
        debug_output = ""
        if self.is_debug:  # and set_terminal_cmd:
            escaped_cmd = set_terminal_cmd.replace('"', '\\"')
            debug_output = f'  print("GnuplotSnippet DEBUG: Setting output to screen.")\n  print("GnuplotSnippet DEBUG: {escaped_cmd}")\n'
        snippet_source = f'# {_source()}\n' if show_source else ""
        extra_cmds = _clean_cmds(*cmds) if cmds else ""
        # Multiplot doesn't want to see any new terminal definitions
        self.__preplot_to_screen = snippet_source + f'if(!GPVAL_MULTIPLOT) {{\n  set output\n  {set_terminal_cmd}\n{debug_output}}}\n{extra_cmds}'
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

    def preplot_add_datablock(self,
                              dataframe: pd.DataFrame,
                              datablock_name: str = "$DataBlock1",
                              formatter: dict[str, str] = {},
                              show_source: bool = True) -> str:
        """Convert a pandas dataframe to a datablock and append it to the preplot snippet.
        The dataframe should include column headers.

        For more sophisticated plots, e.g. with contours, use preplot_add_datafile().
        Usage Example:
         from gnuplot_advanced import GnuplotSnippet, next_datablock_counter
         df = pd.DataFrame(points, columns=['x_m', 'y_m'])
         datablock_name = f'$DataBlock_Profile{next_datablock_counter()}'
         gs = GnuplotSnippet()
         gs.preplot_add_datablock(df, datablock_name=datablock_name)
         gs.plot_elements('{db} using "x_m":"y_m" {title} with linepoints linetype {lt} linewidth {lw}'.format(
            db=datablock_name,
            title=f'title "{self.name}"',
            lt=self.style.get('linetype', 1),
            lw=self.style.get('linewidth', 1.5),
          ))
         gc.preplot(gs.preplot())
         gc.plot(gs.plot_elements(), pause=-1)
         gc.postplot(gs.postplot())
         gc.close()
        Note:
         set datafile columnheaders # is sent to gnuplot by this method.
        :param dataframe: pandas DataFrame with column headers.
        :param datablock_name: str unique valid gnuplot datablock name.  Default is "$DataBlock1".  Use this same name
            when creating the plot_elements()!
        :param formatter: {} used to optionally format the block to be more human readable.
        :param show_source: bool when True prepend a comment indicating caller details of this method.

        :returns: preplot snippet
        """
        snippet_source = f'# {_source()}\n' if show_source else ""
        separator = "\t"  # data separator
        self.__preplot += snippet_source + f'set datafile separator "{separator}"\nset datafile columnheaders\n'
        content = format_dataframe(dataframe, formatter=formatter)
        self.__preplot += f'{datablock_name} << EOD\n{content}EOD\n'  # Note: could add '#' before {content} to comment out the column header but not required.
        return self.__preplot

    def preplot_add_datafile(self, datasets: list[pd.DataFrame], datafile: str = "", formatter: dict[str, str] = {}, show_source: bool = True) -> str:
        """Write a single or "multi-data-set" Gnuplot datafile
        The dataframe(s) should include column headers.
        Usage Example:
        gs = GnuplotSnippet()
        gs.preplot('array Set_IDs[3] = ["1st", "2nd", "3rd"]') # we use this gnuplot array when plotting.
        gs.preplot_add_datafile(dfs, datafile=datafile)   # dfs = list[np.dataframe] one per dataset.
        gs.plot_elements(f'for [i=1:|Set_IDs|] "{datafile}" index i-1 using 1:2 title sprintf("Contour = %s", Set_IDs[i]) with lines')
        OR
        gs.plot_elements(f'for [i=1:{len(dfs)}] "{datafile}" index i-1 using 2:3 notitle with lines')
        # Then later:
        gc = GnuplotController() 
        gc.preplot(gs.preplot())
        gc.plot(gs.plot_elements(), pause=-1)
        gc.close()
        #
        Note:
         set datafile columnheaders # is sent to gnuplot by this method.
        :param datasets: list of pandas DataFrames where each DataFrame is a gnuplot dataset.  Each DataFrame should have column headers.
        :param datafile: This will create this Gnuplot compatible multi-dataset datafile.
        :param formatter: {} used to optionally format the datafile to be more human readable.
        :param show_source: bool when True prepend a comment indicating caller details of this method.
        :param gnuplot_arrayname: A unique name of Gnuplot array to hold set_ids. Must be unique!
        :returns: preplot snippet
        """
        snippet_source = f'# {_source()}\n' if show_source else ""
        separator = "\t"  # data separator
        self.__preplot += snippet_source + f'set datafile separator "{separator}"\nset datafile columnheaders\n'
        # if set_ids:
        #     # Create a Gnuplot array of dataset ids for possible inclusion in plot titles:
        #     n = len(set_ids)
        #     values_str = ", ".join(f'\\"{s}\\"' for s in set_ids)
        #     array_str = f'array {gnuplot_arrayname}[{n}] = [ {values_str} ]\n'
        #     self.__preplot += array_str
        #     if self.is_debug:
        #         self.__preplot += f'print("GnuplotSnippet DEBUG: Number of datasets = {n} with Set IDs: {array_str}")\n'
        #
        blocks: list[str] = []
        for df in datasets:
            blocks.append(format_dataframe(df, formatter=formatter))
        if datafile:
            with open(datafile, "w") as f:
                f.write("\n\n".join(blocks))
            if self.is_debug:
                escaped_filename = datafile.replace('"', '\\"')
                self.__preplot += f'\
  print("GnuplotSnippet DEBUG: Python wrote multi-dataset datafile {escaped_filename}")\n\
  print("GnuplotSnippet DEBUG: Usage example: plot {escaped_filename} for [i=1:3] index i-1 using 1:2 title sprintf(\\"Contour: %d\\",i")\n'

        return self.__preplot

    def plot_elements(self, *plot_elements, reset: bool = False) -> tuple[str]:
        """Append one or more plot elements lines to the gnuplot plot string.
        
        Note: from Gnuplot help, a plot command for Gnuplot looks like this:
           plot {<ranges>} <plot-element> {, <plot-element>, <plot-element>}
        Accepts either:
           - Multiple element strings as arguments: plot_elements(plot_element1, plot_element2)
           - Tuples of plot element strings: plot_elements((plot_element1, plot_element2))
        Usage Example:
         gs = GnuplotSnippet()
         gs.plot_elements('cos(x)', 'sin(x)')
         gc = GnuplotController() 
         gc.preplot(gs.preplot())
         gc.plot(gs.plot_elements(), pause=-1)
         gc.postplot(gs.postplot())
         gc.close()
        :param plot_elements: one or more Gnuplot plot elements
        :param reset: if true clear plot elements before appending.
        :returns: tuple of plot_elements
        """
        if reset:
            self.__plot_elements = ()  # clear
        self.__plot_elements += _flatten_to_tuple_of_strings(plot_elements)
        return self.__plot_elements

    def postplot(self, *post_plot_cmds, defaults: bool = False, reset: bool = False, show_source: bool = True) -> str:
        """Append one or more post_plot_cmds to the postplot snippet to be sent to gnuplot after plotting.
        
        Usually "unset" commands, e.g. unset label; unset arrow; unset multiplot; etc.
        Examples to consider: "unset format x; unset xdata; unset x2tics; unset x2mtics; unset y2mtics;"
        Only required if you want to follow up with another graph without resetting.
         Usage Example:
         gs1 = GnuplotSnippet()
         gs1.plot_elements('cos(x)', 'sin(x)')
         gs2 = GnuplotSnippet()
         gs2.plot_elements('tan(x)')
         #
         gc = GnuplotController() 
         gc.preplot(gs1.preplot())
         gc.plot(gs1.plot_elements(), pause=-1)
         gc.postplot(gs1.postplot()) # Tidy up before the next plot.
         #
         gc.plot(gs2.plot_elements(), pause=-1)
         gc.close()
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
        Useful when adding several GnuplotSnippets from different objects into one.
         Usage Example:
         gs1 = GnuplotSnippet()
         gs1.plot_elements('cos(x)', 'sin(x)')
         gs2 = GnuplotSnippet()
         gs2.plot_elements('tan(x)')
         #
         gs1.append(gs2)        # Append gs2 so now all appear on the one plot.
         gc = GnuplotController() 
         gc.preplot(gs1.preplot())
         gc.plot(gs1.plot_elements(), pause=-1)
         gc.close()
        # EQUIVALENT TO:
         gc.preplot(gs1.preplot(), gs2.preplot())
         gc.plot(gs1.plot_elements(), gs2.plot_elements(), pause=-1)
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
