# Copyright (c) 2025-2026 Neil Temperley
# SPDX-License-Identifier: MIT
# See the LICENSE file in the project root for full license text.
# https://github.com/neiltemperley/gnuplot-snippets
"""Flexible controller for unrestricted gnuplot integration with Python."""
import logging
import math
import shutil
import subprocess
import sys
import time
from datetime import datetime
from types import TracebackType
from typing import Literal

from ._utils import (_clean_cmds, _extract_set_terminal_cmd,
                     _flatten_to_tuple_of_strings, _source)
from .errors import GnuplotError, GnuplotNotFoundError

logger = logging.getLogger("gnuplot_snippets")


def _gp_quote(text: str) -> str:
    """Return ``text`` as a gnuplot single-quoted string (quotes doubled)."""
    return "'" + text.replace("'", "''") + "'"


class GnuplotController:
    """Control creation and display of gnuplot plots.

    Best used as a context manager so gnuplot is always shut down and the
    debug script is written, even when an exception occurs::

        with GnuplotController(script_filename="debug.gp") as gc:
            gc.preplot('set title "sine curve"', 'set angle degrees', 'set xrange [-360:360]')
            gc.plot("sin(x)", pause=-1)
    
    Note: GnuplotController() can be used standalone but works best with GnuplotSnippets().
    Note: commands are passed to gnuplot unchanged (including ``system``),
    so never pass untrusted input.
    """

    def __init__(self,
                 debug: bool = False,
                 script_filename: str = "",
                 gnuplot_executable: str = "gnuplot") -> None:
        """Open gnuplot as a subprocess.

        Example without GnuplotSnippets::
        
            gc = GnuplotController()
            gc.preplot('set title "Some curves"', 'set angle degrees')
            gc.plot("sin(x)", "cos(x)", pause=4)
            gc.plot("sin(x)", "tan(x)", pause=5)
            gc.close()

        :param debug: If True, print the recorded gnuplot script on close.
        :param script_filename: If set, write the recorded script here on close.  Useful
            for debugging gnupot errors by "gnuplot ``script_filename``".
        :param gnuplot_executable: Name or path of the gnuplot executable.
        """
        # Plain attributes first so close() is always safe to call:
        self.is_debug: bool = debug
        self.script_filename = script_filename
        self.pause_override: int | float | None = None  # overrides pause if set
        self._closed = False
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.script = (
            "# Gnuplot script particularly useful for debugging gnuplot errors by running \"gnuplot script_filename\" in a terminal.\n"
            f"# Created on {timestamp}\n\n")

        self.gnuplot_path = self._find_gnuplot(gnuplot_executable)
        self.gnuplot = subprocess.Popen(
            [self.gnuplot_path],  # don't want -persistent switch!
            stdin=subprocess.PIPE,
            text=True,
            # universal_newlines=True,
            encoding="utf-8")

    def __enter__(self) -> "GnuplotController":
        """Context manager support."""
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc: BaseException | None,
                 tb: TracebackType | None) -> Literal[False]:
        """Context manager support."""
        self.close()
        return False  # never swallow exceptions

    def _find_gnuplot(self, executable: str = "gnuplot") -> str:
        """Return the full path to gnuplot, or raise a clear error.

        :param executable: gnuplot executable
        """
        path = shutil.which(executable)
        if path is None:
            raise GnuplotNotFoundError(
                f"Could not find '{executable}'. "
                "Install gnuplot (e.g. on Linux 'sudo apt install gnuplot') "
                "and check you can run it from the terminal command prompt.")
        return path

    def cmd(self,
            gnuplot_str: str,
            show_source: bool = False,
            script_str: str | None = None) -> None:
        """Send a command str to gnuplot ensuring a newline termination.

        :param gnuplot_str: Raw gnuplot command(s).
        :param show_source: If True, record the calling file and line in the script.
        :param script_str: If given, recorded in the script instead of ``gnuplot_str``
            (e.g. to add prompts that only make sense when run standalone).
        """
        cmd_source: str = f'# {_source(is_snippet=False)}\n' if show_source else ""
        gnuplot_str = gnuplot_str.rstrip() + "\n"
        stdin = self.gnuplot.stdin
        if stdin is None:
            raise GnuplotError("gnuplot stdin is not available!")
        try:
            stdin.write(gnuplot_str)
            stdin.flush()
        except (BrokenPipeError, ValueError, OSError) as e:
            raise GnuplotError("gnuplot process has exited!") from e
        logged = gnuplot_str if script_str is None else script_str.rstrip(
        ) + "\n"
        self.script += cmd_source + logged

    def preplot(self, *cmds: str, show_source: bool = False) -> None:
        """Send setup commands.

        :param cmds: gnuplot commands.
        :param show_source: If True, record the calling file and line in the script.
        """
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        self.cmd(_clean_cmds(cmd_source, *cmds))

    def postplot(self, *cmds: str, show_source: bool = False) -> None:
        """Send tidy up commands.

        This is an alias for preplot() to improve usability.

        :param cmds: gnuplot commands.
        :param show_source: If True, record the calling file and line in the script.
        """
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        self.cmd(_clean_cmds(cmd_source, *cmds))

    def premultiplot_to_file(self,
                             *set_cmds: str,
                             filename: str | None = None,
                             show_source: bool = True) -> None:
        """Begin a multiplot that is written to a file.

        Sends, in order: ``unset multiplot``, the ``set terminal`` command,
        ``set output '<filename>'``, then the remaining commands (e.g.
        ``set multiplot layout 1,2``). The output must be set after the
        terminal and before the multiplot starts.

        Note: Once this is called, any 'set terminal' commands in snippets are
              helpfully blocked until an 'unset multiplot' is sent by postmultiplot().

        Example::

            gc.premultiplot_to_file('set terminal pngcairo size 1000,1000',
                                    'set multiplot layout 1,2',
                                    filename='file.png')
            # then gc.preplot(...), gc.plot(...) and gc.postplot(...) for each plot...
            gc.postmultiplot()

        :param set_cmds: A 'set terminal ...' command plus 'set multiplot ...' plus any others.
        :param filename: Output file. Note: Provide both a 'set terminal' command and
            a filename, or neither.
        :param show_source: If True, record the calling file and line in the script.
        """
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        set_terminal_cmd, remaining = _extract_set_terminal_cmd(*set_cmds)
        if (set_terminal_cmd is None) != (filename is None):
            raise ValueError(
                "Provide both a 'set terminal ...' command and 'filename', or neither."
            )
        if set_terminal_cmd is None or filename is None:
            # Neither given: leave terminal/output as already configured.
            self.cmd(_clean_cmds(cmd_source, 'unset multiplot', *set_cmds))
            return
        self.cmd(
            _clean_cmds(cmd_source, 'unset multiplot', set_terminal_cmd,
                        f"set output {_gp_quote(filename)}", *remaining))

    def premultiplot_to_screen(self,
                               *set_cmds: str,
                               show_source: bool = True) -> None:
        """Begin a multiplot shown on screen.

        Note: Once this is called, any 'set terminal' commands in snippets are
              helpfully blocked until an 'unset multiplot' is sent by postmultiplot().

        Example::

            gc.premultiplot_to_screen('set terminal qt 1000,1000 title "Multiplot"',
                                      'set multiplot layout 1,2')
            # then gc.preplot(...), gc.plot(...) and gc.postplot(...) for each plot...
            gc.postmultiplot()

        :param set_cmds: A screen 'set terminal ...' command plus 'set multiplot ...' plus any others.
        :param show_source: If True, record the calling file and line in the script.
        """
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        set_terminal_cmd, _ = _extract_set_terminal_cmd(*set_cmds)
        if set_terminal_cmd is None:
            raise ValueError(
                "Must have a screen 'set terminal ' command, e.g. 'set terminal qt'."
            )
        self.cmd(
            _clean_cmds(cmd_source, 'set output', 'unset multiplot',
                        *set_cmds))

    def postmultiplot(self, *cmds: str, show_source: bool = False) -> None:
        """Send 'unset multiplot' plus other cmds to cleanup after a multiplot.

        Note: Once premultiplot_to_xxxx() is called, any 'set terminal' commands in
              snippets are blocked until an 'unset multiplot' is sent.

        Example::

            gc.premultiplot_to_screen('set terminal qt 1000,1000 title "Multiplot"',
                                      'set multiplot layout 1,2')
            # then gc.preplot(...), gc.plot(...) and gc.postplot(...) for each plot...
            gc.postmultiplot()


        :param cmds: Extra gnuplot commands to send after 'unset multiplot'.
        :param show_source: If True, record the calling file and line in the script.
        """
        cmd_source = f'# {_source(is_snippet=False)}\n' if show_source else ""
        self.cmd(_clean_cmds(cmd_source, 'unset multiplot', *cmds))

    def plot(self,
             *plot_elements: str | tuple[str, ...],
             pause: int | float | Literal["mouse_measure"] = 0,
             plot_and_ranges: str = "plot",
             show_output: bool = True,
             show_source: bool = False) -> None:
        """Build a gnuplot plot command and send it, followed by a pause.

        Note: A gnuplot plot command has the form:
              plot {<ranges>} <plot-element> {, <plot-element>, ...}

        When a pause is used, Python waits until it completes, keeping the
        gnuplot window and the Python terminal in sync during interaction.

        Example::
        
        gc = GnuplotController()
        gc.preplot('set title "Some curves"', 'set angle degrees')
        # gc.plot(gs1.plot_elements(), gs2.plot_elements(), pause=-1) # e.g. with GnuplotSnippets gs1 and gs2
        gc.plot("sin(x)", "cos(x)", pause=4)  # without GnuplotSnippets
        gc.plot("sin(x)", "tan(x)", plot_and_ranges="plot [-70:70]", pause=5)  # without GnuplotSnippets
        gc.preplot("unset angle")
        # ..other GnuplotController commands
        gc.close()

        :param plot_elements: gnuplot plot elements, e.g. "sin(x)" or "'data.csv' using 1:2".
        :param pause: How to pause after plotting. -1 waits for user input,
            0 does not pause, N > 0 pauses N seconds, and "mouse_measure"
            prompts and waits for user interaction with plot, e.g. measure a gradient.
            When pause is -1, the user may respond at the prompt:
              q, quit                 close gnuplot and exit Python
              Enter, c, continue      continue to next plot
              f, fastforward, a, all  stop pausing for all remaining plots
              <number>                set the pause (secs) for all remaining plots
        :param plot_and_ranges: The leading "plot {<ranges>}" portion of the
            gnuplot plot command, e.g. "plot", "plot [0:10]", or "splot".
        :param show_output: If True, instruct gnuplot to print the output filename
            when plotting to a file.
        :param show_source: If True, add a comment in the generated gnuplot
            script giving the file and line of this call. This is incredibly useful for
            debugging a faulty script!
        """
        if len(plot_elements) == 0:
            raise GnuplotError("Plot elements cannot be empty!")
        if self.pause_override is not None and pause != 0:
            pause = self.pause_override
        elements = _flatten_to_tuple_of_strings(plot_elements)

        # Build the gnuplot plot string:
        continue_str = ",  \\\n"  # extra spaces make nicer gnuplot error messages
        plot_cmd = _clean_cmds(plot_and_ranges + " \\\n" +
                               continue_str.join(e.strip()
                                                 for e in elements) + "\n")
        if show_source:
            plot_cmd = f"# {_source(is_snippet=False)}\n" + plot_cmd
        if show_output:
            # Printed before the pause so the filename is visible while pausing.
            plot_cmd += """
 if (strlen(GPVAL_OUTPUT) > 0) {
   print(sprintf("Gnuplot: Created plot file: \\"%s\\"", GPVAL_OUTPUT))
 }
            """
        send_cmd = script_cmd = plot_cmd
        if isinstance(pause, (int, float)):
            base = plot_cmd.rstrip()
            send_cmd = base + f"\npause {pause}\n"
            # Write user-friendly versions to script file:
            if pause < 0:
                script_cmd = base + f'\npause {pause} "Gnuplot: Press Enter to continue..."\n'
            elif pause == 0:
                script_cmd = base + f'\npause {pause} \n'  # no message
            else:
                script_cmd = base + f'\npause {pause} "Gnuplot: Pausing for {pause} seconds..."\n'
        self.cmd(send_cmd, script_str=script_cmd)  # send it

        # --------------------------------------------------------------
        # Optionally override original scripted plot workflow:
        user_input = self._wait_for_user(pause).strip().lower()
        if user_input in {"q", "quit"}:
            print("Python: Quitting gnuplot and Python!")
            self.close()
            sys.exit()
        elif user_input in {"", "c", "continue"}:
            pass  # no change
        elif user_input in {"f", "fastforward", "a", "all"}:
            print(
                "Python: Fast forwarding through all plots without further pausing!"
            )
            self.pause_override = 0
        else:
            try:
                new_pause = float(user_input)
                if not (math.isfinite(new_pause) and new_pause >= 0):
                    raise ValueError(user_input)
                self.pause_override = new_pause
                print(
                    f"Python: Sleep for following plots is set to = {self.pause_override}."
                )
            except ValueError:
                print("Python: Unrecognised response.  Continuing...")

    def _wait_for_user(
            self, pause_option: int | float | Literal["mouse_measure"]) -> str:
        """Mimic gnuplot's pause functionality in Python based on ``pause_option``.

        Note:
        - gnuplot can't see keypresses so gnuplot's "pause key" can't be used.
        - python can't see gnuplot mouse clicks so "pause mouse" also won't work.
        - These work: "pause -1", "pause 0" etc.

        :param pause_option: "mouse_measure" OR gnuplot pause values -1, 0, 1.5, 3, etc.
        :return: Whatever the user typed at the prompt ("" if none).
        """
        user_input = ""
        try:
            if pause_option == "mouse_measure":
                self.cmd(self._mouse_measurement_cmds())
                user_input = input(
                    "Python: Mouse Measurements! Next keypress must be in gnuplot window!\n"
                )
            elif isinstance(pause_option, (int, float)):
                if pause_option < 0:
                    user_input = input(
                        "Python: Press Enter to continue (or 'q' to quit, 'f' for fast forward, 'N' for N sec delays):...\n"
                    )
                    try:
                        if self.gnuplot.stdin is not None:
                            self.gnuplot.stdin.write(
                                "\n")  # gnuplot needs a char!
                            self.gnuplot.stdin.flush()
                    except (BrokenPipeError, ValueError, OSError) as e:
                        raise GnuplotError(
                            "gnuplot process has exited!") from e
                elif pause_option != 0:
                    print(f"Python: Pausing for {pause_option} seconds...")
                    time.sleep(pause_option)
            else:
                print(
                    f"Python: Invalid pause option = \"{pause_option}\". Try pause=\"mouse_measure\" or standard gnuplot numerical pause values: -1, 0, 3, etc. "
                )
        except EOFError:
            # Non-interactive stdin (CI, pipes): carry on without waiting.
            return ""
        return user_input

    def close(self) -> None:
        """Close the gnuplot window and end the session.

        Safe to call more than once. The debug script is written first, so it
        survives even if shutting gnuplot down fails.
        """
        if self._closed:
            return
        self._closed = True
        try:
            # Note: gnuplot exits on error!
            if self.is_debug:
                print("# GNUPLOT LOG SCRIPT FOR DEBUGGING:")
                print(self.script)
            if self.script_filename:
                print(f"Python: Writing script to \"{self.script_filename}\".")
                with open(self.script_filename, "w", encoding="utf-8") as f:
                    f.write(self.script)
        finally:
            self._shutdown()

    def _shutdown(self) -> None:
        """Ask gnuplot to exit, escalating to terminate then kill if it hangs."""
        if self.gnuplot.poll() is None:
            try:
                if self.gnuplot.stdin is not None:
                    self.gnuplot.stdin.write(
                        "exit\n")  # End gnuplot gracefully
                    self.gnuplot.stdin.close()
            except (OSError, ValueError) as e:
                print(f"Python: Error closing gnuplot: {e}")
            try:
                self.gnuplot.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.gnuplot.terminate()
                try:
                    self.gnuplot.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    self.gnuplot.kill()
                    self.gnuplot.wait()
        # Check if gnuplot returned an error:
        if self.gnuplot.returncode:  # non-zero (and not None)
            print(
                f"\nPython: gnuplot reported an error! To find the exact line, run:\n"
                f"    gnuplot \"{self.script_filename}\"\n"
                f"Then open \"{self.script_filename}\" and look for the comments \n"
                "near that line that point back to the Python source.\n")

    def _mouse_measurement_cmds(self) -> str:
        """Gnuplot code that adds the ability to measure deltas and gradients using
        the mouse on an interactive plot.  Very cool!

        When in use press 'm' or 'M' in plot window to get started or Esc or Return to quit.
        The measurement labels are removed again on exit.
        """
        return r"""
# gnuplot script to do measurements with the mouse. Neil Temperley 2025-04-29
# Esc or Enter to exit loop
l901 = 0; l902 = 0
pause mouse keypress "\nGnuplot: Click in gnuplot window, then press 'm' key to change mouse buttons to measure deltas and gradients,\n otherwise click in gnuplot window then press Esc or Enter to quit measurement..."
while (1) {
    if (MOUSE_KEY == 27 || MOUSE_KEY == 10 || MOUSE_KEY == 13) {  # 27 = Esc or Enter to exit
        print "\nGnuplot: Now press Enter here (in terminal window) to continue..."
        break
    }
   if (MOUSE_KEY == 109 || MOUSE_KEY == 77) { # 109='m' or 77='M' key to measure gradient
        pause mouse "\nGnuplot: First point for gradient.."
        if (exists("MOUSE_BUTTON")) {
            mx11 = MOUSE_X; my11 = MOUSE_Y; my21 = MOUSE_Y2;
            print sprintf("\nGnuplot: Mouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
            set label 901 sprintf("   Point 1!")
            set label 901 at MOUSE_X, MOUSE_Y
            set label 901 point pt 6 ps 3
            l901 = 1
            replot
        } else {
             print "Gnuplot: No mouse click?"
        }
        pause mouse "Gnuplot: Second point for gradient.."
        if (exists("MOUSE_BUTTON")) {
            mx12 = MOUSE_X; my12 = MOUSE_Y; my22 = MOUSE_Y2;
            print sprintf("\nGnuplot: Mouse button %d at x1, y1, y2 = %.8g, %.8g, %.8g", MOUSE_BUTTON, MOUSE_X, MOUSE_Y, MOUSE_Y2)
            set label 902 sprintf("   Point 2!")
            set label 902 at MOUSE_X, MOUSE_Y
            set label 902 point pt 6 ps 3
            l902 = 1
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
    pause mouse keypress "\nGnuplot: Click in gnuplot window, then press 'm' key to change mouse buttons to measure deltas and gradients,\n otherwise click in gnuplot window, then press Esc or Enter to quit measurement..."
}
# Tidy up so the labels don't leak into later plots:
if (l901) { unset label 901 }
if (l902) { unset label 902 }
        """
