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
- gnuplot script logic resides primarily inside object classes.
- Native-feeling plot window interaction (as if running gnuplot directly).
- Interactive gradient and coordinate measurement via mouse.
- Batch-mode rendering for publication workflows.
- Logging and optional gnuplot stand-alone script dumping for debug and inspection.
- Python source markers in logs and stand-alone scripts.
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

This module addresses both issues:

- Organizing reusable gnuplot script fragments
- Re-enabling interactive plotting behaviors from Python
- Introducing new interactive features (like mouse measurements)

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

- Display plots interactively, one at a time, and publish PDF or LaTeX versions.
- Later switch to batch mode to render PDF or LaTeX-ready plots for publication.

This toolset was built to support that workflow. It won't do
everything for you — but it removes a lot of friction.

## Requirements

- Python 3.11 or newer
- [gnuplot](http://www.gnuplot.info/) installed and available on your `PATH`
- Tested on gnuplot 5.4 (check with `gnuplot --version`) using Linux.

## Installation

```bash
pip install gnuplot-snippets
```

Then run the demo:

```bash
python -m gnuplot_snippets.demo
```
Use the code in `demo.py` as a template to get started.

## License

Released under the [MIT License](https://github.com/neiltemperley/gnuplot-snippets/blob/main/LICENSE).

## Disclaimer

This is an unofficial project and is not affiliated with gnuplot.

