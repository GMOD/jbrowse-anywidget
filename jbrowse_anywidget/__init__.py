"""JBrowse 2 as an anywidget, for Jupyter, JupyterLab, VS Code, Colab and marimo.

A widget's options are the JBrowse product's own, passed through verbatim:
`LinearGenomeView(**options)` takes what `createLinearGenomeView` takes and
`JBrowseApp(**options)` what `createApp` takes, with JBrowse's camelCase keys.
Nothing here names them, so an option JBrowse adds works with no change here::

    view = LinearGenomeView(
        assembly="hg38",
        location="BRCA1",
        tracks=["https://.../ncbiRefSeq.sort.gff.gz"],
    )
    view.update(location="TP53")

Python adds only what JSON cannot express: bytes from this kernel
(`add_local_file`), a DataFrame as a track config (`features_track`), and a
hosted config fetched and stamped with its base URI (`fetch_hub`).
"""

from __future__ import annotations

import json
import math
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import TYPE_CHECKING, Any, Union

import anywidget
import traitlets

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    import pandas as pd

_STATIC = Path(__file__).parent / "static"

__all__ = ["LinearGenomeView", "JBrowseApp", "features_track", "fetch_hub"]

JsonDict = dict[str, Any]
FeatureSource = Union["pd.DataFrame", "Iterable[Mapping[str, Any]]"]


def _sync_traits(widget: Any) -> set[str]:
    """The traits this widget syncs to JS, excluding ipywidgets' own.

    The trait-contract test and the screenshot harness both derive the set from
    here, so neither keeps a list of its own.
    """
    names: set[str] = set()
    for cls in type(widget).__mro__:
        if cls is anywidget.AnyWidget:
            break
        names |= set(cls.class_own_traits(sync=True))
    return {name for name in names if not name.startswith("_")}


class _Widget(anywidget.AnyWidget):
    _css = _STATIC / "jbrowse-anywidget.css"

    options = traitlets.Dict().tag(sync=True)
    # name -> bytes, which tracks then refer to by name as if it were a URL.
    # ipywidgets sends bytes as binary buffers rather than JSON.
    local_files = traitlets.Dict(value_trait=traitlets.Bytes()).tag(sync=True)
    current_session = traitlets.Dict().tag(sync=True)
    selected_feature = traitlets.Dict(default_value=None, allow_none=True).tag(
        sync=True
    )

    def __init__(self, **options: Any) -> None:
        super().__init__(options=options)

    def update(self, **changes: Any) -> None:
        """Merge `changes` into `options`.

        The view applies only the keys whose values changed, in place where
        JBrowse can (a linear view's `tracks` and `location`, an app's
        `session`) and by rebuilding otherwise::

            view.update(tracks=[*view.options["tracks"], features_track(df)])
        """
        self.options = {**self.options, **changes}

    def add_local_file(self, path: str | Path, name: str | None = None) -> str:
        """Push a file from this kernel into the browser, and return its name.

        The browser reads it by byte range, so an indexed file stays indexed. A
        sibling index (`.tbi`, `.csi`, `.bai`, `.crai`, `.fai`, `.gzi`) is
        registered too. Use the returned name where a track takes a URL::

            view.update(tracks=[view.add_local_file("peaks.bed.gz")])
        """
        path = Path(path)
        name = name or path.name
        files = {name: path.read_bytes()}
        for suffix in (".tbi", ".csi", ".bai", ".crai", ".fai", ".gzi"):
            index = path.with_name(path.name + suffix)
            if index.exists():
                files[name + suffix] = index.read_bytes()
        self.local_files = {**self.local_files, **files}
        return name


class LinearGenomeView(_Widget):
    """One linear genome view; options are `createLinearGenomeView`'s.

    `location` reads back the region in view, and `current_session` the layout
    in the shape the `session` option takes.
    """

    _esm = _STATIC / "index.js"

    location = traitlets.Unicode("").tag(sync=True)


class JBrowseApp(_Widget):
    """The full JBrowse app; options are `createApp`'s.

    `views` holds any view type, each a `{"type", ...settings}` dict::

        JBrowseApp(
            assemblies=[{"name": "hg38", "uri": ...}, {"name": "mm39", "uri": ...}],
            tracks=[{"type": "SyntenyTrack", "trackId": "hg38_mm39", "adapter": ...}],
            views=[{
                "type": "LinearSyntenyView",
                "views": [{"assembly": "hg38"}, {"assembly": "mm39"}],
                "tracks": ["hg38_mm39"],
            }],
        )

    `view_locations` reads back where each view is looking.
    """

    _esm = _STATIC / "app.js"

    view_locations = traitlets.List().tag(sync=True)


