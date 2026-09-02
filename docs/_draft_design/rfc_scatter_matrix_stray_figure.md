<!--
 Copyright 2021 IRT Saint Exupery, https://www.irt-saintexupery.com

 This work is licensed under the Creative Commons Attribution-ShareAlike 4.0
 International License. To view a copy of this license, visit
 http://creativecommons.org/licenses/by-sa/4.0/ or send a letter to Creative
 Commons, PO Box 1866, Mountain View, CA 94042, USA.
-->

# RFC — `ScatterMatrix` (matplotlib) leaves a stray blank figure open

> **Status of this document**: proposal for the `gemseo-vimseo` fork, checked
> against `gemseo-vimseo` 6.0.0 as of 2026-09-02.

This bug lives in the vendored GEMSEO distribution, not in VIMSEO. `gemseo-vimseo`
(PyPI, "Temporary version of GEMSEO for VIMSEO", source
`https://gitlab.com/SebastienBocquet-IRT/gemseo`) installs as the ordinary
`gemseo/` package and is pinned in `pyproject.toml` as `gemseo-vimseo[all] >= 6, < 7`.
The fix therefore has to be made in the fork and released; nothing in the VIMSEO
tree changes.

---

## 1. Diagnosis

File `gemseo/post/dataset/plots/_matplotlib/scatter_plot_matrix.py`,
`ScatterMatrix._create_figures`. When `coloring_variable` is set, the legend proxy
handles are built like this (lines 72-82):

```python
handles = [
    plt.plot(
        [],
        [],
        color=plt.cm.brg(value),
        ls="",
        marker=".",
        markersize=sqrt(10),
    )[0]
    for value in interp(color, [min(color), max(color)], [0.0, 1.0])
]
```

This list comprehension runs **before** the real figure is created by
`self._get_figure_and_axes(...)` at line 94. `plt.plot(...)` is a pyplot
state-machine call: with no current figure it implicitly opens one, so the first
iteration creates a blank `Figure` with a single empty `Axes` (view limits
autoscale to roughly `-0.05 .. 0.05`). Nothing is ever drawn into it. Line 94 then
opens the *real* figure with `plt.subplots(...)`, the scatter matrix is drawn
there, and `_create_figures` returns `[real_fig]` (line 168).

The stray figure is never added to the plot's figure list and never closed. After
`DatasetPlot.execute(...)` returns, `matplotlib.pyplot.get_fignums()` has **two**
entries even though `execute()` returned one.

Consequences downstream:

- Any tool that saves *every* open pyplot figure emits a leading blank image.
  mkdocs-gallery's `matplotlib_scraper` does exactly this — it iterates
  `plt.get_fignums()`, saves each, and only then calls `plt.close("all")`. In
  `docs/runnable_examples/02_integrated_models/plot_02_visualize-model_result.py`
  the two `ScatterMatrix(..., coloring_variable="color")` cells each render a blank
  frame followed by the correct matrix. The same would happen in a Jupyter/nbsphinx
  or sphinx-gallery build.
- `model.plot_results(data="SCALARS")` and any VIMSEO code path that builds a
  matplotlib `ScatterMatrix` with `coloring_variable` leaks a figure per call; in a
  long session these accumulate until something calls `plt.close("all")`.

Reproduce:

```python
from gemseo.datasets.dataset import Dataset
from gemseo.post.dataset.scatter_plot_matrix import ScatterMatrix
from matplotlib import pyplot as plt
from pandas import DataFrame

df = DataFrame({"a": [0.0, 1.0, 2.0], "b": [1.0, 0.5, 2.0]})
df["color"] = range(len(df))
ScatterMatrix(Dataset.from_dataframe(df), coloring_variable="color").execute(save=False, show=False)
assert len(plt.get_fignums()) == 1  # fails: 2
```

The plotly engine (`file_format="html"`,
`gemseo/post/dataset/plots/_plotly/scatter_plot_matrix.py`) is unaffected — it
builds no proxy handles.

---

## 2. Proposal

Build the proxy handles as artists instead of through the pyplot state machine.
`matplotlib.lines.Line2D` instances are valid handles for `plt.legend(handles,
labels, ...)` (line 167) and create no figure.

In `gemseo/post/dataset/plots/_matplotlib/scatter_plot_matrix.py`:

```python
from matplotlib.lines import Line2D          # new import; `from matplotlib import pyplot as plt` stays
```

```python
handles = [
    Line2D(
        [],
        [],
        color=plt.cm.brg(value),
        ls="",
        marker=".",
        markersize=sqrt(10),
    )
    for value in interp(color, [min(color), max(color)], [0.0, 1.0])
]
```

Four lines changed in one file. Nothing else in `_create_figures` moves; the
`plt.suptitle` / `plt.legend` calls at lines 165-167 still act on the current
figure, which by then is the real one from line 94.

---

## 3. Benefits

- `execute()` leaves the pyplot stack holding exactly the figures it returns — no
  stray blank frame in mkdocs-gallery, notebooks, or Sphinx, and no slow figure
  leak in long-running sessions.
- Fixes the visible defect in
  `docs/runnable_examples/02_integrated_models/plot_02_visualize-model_result.py`
  without an example-side workaround (the two `ScatterMatrix` cells stay on the
  matplotlib engine, unchanged).
- Legend appearance is identical: `Line2D([], [], color=..., ls="", marker=".",
  markersize=...)` is exactly what `plt.plot([], [], ...)` returns.

---

## 4. Backward compatibility

None affected. The returned figure list, the rendered scatter matrix and the
legend are byte-for-byte the same; only the transient extra figure disappears. No
public signature changes.

---

## 5. Items to verify before implementation

1. `gemseo/post/dataset/plots/_matplotlib/boxplot.py:89,93` uses the same
   `plt.plot([], ...)`-for-legend-handles idiom. There it runs *after* the figure
   exists, so it does not leak a figure, but it still adds invisible empty lines to
   the real axes; apply the same `Line2D` cleanup for consistency. Scan the rest of
   `_matplotlib/` for other pre-figure pyplot calls (`radar_chart.py`,
   `surfaces.py` create their figure explicitly and look fine).
2. Whether to also file this upstream at
   `https://gitlab.com/gemseo/dev/gemseo/-/issues` so the fork does not have to
   carry the patch indefinitely.
3. Target release: `gemseo-vimseo` 6.0.1, followed by bumping the pin in
   `pyproject.toml` and the `requirements/*.txt` lock files, and dropping this
   document once the release is in.
4. Add a regression test in the fork: the reproduce snippet above, asserting
   `len(plt.get_fignums()) == 1` after `execute(save=False, show=False)`.
