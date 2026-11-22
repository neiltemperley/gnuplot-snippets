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


<!-- Advanced tools to aid integrating Gnuplot with Python enabling -->
<!-- advanced flexible graph-by-graph interaction and batch publishing all -->
<!-- from within Python. The tools are targeted at Gnuplot power users who -->
<!-- want to examine a variety complicated plots of data from different -->
<!-- Python objects and classes and achieve this with a minimum of -->
<!-- gnuplot rescripting per plot. -->


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


<!-- - Unrestricted access to gnuplot functionality for complicated plots. -->
<!-- - Minimal gnuplot code duplication when plotting the same data on different graphs -->
<!--   - Where possible most gnuplot script resides in its object's class. -->
<!-- - Plot window interaction as if launched from within gnuplot. -->
<!-- - Advanced interactive mouse measurement of graph gradients. -->
<!-- - Batch processing for publication. -->
<!-- - Logging and gnuplot script dump for an alternative debugging workflow. -->

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

---

<!-- `gnuplot_advanced` provides tight Python and Gnuplot integration and -->
<!-- management of gnuplot script workflows. -->

<!-- While creating a one-off plot from with Python is easy.  Managing -->
<!-- complex plots with data drawn from multiple objects and classes is -->
<!-- not.  Furthermore from within Python it is difficult to mimic the same -->
<!-- on-screen interactivity available from launching gnuplot script from -->
<!-- within a gnuplot session.  This module seeks to address both problems -->
<!-- while providing some new interactive functionality --- mouse -->
<!-- measurements. -->
 
<!-- This module is *not* for gnuplot beginners.  This module deliberately -->
<!-- avoids providing a simplified interface to Gnuplot.  Rather the focus -->
<!-- is on leveraging Gnuplot's advanced capabilities from within Python -->
<!-- and ensuring proper interaction with Gnuplot plot windows is possible. -->
  
### Background
I often work with multiple mathematical models, each represented by a
class with one or more `gnuplot_xxx()` methods. These models typically
generate Gnuplot datablocks or multi-contour datafiles.

Things become complex when combining models, e.g. overlaying two
models with multiple axes, creating a multiplot, or using glorious
Gnuplot constructs such as:
```gnuplot
plot \
for [i=1:nContoursModelA] "datafileModelA.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model A, Contour=%d",aContoursModelA[i]) lw 2.5,\
for [i=1:nContoursModelB] "datafileModelB.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model B, Contour=%d",aContoursModelB[i]) lw 2.5,\
  $DataBlockModelC using 1:3 title "Model C" lw 2.5 dt 2
```

<!-- I often have multiple mathematical models (algorithms) that I want to -->
<!-- plot individually or in various combinations to make comparisons. -->
<!-- Each model has it's own class and one or more gnuplot_xxxx() methods -->
<!-- to plot itself.  Prior to plotting, each model typically will generate -->
<!-- one more gnuplot datablocks, or gnuplot datafiles consisting of -->
<!-- multiple contours. -->

<!-- Things get tricky when I want to show different models on the one -->
<!-- plot, e.g. plot two models on the one graph with multiple axes, or -->
<!-- create a multiplot using glorious gnuplot plot constructs such as -->
<!-- ```gnuplot -->
<!-- plot \ -->
<!-- for [i=1:nContoursModelA] "datafileModelA.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model A, Contour=%d",aContoursModelA[i]) lw 2.5,\ -->
<!-- for [i=1:nContoursModelB] "datafileModelB.dat" index i-1 using 1:(column("Performance_Gap")) axes x1y2 title sprintf("Model B, Contour=%d",aContoursModelB[i]) lw 2.5,\ -->
<!--   $DataBlockModelC using 1:3 axes x1y1 title "Model C" lw 2.5 dt 2 -->

This module provides Python-side containers for such Gnuplot snippets,
allowing you to mix and match them to create plots with minimal script
duplication.

During model research and development, I often:

- Display plots interactively, one at a time
- Later switch to batch mode to render LaTeX-ready plots for publication

This toolset was built to support that workflow. It won’t do
everything for you --- but it removes a lot of friction.


<!-- This module provides 'containers' for gnuplot script portions that can -->
<!-- be safely combined into a new plots with a minimal of new gnuplot -->
<!-- script code required. -->

<!-- Furthermore, during the model research and development phase I want to -->
<!-- show the plots sequentially on screen and interact manually with each -->
<!-- in turn. Later I want to batch process them creating LaTeX plot files -->
<!-- for publishing. -->

<!-- This module is the toolset I developed for doing all the above.  It -->
<!-- doesn't do everything for you but it helps. -->


## 📦 Installation

```bash
pip install gnuplot_advanced
```