# an untimed urlopen on a stalled connection hangs the notebook cell
_TIMEOUT = 30


def features_track(
    features: FeatureSource,
    name: str = "features",
    track_id: str | None = None,
    assembly_name: str | None = None,
    color: str | None = None,
    quantitative: bool | None = None,
    **config: Any,
) -> JsonDict:
    """Build a track config from a DataFrame or list of dicts, inlining the rows.

    Rows need refName (or chrom/chr), start, end (0-based half-open); every
    other column rides onto its feature. `color` is a CSS color or a `jexl:`
    expression over those columns.

    A **`score`** column makes this a `QuantitativeTrack` — a real wiggle, with
    a value axis and autoscaling, rather than boxes to color by hand. `score` is
    JBrowse's own name for the plotted value, so a column called `depth` or
    `signal` will not do it; rename, or pass `quantitative=` to decide outright.

    Any other keyword is track config merged on top, so a `displays` list plots
    the columns the way a grammar of graphics does — a `LinearMarkDisplay`
    with a `y` field and a colour scale::

        features_track(
            de,
            name="differential expression",
            displays=[{
                "type": "LinearMarkDisplay",
                "marks": [{
                    "shape": "point",
                    "encoding": {
                        "y": "log2fc",
                        "color": {"field": "sig", "scale": "categorical"},
                    },
                }],
            }],
        )

    The rows travel as JSON, which suits a few thousand; `add_local_file` is
    the route for more. `assembly_name` is only needed to pin the track to an
    assembly other than the view's own.
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
        display = "LinearWiggleDisplay" if quantitative else "LinearBasicDisplay"
        track["displays"] = [{"type": display, "color": color}]
    return {**track, **config}


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
    # A NaN, a numpy scalar or a Timestamp breaks the whole sync at display
    # time, with an error naming the packer rather than the column.
    if hasattr(value, "item") and not isinstance(value, (str, bytes)):
        value = value.item()
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    return str(value)


def _rows(features: FeatureSource) -> list[JsonDict]:
    if hasattr(features, "to_dict"):
        return features.to_dict(orient="records")
    return list(features)


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in str(text).lower()).strip("-")


_GENOMES = "https://jbrowse.org"


def fetch_hub(hub: str) -> JsonDict:
    """Fetch a hosted assembly config from jbrowse.org, or any config.json URL.

    `hub` is a UCSC database name (``hg38``, ``hg19``, ``mm10``, …), a GenArk
    accession (``GCA_...``/``GCF_...``), or the ``http(s)://`` URL of any
    config.json. Returns the full config dict — a self-contained assembly
    (remote sequence, refName aliases, cytobands) plus a catalog of hosted
    tracks, all CORS-enabled — which is the easy way to get human/model-organism
    data without hunting for files. Relative URIs in it are stamped to resolve
    against the config's own URL::

        hub = fetch_hub("hg38")
        view = LinearGenomeView(
            assembly=hub["assemblies"][0],
            aggregateTextSearchAdapters=hub["aggregateTextSearchAdapters"],
        )
    """
    match = re.match(r"^(GC[AF])_(\d{3})(\d{3})(\d{3})", hub)
    if hub.startswith(("http://", "https://")):
        url = hub
    elif match:
        a, b, c, d = match.groups()
        url = f"{_GENOMES}/hubs/genark/{a}/{b}/{c}/{d}/{hub}/config.json"
    else:
        url = f"{_GENOMES}/ucsc/{hub}/config.json"
    try:
        with urllib.request.urlopen(url, timeout=_TIMEOUT) as response:
            config = json.load(response)
    except urllib.error.HTTPError as e:
        hint = "" if url == hub else " See https://genomes.jbrowse.org for hubs."
        raise ValueError(f'hub "{hub}" not found ({e.code} from {url}).{hint}') from e
    except OSError as e:
        raise ValueError(f'could not fetch hub "{hub}" from {url}: {e}') from e
    _stamp_base_uri(config, url)
    return config


def _stamp_base_uri(node: Any, base: str) -> None:
    if isinstance(node, dict):
        # `baseUri ?? base`, as stampBaseUri.ts does: an explicit null is stamped
        if "uri" in node and node.get("baseUri") is None:
            node["baseUri"] = base
        for value in node.values():
            _stamp_base_uri(value, base)
    elif isinstance(node, list):
        for value in node:
            _stamp_base_uri(value, base)
