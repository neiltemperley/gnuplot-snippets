# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""Flexible unrestricted tools for Gnuplot integration with Python."""
# import inspect
import sys
import logging
import re
from collections.abc import Iterable, Iterator

import pandas as pd

logger = logging.getLogger("gnuplot_snippets")

_TERMINAL_RE = re.compile(r"^\s*set\s+term[inal]*\b", re.IGNORECASE)

_gnuplot_datablock_counter: int = 0  # used to ensure unique datablock names.


class GnuplotError(Exception):
    """Base class for exceptions in the gnuplot plotting library."""


def next_datablock_counter() -> int:
    """Get and increment global counter to ensure unique Gnuplot datablock names.
    Very useful to add to your code."""
    global _gnuplot_datablock_counter
    _gnuplot_datablock_counter += 1
    return _gnuplot_datablock_counter


def escape_str(s: str) -> str:
    """Escape underscores for Gnuplot titles and labels in "enhanced" terminals.

    When a terminal is "enhanced" underscores signify subscripts.
    Useful for showing a filename with underscores correctly in a title or label.
    :param s: gnuplot title
    :returns: escaped string
    """
    return s.replace('_', '\\\\_')


def format_dataframe(dataframe: pd.DataFrame,
                     column_formats: dict[str, str] | None = None) -> str:
    """Convert a dataframe to neat readable columns also suitable for a Gnuplot datablock or datafile.

    Useful for visual examination of data.
    
    Note: This assumes the column names are shorter than, or equal to, the field widths provided in column_formats.
          So increase the field widths if necessary.
    
    Note: If no column_formats is provided numbers are formatted according to pandas with better but imperfect
        alignment of columns to data; OR If the same format for all columns is acceptable, omit column_formats
        and try the equivalent of "df = df.map("{:8.2f}".format)" before calling this method.
    
    :param dataframe: pandas 2D dataframe, e.g. with columns: 'column1', 'column2' etc.
    :param column_formats: dict of form {'column1':'fmt1', 'column2':'fmt2', ...} where 'column1' etc matches
        dataframe column names exactly and 'fmt1' etc is of the python form,
        e.g. '8.2f', '', '5d'.  
    :returns: formatted string.
    """
    if dataframe.empty:
        return ""
    column_formats = column_formats or {}
    formatted_df = dataframe.copy()
    # Create map:
    formatted_map = {}
    for col, fmt in column_formats.items():
        formatted_map[col] = ("{:" + fmt + "}").format
        # formatted_map[col] = lambda x, format=fmt: f"{x:{format}}"
    # Convert data to formatted strings:
    for col in dataframe.columns:
        if col in formatted_map:  #... ignore unknown keys
            formatted_df[col] = dataframe[col].map(formatted_map[col])
        else:
            formatted_df[col] = dataframe[col].map(
                lambda x: f"{x:}")  # default formats of pandas
    # Format header row to align to columns:
    header = ""
    first_row = formatted_df.iloc[0]
    for col, cell in first_row.items():
        header += f"{col:>{len(cell)}}\t"
    return header + "\n" + formatted_df.to_csv(
        header=False, index=False, sep="\t")


