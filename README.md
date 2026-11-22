# gnuplot_advanced

<!--toc:start-->
- [gnuplot_advanced](#gnuplotadvanced)
  - [Features](#features)
  - [🚀 Overview](#🚀-overview)
  - [Background](#background)
  - [📦 Installation](#📦-installation)
<!--toc:end-->

Advanced Gnuplot utilities for power users.

Tools for tightly integrating Gnuplot with Python, enabling flexible
graph-by-graph interaction, interactive exploration, and batch
publishing — all from within Python.

Designed for Gnuplot power users who need to visualize complex data
across different Python objects and classes with minimal Gnuplot
rescripting per plot.


## Features

- Full access to Gnuplot functionality for sophisticated plots.
- Minimal Gnuplot code duplication across different plots.
- Gnuplot script logic resides primarily inside object classes.
- Native-feeling plot window interaction (as if running Gnuplot directly).
- Interactive gradient and coordinate measurement via mouse.
- Batch-mode rendering for publication workflows.
- Logging and optional Gnuplot stand-alone script dumping for debug and inspection.
- Python source markers in logs and stand-alone scripts.
- Neat human-readable formatting of Gnuplot datablocks and datafiles.


## 🚀 Overview

`gnuplot_advanced` provides seamless integration between Python and
Gnuplot, focused on organizing and reusing Gnuplot script components
across complex visualizations.

Creating one-off plots from Python using existing Gnuplot packages is
easy — but managing large, layered plots with data originating from
multiple classes is not. And Python packages often lack the same
interactive behavior that comes from launching a Gnuplot session
directly.

Conversely managing a large number of interactive and publication
plots solely using Gnuplot script files results in large complex files
difficult to naviage and manage.

This module addresses both issues:

- Organizing reusable Gnuplot script fragments
- Re-enabling interactive plotting behaviors from Python
- Introducing new interactive features (like mouse measurements)

The fundamental principle of snippets as implemented here is that each
object class should generate Gnuplot scripts (snippets) to plot itself
on screen or to a file.  To plot multiple objects on the same graph,
or to create a multiplot graph, those snippets are simply combined
with a minimum of additional Gnuplot commands.

> ⚠️ This package is *not intended for Gnuplot beginners*. It assumes
> comfort with Gnuplot syntax and behavior. It does *not* provide a
> simplified interface to Gnuplot, rather, it empowers experienced users with
> unrestricted access to Gnuplot from within Python.

  
### Background
I often work with multiple mathematical models, each represented by a
class with one or more `gnuplot_xxx()` methods. These models typically
generate Gnuplot datablocks or multi-contour datafiles.

Things become complex when combining models, e.g. overlaying two
models with multiple axes, creating a multiplot, or using glorious
Gnuplot constructs such as:

```text
plot \
for [i=1:nContoursModelA] "datafileModelA.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model A, Contour=%d",aContoursModelA[i]) lw 2.5, \
for [i=1:nContoursModelB] "datafileModelB.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model B, Contour=%d",aContoursModelB[i]) lw 2.5, \
  $DataBlockModelC using 1:3 title "Model C" lw 2.5 dt 2
```

This module provides Python-side containers for such Gnuplot snippets,
allowing you to mix and match them to create plots with minimal script
duplication.

During model research and development, I often:

- Display plots interactively, one at a time and publish pdf or LaTeX versions.
- Later switch to batch mode to render pdf or LaTeX-ready plots for publication

This toolset was built to support that workflow. It won’t do
everything for you --- but it removes a lot of friction.


## 📦 Installation

1. Install gnuplot.  You can find it here: http://www.gnuplot.info/
2. Make sure running gnuplot at a terminal prompt will work!
3. Download gnuplot_advanced from PyPI
4. Install gnuplot_advanced:

```bash
pip install gnuplot_advanced
```
5. Run the demo.py

```bash
python -m gnuplot_advanced.demo
```
6. Use the code in demo.py as template to get started.
