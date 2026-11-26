# gnuplot-snippets

Composable gnuplot snippets for Python, for interactive and batch plotting by advanced users.

Tools for tightly integrating gnuplot with Python, enabling flexible
graph-by-graph interaction, interactive exploration, and batch
publishing — all from within Python.

Designed for gnuplot power users who need to visualize complex data
across different Python objects and classes with minimal gnuplot
rescripting per plot.

## Features

- Unrestricted access to gnuplot commands from Python.
- Minimal gnuplot code duplication across different plots.
- Gnuplot script logic resides primarily inside object classes.
- Native-feeling plot window interaction (as if running gnuplot directly).
- Interactive gradient and coordinate measurement via mouse.
- Batch-mode rendering for publication workflows.
- Logging and optional gnuplot stand-alone script dumping for debug and inspection.
- Python source markers in stand-alone scripts.
- Neat human-readable formatting of gnuplot datablocks and datafiles.

## Overview

Creating one-off plots from Python using existing gnuplot packages is
easy — but managing large, layered plots with data originating from
multiple classes is not. And Python packages often lack the same
interactive behavior that comes from launching a gnuplot session
directly.

Conversely, managing a large number of interactive and publication
plots solely using gnuplot script files results in large, complex files
that are difficult to navigate and manage.

This module addresses both issues by:

- Organizing reusable gnuplot script fragments.
- Re-enabling interactive plotting behaviors from Python.
- Introducing new interactive features (like mouse measurements).
- Enabling a "preview then publish" workflow across multiple plots.

The fundamental principle of snippets as implemented here is that each
object class should generate gnuplot scripts (snippets) to plot itself
on screen or to a file. To plot multiple objects on the same graph,
or to create a multiplot graph, those snippets are simply combined
with a minimum of additional gnuplot commands.

> **Note:** This package is *not intended for gnuplot beginners*. It assumes
> comfort with gnuplot syntax and behavior. It does *not* provide a
> simplified interface to gnuplot; rather, it gives experienced users
> unrestricted access to gnuplot from within Python.

## Background

I often work with multiple mathematical models, each represented by a
class with one or more `gnuplot_xxx()` methods. These models typically
generate gnuplot datablocks or multi-contour datafiles.

Things become complex when combining models, e.g. overlaying two
models with multiple axes, creating a multiplot, or using glorious
gnuplot constructs such as:

```text
plot \
for [i=1:nContoursModelA] "datafileModelA.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model A, Contour=%d",aContoursModelA[i]) lw 2.5, \
for [i=1:nContoursModelB] "datafileModelB.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model B, Contour=%d",aContoursModelB[i]) lw 2.5, \
  $DataBlockModelC using 1:3 title "Model C" lw 2.5 dt 2
```

This module provides Python-side containers for such gnuplot snippets,
allowing you to mix and match them to create plots with minimal script
duplication.

During model research and development, I often:

- Display plots interactively, one at a time, and publish PDF or
  LaTeX versions as I go.
- Later switch to batch mode to render PDF or LaTeX-ready plots for publication.

This toolset was built to support that workflow. It won't do
everything for you — but it removes a lot of friction.

## Requirements

- Python 3.10 or newer
- [gnuplot](http://www.gnuplot.info/) installed and available on your `PATH`
- Tested with gnuplot 5.4 (check with `gnuplot --version`) on Linux.

## Installation

```bash
pip install gnuplot-snippets
```

To try it in a throwaway environment first:

```bash
deactivate 2>/dev/null   # exit any active environment
mkdir -p ~/tmp
cd ~/tmp
python3 -m venv ~/tmp/gp-snippets-test
source ~/tmp/gp-snippets-test/bin/activate
# On Windows: %USERPROFILE%\tmp\gp-snippets-test\Scripts\activate
python -m pip install --upgrade pip
pip install gnuplot-snippets

# Check it works:
pip show -f gnuplot-snippets
python -c "import gnuplot_snippets; print(gnuplot_snippets.__file__)"
```

Then run the demo (see [Full demo](#full-demo) below).

## Quick example

Provide a class a `gnuplot()` method that returns a `GnuplotSnippets`:

```python
from gnuplot_snippets import GnuplotController, GnuplotSnippets

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
            show_source=True) # add source marker to script file
        gs.preplot(
            'fVelocity(t,a,b,c) = a*t**3 + b*t**2 + c*t',
            'fAcceleration(t,a,b,c) = 3.*a*t**2 + 2.*b*t + c',
            f'set title "Performance for {self.name}"',
            show_source=True)
        gs.plot_elements(
            f'fVelocity(x,{self.a},{self.b},{self.c}) title "{self.name}" with lines',
            f'fAcceleration(x,{self.a},{self.b},{self.c}) axis x1y2 title "{self.name} Acceleration" with lines',
        )
        gs.postplot('unset label')
        return gs

gc = GnuplotController(script_filename="my_script.gp")
gs = Car("Car1", 0.01, 0.0001, 0.1).gnuplot()

# Note: Args to gc.preplot() are snippets or gnuplot commands.
#       gs.preplot() returns the preplot() snippet string.
gc.preplot(gs.preplot(), "set xrange[0:15]", "set y2range[0:*]", gs.output_to_screen())
gc.plot(gs.plot_elements(), pause=4)  # wait 4s

# Change title and repeat plot with interactive measurement:
gc.preplot(
    'set title "Interactive Demo. \\nClick in this window, press \'m\' key, then click two points."'
)
gc.plot(gs.plot_elements(), pause="mouse_measure")  # interactive
gc.postplot(gs.postplot())
gc.close()
```

### Notes

- The example above uses the `qt` terminal. On Windows, switch to the
  `windows` terminal (see the comment in the demo).
- Commands are sent to gnuplot in the order you pass them, so later `set`
  commands override earlier ones, just like a normal gnuplot script.
- Here every command is also written to `my_script.gp`, so you can re-run or
  debug it directly with `gnuplot my_script.gp`.

## Full demo

The full demo covers plotting to the screen, publishing to a PDF, overlaying
two objects on one graph, and using the controller directly without snippets
(including the interactive `mouse_measure` pause). Use it as a template to
get started.

```bash
python -m gnuplot_snippets.demo
# OR:
gnuplot-snippets-demo
```

Demo source: https://github.com/neiltemperley/gnuplot-snippets/blob/main/src/gnuplot_snippets/demo.py

## Security

Snippets are passed to gnuplot verbatim, and gnuplot can run shell commands
(e.g. via `system`) and write files. Never build snippets from untrusted
input, and choose safe filenames for script and output files.

## License

Released under the [MIT License](https://github.com/neiltemperley/gnuplot-snippets/blob/main/LICENSE).

## Disclaimer

This is an unofficial project and is not affiliated with gnuplot.
