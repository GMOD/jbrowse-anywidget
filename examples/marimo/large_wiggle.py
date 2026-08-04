"""Large signal in marimo: the visible region drives the computation.

The reactive twin of examples/13_large_wiggle.ipynb. Same idea — a wiggle is
only ever drawn at screen resolution, so bin in Python for the window in view
and the payload stops depending on how much data is underneath — but in marimo
the wiring disappears: no `observe`, no callback, no manually clearing the
previous track. A cell that reads `view.location` simply re-runs when it
changes, because marimo tracks that dependency itself.

Run it:      marimo edit examples/marimo/large_wiggle.py
Or read it:  marimo export html examples/marimo/large_wiggle.py -o out.html
"""

import marimo

app = marimo.App(width="medium")


@app.cell
def _():
    import re

    import marimo as mo
    import numpy as np

    from jbrowse_anywidget import LinearGenomeView, features_track

    return LinearGenomeView, features_track, mo, np, re


@app.cell
def _(mo):
    mo.md(
        """
        # Large signal, recomputed for the window in view

        `signal` below stands in for whatever your pipeline produced — an array,
        a zarr store, a database, a file on a cluster the browser can't reach.
        It never moves. Only the ~1500 values needed to draw the current view
        ever cross into the browser.
        """
    )
    return


@app.cell
def _(np):
    # 100bp bins across hg38 chr1 — the shape of a coverage track. Inlining all
    # of this would be ~233MB of JSON; as a bigWig it is 21MB. Neither happens.
    CHROM, CHROM_LEN, BIN = "1", 248_956_422, 100
    starts = np.arange(0, CHROM_LEN - BIN, BIN, dtype=np.int64)
    signal = np.random.default_rng(0).gamma(2.0, 3.0, starts.size).astype(np.float32)
    return BIN, CHROM, signal, starts


@app.cell
def _(LinearGenomeView, mo):
    view = mo.ui.anywidget(
        LinearGenomeView(assembly="hg38", location="1:1,000,000..1,200,000")
    )
    view
    return (view,)


@app.cell
def _(BIN, CHROM, features_track, np, re, signal, starts, view):
    # THE reactive cell. Reading view.location is the whole subscription — pan or
    # zoom above and this re-runs, rebins, and replaces the track. The Jupyter
    # version of this needs view.observe(handler, "location"), a callback, and an
    # explicit `view.tracks = []` to drop the previous window.
    SCREEN_BINS = 1500

    def rebin(start, end):
        # ceiling division, so SCREEN_BINS is a ceiling rather than a target a
        # floor-divided step overshoots
        step = max(BIN, -(-(end - start) // SCREEN_BINS))
        edges = np.arange(start, end, step, dtype=np.int64)
        idx = np.searchsorted(starts, edges)
        return (
            step,
            edges,
            [
                float(signal[a:b].mean()) if b > a else 0.0
                for a, b in zip(idx, np.r_[idx[1:], idx[-1]])
            ],
        )

    match = re.match(
        r"^\s*([^:\s]+)\s*:\s*([\d,]+)\s*\.\.\s*([\d,]+)", view.location or ""
    )
    if match:
        start, end = (int(match[i].replace(",", "")) for i in (2, 3))
        step, edges, values = rebin(start, end)
        # a `score` column makes this a QuantitativeTrack: a real wiggle with a
        # value axis, not boxes to color by hand
        view.widget.tracks = [
            features_track(
                [
                    {
                        "refName": CHROM,
                        "start": int(s),
                        "end": int(s) + step,
                        "score": round(v, 2),
                    }
                    for s, v in zip(edges, values)
                ],
                name="signal (recomputed for this view)",
                track_id="live",
            )
        ]
        summary = f"{end - start:,} bp in view -> {len(edges)} bins at {step:,} bp"
    else:
        # a gene name or a whole-chromosome locstring doesn't parse
        summary = f"not a region: {view.location!r}"
    return (summary,)


@app.cell
def _(mo, summary):
    mo.md(f"`{summary}` — constant work per view, whatever the data behind it.")
    return


if __name__ == "__main__":
    app.run()