def _gp_quote(s: str) -> str:
    """Escape a string for use inside a Gnuplot double-quoted string."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _split_top_level(line: str) -> list[str]:
    """Split one Gnuplot line on ';' outside quotes, braces and comments."""
    segments: list[str] = []
    start, depth, quote, i = 0, 0, "", 0
    while i < len(line):
        ch = line[i]
        if quote:
            if ch == "\\" and quote == '"':
                i += 1  # skip escaped character
            elif ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
        elif ch == "#":
            break  # rest of the line is a comment
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth = max(0, depth - 1)
        elif ch == ";" and depth == 0:
            segments.append(line[start:i])
            start = i + 1
        i += 1
    segments.append(line[start:])
    return segments


def _extract_set_terminal_cmd(*set_cmds: str) -> tuple[str | None, list[str]]:
    """Find 'set terminal ...' command(s) if it exists.

    Commands may be separated by newlines or by semicolons (outside quotes and
    braces). The terminal command is removed from the remaining commands.
    :param set_cmds: Gnuplot commands
    :returns: tuple of set terminal command, list of remaining command lines.
    """
    lines: list[str] = []
    terms: list[str] = []
    for cmd in set_cmds:
        for line in cmd.splitlines():
            if not line.strip():
                continue
            kept: list[str] = []
            for seg in _split_top_level(line):
                if _TERMINAL_RE.match(seg):
                    terms.append(seg.strip())
                elif seg.strip():
                    kept.append(seg.strip())
            if kept:
                lines.append("; ".join(kept))
    if len(terms) > 1:
        raise ValueError(
            f"More than one 'set terminal' command given: {terms}.")
    return (terms[0] if terms else None), lines


def _source(note: str = "", is_snippet: bool = True, depth: int = 2) -> str:
    """Create a comment string identifying the source of a gnuplot command.

    Reports the location ``depth`` frames above this function. The default of 2
    is the caller of the function that called ``_source``, i.e. the user's code
    when called from a public GnuplotSnippets or GnuplotController method.

    Note: No newline at end.
    :param note: optional note to append. Newlines are converted to comment lines.
    :param is_snippet: True if called from a GnuplotSnippets method, else GnuplotController.
    :param depth: number of frames to walk up from this function.
    :returns: Source string to write to the gnuplot script file.
    """
    source_type = "GnuplotSnippets" if is_snippet else "GnuplotController"
    note = note.replace("\n", "\n# ")
    try:
        frame = sys._getframe(depth)
    except (ValueError, AttributeError):  # stack too shallow / non-CPython
        return f"{source_type} Source unknown. {note}"
    filename = frame.f_code.co_filename
    return f"{source_type} Source: {filename}: {frame.f_lineno}: {frame.f_code.co_name}()... {note}"


def _flatten_to_tuple_of_strings(*args) -> tuple[str, ...]:
    """Flatten strings and arbitrarily nested iterables of strings.

    Accepts str, or any iterable (tuple, list, generator, ...) of those, nested to any depth.
    Empty strings are dropped, since plot elements cannot be empty.

    :raises TypeError: if any item is neither a str nor an iterable.
    :returns: tuple of strings
    """

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    def _flatten(item) -> Iterator[str]:
        if isinstance(item, str):
            yield item
        elif isinstance(item, (bytes, dict)):
            raise TypeError(
                f"plot elements cannot contain {type(item).__name__}")
        elif isinstance(item, Iterable):
            for sub in item:
                yield from _flatten(sub)
        else:
            raise TypeError(
                f"plot elements must be str or iterable of str, got {type(item).__name__}: {item!r}!"
            )

    # ++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    return tuple(s for s in _flatten(args) if s.strip())


def _check_cmd(cmd):
    """Check cmd is a string."""
    if not isinstance(cmd, str):
        if type(cmd).__name__ == "GnuplotSnippets":
            raise TypeError(
                f"Expected string, got {type(cmd).__name__}: {cmd!r}.\nPerhaps you sent a snippets object to preplot()? To add a snippet use the snippets' append() method."
            )
        else:
            raise TypeError(
                f"Expected a string; got {type(cmd).__name__}: {cmd!r}.")
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
        for line in cmd.splitlines():
            # logger.debug("line     \t= \"{}\"".format(line))
            # Replace 'pause -1', 'pause mouse' with '# pause 0' etc.
            new_line = re.sub(r'\bpause\s+(-?\d+|mouse)([^;\n]*)[;]*',
                              r'# pause \1\2\n', line)
            # logger.debug("new_line \t= \"{}\"".format(new_line))
            lines.append(new_line.rstrip())
    return "\n".join(lines) + "\n" if len(lines) > 0 else ""


class GnuplotSnippets():
    """Save gnuplot command snippets to later combine for plotting.

    Helper class for constructing and managing Gnuplot command snippets for use
    with a GnuplotController. Supports datablocks, datafiles, publishing to file or screen, multiplot
    workflows, and custom terminal/output setup.

    Example::
    
      # Typical usage (see individual methods for details):
      # Inside class MyClass:
      def gnuplot(self):
        gs = GnuplotSnippets()
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
                    'set terminal cairolatex color pdf size 5.0,5.0*0.7 lw 2.0',
                    'set xlabel "$x$ [-]"; set format x "$%G$"',
                    'set ylabel "$y$ [-]"; set format y "$%G$"',
                    filename='output_filename.tex',
        )
        return gs

    Then elsewhere::
    
        my_object = MyClass() 
        gs = my_object.gnuplot()  # get the snippets
    
        gc = GnuplotController()
        gc.preplot(gs.preplot(), gs.output_to_file(),)
        gc.plot(gs.plot_elements(), pause=0)  # Export to file
        gc.postplot(gs.postplot())
        
        # Switch back to screen display
        gc.preplot(gs.output_to_screen())
        gc.plot(gs.plot_elements(), pause=-1)
        gc.postplot(gs.postplot())
        
        gc.close()

    Notes:
        - `gc.preplot(gs.output_to_file())` and `gc.preplot(gs.output_to_screen())` are ignored during
          active multiplot sessions.
        - Use `gs.preplot()` for functions  and set commands.
        - Use `gc.preplot(gs.output_to_screen())` to switch from file output back to interactive display.
    """

    def __init__(self, comment: str = "", debug: bool = False) -> None:
        """Initialise all snippets to empty.

        :param comment: Comment to write to the script.
        Note: If its multiline each line must begin with Gnuplot comment char "# ".
        :param debug: If True get Gnuplot to print some helpful output.
        """
        # These are Gnuplot command snippets:
        # Set and unset commands to process before plotting:
        self.__preplot: str = f'# {comment}\n' if comment else ""
        # Plot elements for the next plot command in a more convenient form for altering:
        self.__plot_elements: tuple[str, ...] = ()
        self.__postplot: str = ""  # set and unset commands to process after plotting
        self.__preplot_to_screen: str = ""  # set terminal and related commands for screen
        self.__preplot_to_file: str = ""  # set terminal and related commands for publishing to a file
        #
        self.is_debug: bool = debug  # do some extra printouts from Gnuplot
        return

    def __str__(self) -> str:
        """Create object string for printing/debugging."""
        s: str = ''
        s += '### preplot to file   \t=\n{}\n'.format(self.__preplot_to_file)
        s += '### preplot to screen \t=\n{}\n'.format(self.__preplot_to_screen)
        s += '### preplot           \t=\n{}\n'.format(self.__preplot)
        s += '### plot_elements     \t=\n{}\n'.format(self.__plot_elements)
        s += '### postplot          \t=\n{}\n'.format(self.__postplot)
        # s += ' = """{}"""\n'.format()
        return s

    def output_to_file(self,
                       *set_cmds: str,
                       filename: str | None = None,
                       show_source: bool = True) -> str:
        """Record gnuplot commands that direct plot output to a file.

        Stores the given commands (usually a ``set terminal ...`` plus any
        related publishing-specific settings such as labels and axis formats) and
        returns the stored snippet.

        Called with no arguments, it just returns the commands stored so far.

        Usually the appropriate "set terminal ....", should be in set_cmds.

        Example::
        
         # Publishing in LaTeX:
         gs = GnuplotSnippets()
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
         # gc.postplot(gs.postplot()) # clean up 
         gc.preplot(gs.output_to_screen())
         gc.plot(gs.plot_elements(), pause=-1) # plot to screen
         gc.close()
        
        :param set_cmds: gnuplot commands, one per argument. Each may contain
            several commands separated by newlines or semicolons.
            Normally includes the appropriate ``set terminal ...``.
        :param filename: Output file name.
        :param show_source: If True, prepend a comment with caller of this method's details.
        :returns: Preplot command string to direct output to file.
        """
        if not set_cmds:
            return self.__preplot_to_file

        set_terminal_cmd, cmds = _extract_set_terminal_cmd(*set_cmds)
        if set_terminal_cmd is None or filename is None:
            raise ValueError(
                "Both a 'set terminal ...' command and 'filename' "
                "must be provided when giving commands.")
        if set_terminal_cmd is not None:
            _check_cmd(set_terminal_cmd)  # simple validity check.

        debug_output = ""
        if self.is_debug and filename and set_terminal_cmd:
            escaped_filename = filename.replace('"', '\\"')
            escaped_cmd = set_terminal_cmd.replace('"', '\\"')
            debug_output = f'  print("GnuplotSnippets DEBUG: Setting output to: {escaped_filename}")\n  print("GnuplotSnippets DEBUG: {escaped_cmd}")\n'
        if set_terminal_cmd and filename:
            snippet_source = f'# {_source()}\n' if show_source else ""
            extra_cmds = _clean_cmds(*cmds) if cmds else ""
            # Multiplot doesn't want to see any new terminal definitions
            self.__preplot_to_file = (
                snippet_source +
                f'if(!GPVAL_MULTIPLOT) {{\n  set output "{_gp_quote(filename)}"\n  {set_terminal_cmd}\n{debug_output}}}\n{extra_cmds}'
            )
        return self.__preplot_to_file

    def output_to_screen(self,
                         *set_cmds: str,
                         show_source: bool = True) -> str:
        """Replace the output_to_screen snippet with ``set_cmds``.
        Usually contains 'set terminal ...' and related commands for screen output.
        
        This will also clear the output with "set output".
        
        Example::
        
         gs = GnuplotSnippets()
         gs.output_to_screen("set terminal qt size 800,800", show_source=True)
         gs.plot_elements('cos(x)', 'sin(x)')
         # Later do this...
         gc = GnuplotController() 
         gc.preplot(gs.output_to_screen(), gs.preplot()) # explicitly direct output to screen
         gc.plot(gs.plot_elements(), pause=-1)
         gc.close()
         
        You can ignore using this method if you are happy with the system screen default.
        :param set_cmds: "set terminal ...", then any additional Gnuplot command lines specific to screen view.
        :param show_source: If True, prepend a comment with caller of this method's details.
        :returns: preplot snippet string to direct output to screen.
        """
        if not set_cmds:
            return self.__preplot_to_screen
        set_terminal_cmd, cmds = _extract_set_terminal_cmd(*set_cmds)
        if (set_terminal_cmd is None):
            raise ValueError(
                "Must have a 'set terminal ' command, e.g. 'set terminal qt'.")
        else:
            _check_cmd(set_terminal_cmd)  # simple validity check.

        debug_output = ""
        if self.is_debug:  # and set_terminal_cmd:
            escaped_cmd = set_terminal_cmd.replace('"', '\\"')
            debug_output = f'  print("GnuplotSnippets DEBUG: Setting output to screen.")\n  print("GnuplotSnippets DEBUG: {escaped_cmd}")\n'
        snippet_source = f'# {_source()}\n' if show_source else ""
        extra_cmds = _clean_cmds(*cmds) if cmds else ""
        # Multiplot doesn't want to see any new terminal definitions
        self.__preplot_to_screen = snippet_source + f'if(!GPVAL_MULTIPLOT) {{\n  set output\n  {set_terminal_cmd}\n{debug_output}}}\n{extra_cmds}'
        return self.__preplot_to_screen

    def preplot(self,
                *set_cmds,
                reset: bool = False,
                show_source: bool = True) -> str:
        """Append one or more lines to the preplot snippet to be sent to gnuplot before plotting.

        For example, all gnuplot "set" and "unset" commands: title, ranges, labels, arrows etc.
        To set terminal use output_to_screen() or output_to_file().
        See also preplot_add_datablock().
        :param set_cmds: one or more set/unset commands. 
        :param reset: if True clear preplot snippet before appending.  Usually not required.
        :param show_source: when True prepend a comment indicating caller details of this method.
        :returns: preplot snippet string.
        """
        snippet_source = f'# {_source()}\n' if set_cmds and show_source else ""
        if reset:
            self.__preplot = ""  # clear
        self.__preplot += snippet_source + _clean_cmds(*set_cmds)
        return self.__preplot

    def preplot_add_datablock(self,
                              dataframe: pd.DataFrame,
                              datablock_name: str = "$DataBlock1",
                              column_formats: dict[str, str] | None = None,
                              show_source: bool = True) -> str:
        """Convert a pandas dataframe to a gnuplot datablock and append it to the preplot snippet.
        The dataframe should include column headers.

        For more sophisticated plots, e.g. with contours, use preplot_add_datafile().
        
        Example::
        
         df = pd.DataFrame(points, columns=['x_m', 'y_m'])
         datablock_name = f'$DataBlock_Profile{next_datablock_counter()}'
         gs = GnuplotSnippets()
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
         "set datafile columnheaders" # is sent to gnuplot by this method.
        :param dataframe: pandas DataFrame with column headers.
        :param datablock_name: str unique valid gnuplot datablock name.  Default is "$DataBlock1".  Use this same name
            when creating the plot_elements()!
        :param column_formats: used to optionally format the block to be more human readable.
        :param show_source: when True prepend a comment indicating caller details of this method.

        :returns: preplot snippet
        """
        snippet_source = f'# {_source()}\n' if show_source else ""
        separator = "\t"  # data separator
        self.__preplot += snippet_source + f'set datafile separator "{separator}"\nset datafile columnheaders\n'
        content = format_dataframe(dataframe, column_formats=column_formats)
        self.__preplot += f'{datablock_name} << EOD\n{content}EOD\n'  # Note: could add '#' before {content} to comment out the column header but not required.
        return self.__preplot

    def preplot_add_datafile(self,
                             datasets: list[pd.DataFrame],
                             datafile: str = "",
                             column_formats: dict[str, str] | None = None,
                             show_source: bool = True) -> str:
        """Create a single or "multi-data-set" Gnuplot datafile from a list
        of DataFrames.
        
        The dataframe(s) should include column headers.
        
        Example::
        
         gs = GnuplotSnippets()
         gs.preplot('array Set_IDs[3] = ["1st", "2nd", "3rd"]') # we use this gnuplot array when plotting.
         gs.preplot_add_datafile(dfs, datafile=datafile)   # dfs = list[np.dataframe] one per dataset.
         gs.plot_elements(f'for [i=1:|Set_IDs|] "{datafile}" index i-1 using 1:2 title sprintf("Contour = %s", Set_IDs[i]) with lines')
        OR::
         gs.plot_elements(f'for [i=1:{len(dfs)}] "{datafile}" index i-1 using 2:3 notitle with lines')
         # Then later:
         gc = GnuplotController() 
         gc.preplot(gs.preplot())
         gc.plot(gs.plot_elements(), pause=-1)
         gc.close()
        #
        Note:
         set datafile columnheaders # is sent to Gnuplot by this method.
        :param datasets: list of pandas DataFrames where each DataFrame is a gnuplot dataset.  Each DataFrame should have column headers.
        :param datafile: This will create this Gnuplot-compatible multi-dataset datafile.
        :param column_formats: used to optionally format the datafile to be more human readable.
                Dict of form {'column1':'fmt1', 'column2':'fmt2', ...} where 'column1' etc matches dataframe
                column names exactly and 'fmt1' etc is of the python form,
                e.g. '8.2f', '', '5d'.  
        :param show_source: when True prepend a comment indicating caller details of this method.
        :returns: preplot snippet
        """
        if not datasets:
            raise GnuplotError("datasets cannot be empty!")
        if not datafile or "\n" in datafile:
            raise GnuplotError(f"Invalid datafile name: {datafile!r}")
        column_formats = column_formats or {}
        snippet_source = f"# {_source()}\n" if show_source else ""
        blocks = [
            format_dataframe(df, column_formats=column_formats)
            for df in datasets
        ]
        with open(datafile, "w", encoding="utf-8") as f:
            f.write("\n\n".join(blocks))
        separator = "\t"  # data separator
        self.__preplot += (snippet_source +
                           f'set datafile separator "{separator}"\n'
                           'set datafile columnheaders\n')
        if self.is_debug:
            escaped_filename = datafile.replace("\\",
                                                "\\\\").replace('"', '\\"')
            self.__preplot += (
                f'print("GnuplotSnippets DEBUG: Python wrote multi-dataset datafile {escaped_filename}")\n'
                f'print("GnuplotSnippets DEBUG: Usage example: plot \\"{escaped_filename}\\" '
                f'for [i=1:3] index i-1 using 1:2 title sprintf(\\"Contour: %d\\", i)")\n'
            )
        return self.__preplot

    def plot_elements(
        self,
        *plot_elements: str | tuple[str, ...],
        reset: bool = False,
    ) -> tuple[str, ...]:
        """Append one or more Gnuplot "plot element" lines to the plot elements snippet.
        
        Recall (from Gnuplot help), that a plot command for Gnuplot looks like this:
         plot {<ranges>} <plot-element1> {, <plot-element2>, <plot-element3>}
        This method accepts either:
          - Multiple element strings as arguments: plot_elements(plot_element1, plot_element2)
          - Tuples of plot element strings: plot_elements((plot_element1, plot_element2))
        
        Example::
         gs = GnuplotSnippets()
         gs.plot_elements('cos(x)', 'sin(x) title "Sin Demo" linewidth 2.0')
         gc = GnuplotController() 
         gc.preplot(gs.preplot()) 
         gc.plot(gs.plot_elements(), pause=-1) # send plot element snippets to controller and plot
         gc.postplot(gs.postplot())
         gc.close()
        :param plot_elements: one or more Gnuplot plot elements, e.g. "sin(x)"
        :param reset: if true clear plot elements before appending.
        :returns: tuple of plot_elements
        """
        if reset:
            self.__plot_elements = ()  # clear
        #  Replace with a new extended tuple:
        self.__plot_elements += _flatten_to_tuple_of_strings(plot_elements)
        return self.__plot_elements

    def postplot(self,
                 *post_plot_cmds,
                 defaults: bool = False,
                 reset: bool = False,
                 show_source: bool = True) -> str:
        """Append one or more post_plot_cmds to the postplot snippet to be sent to gnuplot after plotting.
        
        Usually "unset" commands, e.g. unset label; unset arrow;  etc.
        Note: "unset multiplot" is not required in a snippet; it is done automatically by
              GnuplotController.postmultiplot().
        
        Examples to consider: "unset format x; unset xdata; unset x2tics; unset x2mtics; unset y2mtics;"
        Only required if you want to follow up with another graph without reseting.
        
        Example::
        
         gs1 = GnuplotSnippets()
         gs1.plot_elements('cos(x)', 'sin(x)')
         gs2 = GnuplotSnippets()
         gs2.plot_elements('tan(x)')
         #
         gc = GnuplotController() 
         gc.preplot(gs1.preplot())
         gc.plot(gs1.plot_elements(), pause=-1)
         gc.postplot(gs1.postplot()) # Tidy up before the next plot.
         gc.plot(gs2.plot_elements(), pause=-1)
         gc.close()
        
        :param post_plot_cmds: one or more commands to send after plotting.
        :param defaults: = True to use fairly safe typical commands.
        :param reset: if true clear postplot snippet before appending.  Usually not required.
        :param show_source: bool when True prepend a comment indicating caller details of this method.
        :returns: post plot command string
        """
        snippet_source = f'# {_source()}\n' if (
            post_plot_cmds or defaults) and show_source else ""
        if reset:
            self.__postplot = ""  # clear
        default_cmds = ""
        if defaults:
            default_cmds = 'unset label; unset arrow; set output\n'
        self.__postplot += snippet_source + default_cmds + _clean_cmds(
            *post_plot_cmds)
        return self.__postplot

    def append(self, *snippets):
        """Append a list, tuple or single snippet onto self.

        Handles append(snippet), append([s1, s2, ...]), append((s1, s2, ...))
        or append(s1, s2, ...).
        Useful when combining several GnuplotSnippets from different objects into one.
        
        Example::
        
         gs1 = GnuplotSnippets()
         gs1.plot_elements('cos(x)', 'sin(x)')
         gs2 = GnuplotSnippets()
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
            # Merge the already-cleaned snippets verbatim: re-running _clean_cmds
            # would strip trailing tabs from datablock rows.
            self.__preplot += sn.preplot()
            self.plot_elements(sn.plot_elements())
            self.__postplot += sn.postplot()
            # Output snippets are replaced, not merged: the last one given wins.
            if sn.output_to_file():
                self.__preplot_to_file = sn.output_to_file()
            if sn.output_to_screen():
                self.__preplot_to_screen = sn.output_to_screen()
        return self
