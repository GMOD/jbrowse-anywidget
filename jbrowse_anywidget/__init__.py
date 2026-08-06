"""JBrowse 2 linear genome view as an anywidget.

Renders in Jupyter, JupyterLab, VS Code, Colab, and marimo from a single bundle,
and supports two-way sync of the visible region between Python and the view.

The interface is JBrowse's own config: assemblies, tracks, and sessions are the
same JSON-like dicts documented at https://jbrowse.org/jb2/docs/config_guide/,
handed straight to the view. `assembly=` also accepts a hub name (``"hg38"``,
``"GCF_..."``) the view fetches and resolves, or a bare sequence-file URL
(``".../hg38.fa.gz"``, ``.2bit``) it builds an assembly from. A custom genome
needing aliases is the flat shorthand dict — ``{"name": ..., "uri": ...,
"refNameAliases": {"uri": ...}}`` — which core expands itself.

Python adds only what JSON cannot express itself: an in-memory DataFrame as a
track (`add_features`), bytes from this kernel as a real file the browser reads
by byte range (`add_local_file`), and a network fetch (`fetch_hub`, `plugin`).
There are deliberately no builders for track, view or assembly configs — those
are plain dicts, so what you write here is what a `config.json` holds, and
nothing in this package has to grow when JBrowse gains a track type, an adapter,
a display, or a view.

For the common case a bare data-file URI in `tracks=[...]` is enough — its
track type and adapter are inferred from the extension (the declarative
shorthand `@jbrowse/img`'s `--bam`/`--bigwig` flags give the CLI) — so a whole
view is one flat, config-free call::

    view = LinearGenomeView(
        assembly="hg38",
        location="10:29,838,565..29,838,850",
        tracks=[
            "https://.../ncbiRefSeq.sort.gff.gz",
            "https://.../phyloP100way.bw",
            "https://.../reads.cram",
        ],
    )

To set a name or any other config, hand over a dict instead of the bare string
— it is merged onto the inferred config, so the adapter and index location still
come for free. A `(uri, index)` pair names a non-sibling index inline.
"""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

import anywidget
import traitlets

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import pandas as pd

_STATIC = Path(__file__).parent / "static"

__all__ = [
    "LinearGenomeView",
    "JBrowseApp",
    "features_track",
    "fetch_hub",
    "plugin",
    "PLUGIN_STORE",
]

# A JBrowse config object (assembly, track, adapter, …): plain JSON as a dict.
JsonDict = dict[str, Any]
# A `tracks=[...]` entry: a full/loose config dict, a bare data-file URI, or a
# `(uri, index)` pair.
TrackEntry = Union[str, "tuple[str, str]", JsonDict]
# What `add_features` accepts: a pandas DataFrame or a sequence of row mappings.
FeatureSource = Union["pd.DataFrame", "Iterable[Mapping[str, Any]]"]


class _LocalFilesMixin(traitlets.HasTraits):
    """Files living in this kernel rather than at a URL, shared by both widgets.

    `name -> bytes`, which a track then refers to by that name as if it were a
    URL. ipywidgets lifts bytes values out of the state dict and ships them as
    binary buffers, so this pays no JSON/base64 overhead.
    """

    local_files = traitlets.Dict(value_trait=traitlets.Bytes()).tag(sync=True)

    def add_local_file(self, path: str | Path, name: str | None = None) -> str:
        """Push a file from this kernel into the browser, and return its name.

        The way to show data too big to inline. `add_features` puts every row in
        the widget's state as JSON — fine for a few thousand, ~20MB by 200k —
        whereas a file registered here is read *by byte range*, so an indexed
        file stays indexed and the view only ever touches the bytes for the
        region on screen. No web server, no CORS, no public bucket.

        Refer to it afterwards exactly as you would a URL, so track-type
        inference and index-sibling derivation work unchanged::

            view.add_local_file("peaks.bed.gz")     # picks up peaks.bed.gz.tbi
            view.add_track("peaks.bed.gz")

        A conventional sibling index (`.tbi`/`.csi`/`.bai`/`.crai`) next to
        `path` is registered too, since that is the name the adapter asks for.
        Write the file with whatever you already use — pysam's `tabix_index`,
        pyBigWig, `bedGraphToBigWig` — then hand it over here.
        """
        path = Path(path)
        name = name or path.name
        files = {name: path.read_bytes()}
        for suffix in (".tbi", ".csi", ".bai", ".crai", ".fai", ".gzi"):
            index = path.with_name(path.name + suffix)
            if index.exists():
                files[name + suffix] = index.read_bytes()
        # one assignment: traitlets syncs per trait, so mutating in place would
        # never reach the browser
        self.local_files = {**self.local_files, **files}
        return name



class LinearGenomeView(_LocalFilesMixin, anywidget.AnyWidget):
    _esm = _STATIC / "index.js"
    _css = _STATIC / "jbrowse-anywidget.css"

    # Config, pushed Python -> JS. tracks/default_session are JBrowse config
    # dicts; a change to them updates the view. assembly is a config dict, a hub
    # name ("hg38", "GCF_..."), or a sequence-file URL — the JS side fetches or
    # builds an assembly from the latter two.
    assembly = traitlets.Union(
        [traitlets.Unicode(), traitlets.Dict()], default_value={}
    ).tag(sync=True)
    tracks = traitlets.List().tag(sync=True)
    default_session = traitlets.Dict().tag(sync=True)
    aggregate_text_search_adapters = traitlets.List().tag(sync=True)
    plugins = traitlets.List().tag(sync=True)


    # The visible region, synced both ways. Reading it after the user has panned
    # gives back their current location.
    location = traitlets.Unicode("").tag(sync=True)

    # Read-back only (JS -> Python): the most recently clicked feature, as a
    # plain dict. `None` until the user selects one. Observe it to react to
    # clicks, e.g. `view.observe(handler, "selected_feature")`.
    selected_feature = traitlets.Dict(default_value=None, allow_none=True).tag(
        sync=True
    )

    def __init__(
        self,
        assembly: str | JsonDict | None = None,
        location: str = "",
        tracks: list[TrackEntry] | None = None,
        default_session: JsonDict | None = None,
        plugins: list[str | JsonDict] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if assembly is not None:
            self.assembly = assembly
        if tracks is not None:
            self.tracks = list(tracks)
        if default_session is not None:
            self.default_session = default_session
        if plugins is not None:
            self.plugins = [plugin(p) for p in plugins]
        if location:
            self.location = location

    def add_track(self, track: TrackEntry) -> None:
        """Add a track and open it in the view.

        `track` is anything a `tracks=[...]` entry can be: a bare data-file URI,
        a `(uri, index)` pair, or a full JBrowse track config dict — the same
        JSON you'd put in a config file, so every track type and adapter works
        with no Python wrapper. Pick one out of a `fetch_hub(...)` catalog, or::

            view.add_track(".../reads.cram")
            view.add_track({
                "type": "AlignmentsTrack", "trackId": "reads", "name": "reads",
                "assemblyNames": ["hg38"],
                "adapter": {"type": "CramAdapter", "uri": ".../reads.cram"},
            })
        """
        self.tracks = [*self.tracks, track]


    def add_features(
        self,
        features: FeatureSource,
        name: str = "features",
        track_id: str | None = None,
        assembly_name: str | None = None,
        color: str | None = None,
        quantitative: bool | None = None,
    ) -> None:
        """Add an in-memory feature track from a pandas DataFrame or list of dicts.

        This is the analysis-ready path — the one thing JSON config can't do
        itself: hand it the result of a computation and it becomes a track with
        no file written. Rows need at least refName (or chrom/chr), start, end
        (start/end are 0-based half-open); any other columns ride along onto each
        feature and show in its details. `color` sets the feature fill — a CSS
        color, or a `jexl:` expression over those columns, e.g.
        "jexl:get(feature,'score') > 0 ? 'red' : 'blue'".

        A `score` column makes this a wiggle — see `features_track`, which
        builds the config this sends.

        Inlining puts every row in the widget's state as JSON, which is right up
        to a few thousand and stops scaling well past that; `add_local_file` is
        the route for anything bigger.
        """
        track_id = track_id if track_id else _slug(name)
        if any(t.get("trackId") == track_id for t in self.tracks):
            # two tracks sharing a trackId collide in the view; calling this
            # twice with the default name is the easy way into that
            raise ValueError(
                f'a track with trackId "{track_id}" is already on this view; '
                "pass a different name= or track_id="
            )
        self.add_track(
            features_track(
                features,
                name=name,
                track_id=track_id,
                assembly_name=assembly_name,
                color=color,
                quantitative=quantitative,
            )
        )

    @traitlets.validate("tracks")
    def _normalize_tracks(self, proposal: Any) -> list[JsonDict]:
        # Each entry is a full JBrowse track config dict, a bare data-file URI,
        # or a (uri, index) pair — so tracks=["a.bw", ("s.bam", "s.bai")] just
        # works. Only the pair needs unpacking here — JSON has no tuple, so it
        # would reach the view as a 2-element array read as a config; the view
        # takes a bare URI string itself.
        #
        # assemblyNames is deliberately NOT filled in here. The view stamps its
        # own resolved assembly onto any track that omits it, and knows that
        # name even when `assembly=` was a hub name it had to fetch — which this
        # side could only guess at. Stamping here also could not survive
        # `view.assembly = ...`: the view only fills an ABSENT assemblyNames, so
        # the stale stamp won and the track silently stopped displaying.
        return [_normalize_track(item) for item in proposal["value"]]


class JBrowseApp(_LocalFilesMixin, anywidget.AnyWidget):
    """The full JBrowse 2 app — any number of views of any type, declared up front.

    Where `LinearGenomeView` shows a single linear view, this drives the whole
    app engine, so `views=[...]` can mix a `LinearGenomeView`, a
    `LinearSyntenyView`, a `DotplotView`, and more. Each entry is a
    ``{"type", "init"}`` dict — the same vocabulary JBrowse Web serializes into
    its ``?session=spec-…`` URLs — built most easily with the `linear_view`,
    `synteny_view`, and `dotplot_view` helpers::

        view = JBrowseApp(
            assemblies=[{"name": "hg38", "uri": ...}, {"name": "mm39", "uri": ...}],
            tracks=[synteny_track("hg38_mm39.paf", "hg38", "mm39")],
            views=[synteny_view(["hg38", "mm39"], tracks=["hg38_mm39.paf"])],
        )

    Unlike `LinearGenomeView`, `tracks` here are full JBrowse track config dicts
    (a synteny track spans two assemblies, so there's no single-assembly
    shorthand to infer); `synteny_track` builds the common PAF case. An
    `assemblies` entry may be a hub name, though::

        JBrowseApp(assemblies=["hg38", "mm39"], views=[...])

    `add_local_file` works here too, so a track config can name a file from
    this kernel instead of a URL.

    `plugins=[...]` loads JBrowse plugins at runtime (see `plugin`), which is
    how view types that don't ship in the bundle — a 3D protein structure, an
    MSA — become available to `views`. Open those with the generic `view`, whose
    init fields are the plugin's own::

        JBrowseApp(
            assemblies=[hg38],
            plugins=["Protein3d"],
            views=[view("ProteinView", url=".../AF-P04637-F1-model_v6.cif")],
        )
    """

    _esm = _STATIC / "app.js"
    _css = _STATIC / "jbrowse-anywidget.css"

    # Config, pushed Python -> JS. Each `assemblies` entry is a config dict, a
    # hub name ("hg38", "GCF_..."), or a sequence-file URL, the same vocabulary
    # LinearGenomeView's `assembly` takes -- the JS side resolves all four, so
    # `fetch_hub` is a convenience here rather than a requirement. `views` is
    # the [{type, init}] list of views to open. A change to any rebuilds.
    assemblies = traitlets.List().tag(sync=True)
    tracks = traitlets.List().tag(sync=True)
    views = traitlets.List().tag(sync=True)
    plugins = traitlets.List().tag(sync=True)

    # A whole session snapshot to open instead of `views` — the plain JSON
    # JBrowse serializes its own state into, so a layout arranged by hand (or
    # saved from an earlier run) replays exactly. Unlike the config traits above
    # this swaps the session in place rather than rebuilding, and `views` stays
    # the app's own starting state, so File > New session returns there. Set it
    # to {} to go back to `views`.
    session = traitlets.Dict().tag(sync=True)

    # Read-back only (JS -> Python), one entry per view in `views`, updated as
    # the user pans/zooms — the same live sync the single-view LinearGenomeView
    # has, extended to every view. A linear view reports its visible region as a
    # locstring ("ctgA:1..5,000"); a synteny/dotplot view reports the list of its
    # two panels' locstrings. Observe it with `app.observe(handler, "view_locations")`.
    view_locations = traitlets.List().tag(sync=True)

    # Read-back only (JS -> Python): the live session, in the shape `session`
    # accepts, so an arrangement round-trips —
    # `JBrowseApp(..., session=saved)` where `saved = app.current_session`.
    # A separate trait from `session` on purpose: writing the live state back
    # into the input would echo, and would override the `views` a later change
    # is meant to show. Updated on the coarse cadence described in app.ts —
    # which views exist, what each has open, where each is looking — not per pan
    # frame.
    current_session = traitlets.Dict().tag(sync=True)

    # Read-back only (JS -> Python): the most recently clicked feature, in any
    # view, as a plain dict. `None` until one is selected.
    selected_feature = traitlets.Dict(default_value=None, allow_none=True).tag(
        sync=True
    )

    def __init__(
        self,
        assemblies: list[JsonDict] | None = None,
        tracks: list[JsonDict] | None = None,
        views: list[JsonDict] | None = None,
        plugins: list[str | JsonDict] | None = None,
        session: JsonDict | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if assemblies is not None:
            self.assemblies = list(assemblies)
        if tracks is not None:
            self.tracks = list(tracks)
        if views is not None:
            self.views = list(views)
        if plugins is not None:
            self.plugins = [plugin(p) for p in plugins]
        if session is not None:
            self.session = session


PLUGIN_STORE = "https://jbrowse.org/plugin-store/plugins.json"

# every fetch here happens inside a notebook cell, where an untimed urlopen on a
# stalled connection hangs the kernel with nothing to show for it
_TIMEOUT = 30


@lru_cache(maxsize=1)
def _plugin_store() -> dict[str, JsonDict]:
    try:
        with urllib.request.urlopen(PLUGIN_STORE, timeout=_TIMEOUT) as response:
            catalog = json.load(response)
    except OSError as e:
        raise ValueError(
            f"could not reach the plugin store at {PLUGIN_STORE}: {e}"
        ) from e
    return {p["name"]: p for p in catalog["plugins"]}


def plugin(spec: str | JsonDict) -> JsonDict:
    """Resolve a plugin to the `{name, url}` spec the view loads at runtime.

    A dict is passed through (so an unlisted or locally-served plugin is just
    `{"name": ..., "url": ...}`); a string is looked up in the JBrowse
    [plugin store](https://jbrowse.org/jb2/plugin_store/) by name, which is how
    the web app's Tools -> Plugin store installs the same bundle::

        LinearGenomeView(assembly="hg38", plugins=["Protein3d", "MsaView"])

    A plugin registers its own view types, track types, and menu items, so the
    widget gains whatever it adds (a protein-structure view, an MSA view, ...).
    """
    if isinstance(spec, dict):
        return spec
    store = _plugin_store()
    entry = store.get(spec)
    if entry is None:
        raise ValueError(
            f'plugin "{spec}" not found in the plugin store. '
            f"Available: {', '.join(sorted(store))}"
        )
    return {"name": entry["name"], "url": entry["url"]}


def _normalize_track(item: TrackEntry) -> JsonDict:
    """Expand a `tracks=[...]` entry to a loose spec the view can consume.

    A bare data-file URI or a `(uri, index)` pair becomes `{"uri": ...}`; a dict
    (a loose spec, or a full JBrowse track config) is passed through untouched.
    """
    if isinstance(item, str):
        return {"uri": item}
    if isinstance(item, (tuple, list)):
        if len(item) != 2:
            raise ValueError(
                f"a track entry pair is (uri, index); got {len(item)} items: {item!r}"
            )
        uri, index = item
        return {"uri": uri, "index": index}
    return item


def features_track(
    features: FeatureSource,
    name: str = "features",
    track_id: str | None = None,
    assembly_name: str | None = None,
    color: str | None = None,
    quantitative: bool | None = None,
) -> JsonDict:
    """Build a track config from a DataFrame or list of dicts, inlining the rows.

    The builder behind `LinearGenomeView.add_features`, separate so the config
    can go anywhere a track config can — `JBrowseApp(tracks=[...])` included,
    which has no `add_features` of its own.

    Rows need refName (or chrom/chr), start, end (0-based half-open); every
    other column rides onto its feature. `color` is a CSS color or a `jexl:`
    expression over those columns.

    A **`score`** column makes this a `QuantitativeTrack` — a real wiggle, with
    a value axis and autoscaling, rather than boxes to color by hand. `score` is
    JBrowse's own name for the plotted value, so a column called `depth` or
    `signal` will not do it; rename, or pass `quantitative=` to decide outright.

    `assembly_name` is only needed to pin the track to something other than the
    view's own assembly, which it otherwise picks up.
    """
    track_id = track_id if track_id else _slug(name)
    rows = _to_features(features, track_id)
    if quantitative is None:
        quantitative = any("score" in row for row in rows)
    track: JsonDict = {
        "type": "QuantitativeTrack" if quantitative else "FeatureTrack",
        "trackId": track_id,
        "name": name,
        "adapter": {"type": "FromConfigAdapter", "features": rows},
    }
    if assembly_name:
        track["assemblyNames"] = [assembly_name]
    if color:
        # the color slot lives on the display, and each track type has its own;
        # displayId is derived from the trackId by core, so it stays out
        display = "LinearWiggleDisplay" if quantitative else "LinearBasicDisplay"
        track["displays"] = [{"type": display, "color": color}]
    return track


def _to_features(features: FeatureSource, track_id: str) -> list[JsonDict]:
    rows = _rows(features)
    out = []
    for i, row in enumerate(rows):
        refname = row.get("refName", row.get("chrom", row.get("chr")))
        if refname is None:
            raise ValueError("each feature needs a refName (or chrom/chr) column")
        missing = [c for c in ("start", "end") if c not in row]
        if missing:
            raise ValueError(
                f"feature {i} is missing the {' and '.join(missing)} column"
            )
        feature = {
            k: _json_safe(v) for k, v in row.items() if k not in ("chrom", "chr")
        }
        feature["refName"] = refname
        feature["start"] = int(row["start"])
        feature["end"] = int(row["end"])
        feature["uniqueId"] = f"{track_id}-{i}"
        out.append(feature)
    return out


def _json_safe(value: Any) -> Any:
    # a missing value in a pandas column arrives as float NaN, which json.dumps
    # writes as bare `NaN` — invalid JSON that the kernel's packer rejects, so
    # one empty cell would break the whole sync. null is what JSON has instead.
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def _rows(features: FeatureSource) -> list[JsonDict]:
    # Accept a pandas DataFrame without importing pandas as a hard dependency.
    if hasattr(features, "to_dict"):
        return features.to_dict(orient="records")
    return list(features)


def _drop_none(blob: JsonDict) -> JsonDict:
    # a config blob carries only the fields that were set; an absent one is
    # omitted rather than sent as null, so core's own default applies
    return {k: v for k, v in blob.items() if v is not None}


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in str(text).lower()).strip("-")


def _clean_uri(uri: str) -> str:
    return re.split(r"[?#]", uri, maxsplit=1)[0]


_GENOMES = "https://jbrowse.org"


def fetch_hub(hub: str) -> JsonDict:
    """Fetch a hosted assembly config from jbrowse.org.

    `hub` is a UCSC database name (``hg38``, ``hg19``, ``mm10``, …) or a GenArk
    accession (``GCA_...``/``GCF_...``). Returns the full config dict — a
    self-contained assembly (remote sequence, refName aliases, cytobands) plus a
    catalog of hosted tracks, all CORS-enabled — which is the easy way to get
    human/model-organism data without hunting for files. Pull the single
    assembly out of it for ``LinearGenomeView(assembly=...)``::

        hub = fetch_hub("hg38")
        view = LinearGenomeView(
            assembly=hub["assemblies"][0],
            aggregate_text_search_adapters=hub["aggregateTextSearchAdapters"],
        )
    """
    match = re.match(r"^(GC[AF])_(\d{3})(\d{3})(\d{3})", hub)
    if match:
        a, b, c, d = match.groups()
        url = f"{_GENOMES}/hubs/genark/{a}/{b}/{c}/{d}/{hub}/config.json"
    else:
        url = f"{_GENOMES}/ucsc/{hub}/config.json"
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as response:
            config = json.load(response)
    except urllib.error.HTTPError as e:
        raise ValueError(
            f'hub "{hub}" not found ({e.code} from {url}). '
            "See https://genomes.jbrowse.org for available assemblies."
        ) from e
    except OSError as e:
        # a DNS failure, refused connection, or timeout — not a missing hub
        raise ValueError(f'could not fetch hub "{hub}" from {url}: {e}') from e
    # Hosted configs reference data with URIs relative to the config's own
    # location; stamp each with baseUri so they resolve (the same pass
    # jbrowse-web runs when it loads a config from a URL).
    _stamp_base_uri(config, url)
    return config


def _stamp_base_uri(node: Any, base: str) -> None:
    if isinstance(node, dict):
        # fill baseUri when absent — mirror jbrowse-web's `baseUri ?? base` (and
        # stampBaseUri.ts) so a node carrying an explicit null baseUri still
        # resolves; a bare `in` check would wrongly treat that as already-stamped
        if "uri" in node and node.get("baseUri") is None:
            node["baseUri"] = base
        for value in node.values():
            _stamp_base_uri(value, base)
    elif isinstance(node, list):
        for value in node:
            _stamp_base_uri(value, base)
