"""JBrowse 2 linear genome view as an anywidget.

Renders in Jupyter, JupyterLab, VS Code, Colab, and marimo from a single bundle,
and supports two-way sync of the visible region between Python and the view.

The interface is JBrowse's own config: assemblies, tracks, and sessions are the
same JSON-like dicts documented at https://jbrowse.org/jb2/docs/config_guide/,
handed straight to the view. `assembly=` also accepts a hub name (``"hg38"``,
``"GCF_..."``) the view fetches and resolves, or a bare sequence-file URL
(``".../hg38.fa.gz"``, ``.2bit``) it builds an assembly from — so `make_assembly`
is only needed for aliases or a non-sibling index. Python adds only what JSON
can't express itself — turning an in-memory DataFrame into a track
(`add_features`) and a little assembly boilerplate (`make_assembly`).

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

`track(uri)` is the same expansion made explicit, for when you want to set a
name or extra config; a `(uri, index)` pair names a non-sibling index inline.
"""

from __future__ import annotations

import json
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

__all__ = ["LinearGenomeView", "track", "make_assembly", "fetch_hub"]

# A JBrowse config object (assembly, track, adapter, …): plain JSON as a dict.
JsonDict = dict[str, Any]
# A `tracks=[...]` entry: a full/loose config dict, a bare data-file URI, or a
# `(uri, index)` pair.
TrackEntry = Union[str, "tuple[str, str]", JsonDict]
# What `add_features` accepts: a pandas DataFrame or a sequence of row mappings.
FeatureSource = Union["pd.DataFrame", "Iterable[Mapping[str, Any]]"]


class LinearGenomeView(anywidget.AnyWidget):
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
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        if assembly is not None:
            self.assembly = assembly
        if tracks is not None:
            self.tracks = list(tracks)
        if default_session is not None:
            self.default_session = default_session
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
    ) -> None:
        """Add an in-memory feature track from a pandas DataFrame or list of dicts.

        This is the analysis-ready path — the one thing JSON config can't do
        itself: hand it the result of a computation and it becomes a track with
        no file written. Rows need at least refName (or chrom/chr), start, end
        (start/end are 0-based half-open); any other columns ride along onto each
        feature and show in its details. `color` sets the feature fill — a CSS
        color, or a `jexl:` expression over those columns, e.g.
        "jexl:get(feature,'score') > 0 ? 'red' : 'blue'".
        """
        track_id = track_id if track_id else _slug(name)
        track = {
            "type": "FeatureTrack",
            "trackId": track_id,
            "name": name,
            "assemblyNames": [self._assembly_name(assembly_name)],
            "adapter": {
                "type": "FromConfigAdapter",
                "features": _to_features(features, track_id),
            },
        }
        if color:
            track["displays"] = [
                {
                    "type": "LinearBasicDisplay",
                    "displayId": f"{track_id}-LinearBasicDisplay",
                    "color": color,
                }
            ]
        self.add_track(track)

    def _resolved_assembly_name(self) -> str | None:
        # A config dict carries its name under "name". A string is either a
        # sequence-file URL the view builds an assembly from (name derived from
        # the file, matching makeAssembly) or a hub name that is itself the
        # resolved name. Returns None when unset.
        if isinstance(self.assembly, str):
            if not self.assembly:
                return None
            if _is_sequence_uri(self.assembly):
                return _assembly_name_from_uri(self.assembly)
            return self.assembly
        return self.assembly.get("name") or None

    def _assembly_name(self, assembly_name: str | None) -> str:
        name = assembly_name or self._resolved_assembly_name()
        if not name:
            raise ValueError("no assembly set; pass assembly_name=")
        return name

    @traitlets.validate("tracks")
    def _normalize_tracks(self, proposal: Any) -> list[JsonDict]:
        # Each entry is a full JBrowse track config dict, a bare data-file URI,
        # or a (uri, index) pair — so tracks=["a.bw", ("s.bam", "s.bai")] just
        # works; the bare/pair forms become loose {"uri": ...} specs the view
        # expands. Then backfill assemblyNames from the view's own assembly,
        # since repeating it on every track is noise; an explicit assemblyNames
        # (e.g. a synteny track) is left untouched.
        name = self._resolved_assembly_name()
        out = []
        for item in proposal["value"]:
            conf = _normalize_track(item)
            if name and not conf.get("assemblyNames"):
                conf = {**conf, "assemblyNames": [name]}
            out.append(conf)
        return out


def make_assembly(
    name: str,
    fasta_uri: str,
    fai_uri: str | None = None,
    gzi_uri: str | None = None,
    aliases: list[str] | None = None,
    refname_aliases_uri: str | None = None,
) -> JsonDict:
    """Build an assembly config dict for an (optionally bgzipped) indexed FASTA.

    A convenience over writing the assembly JSON by hand; the return value is a
    plain dict you can edit or pass as `assembly=`. `refname_aliases_uri` points
    at a tab-separated aliases file (as UCSC publishes) so a track whose
    reference names differ from the FASTA — e.g. a BAM using `chr1` against a
    `1`-named reference — still lines up.
    """
    bgzipped = fasta_uri.endswith(".gz")
    adapter_type = "BgzipFastaAdapter" if bgzipped else "IndexedFastaAdapter"
    if fai_uri or gzi_uri:
        # a custom index location needs the longhand slots; the `uri` shorthand
        # would derive (and override) faiLocation/gziLocation from the fasta uri
        adapter = {
            "type": adapter_type,
            "fastaLocation": {"uri": fasta_uri},
            "faiLocation": {"uri": fai_uri if fai_uri else fasta_uri + ".fai"},
        }
        if bgzipped:
            adapter["gziLocation"] = {"uri": gzi_uri if gzi_uri else fasta_uri + ".gzi"}
    else:
        # JBrowse derives the .fai (and .gzi) sibling from `uri`
        adapter = {"type": adapter_type, "uri": fasta_uri}
    assembly = {
        "name": name,
        "aliases": aliases if aliases else [],
        "sequence": {
            "type": "ReferenceSequenceTrack",
            "trackId": f"{name}-ReferenceSequenceTrack",
            "adapter": adapter,
        },
    }
    if refname_aliases_uri:
        assembly["refNameAliases"] = {
            "adapter": {
                "type": "RefNameAliasAdapter",
                "uri": refname_aliases_uri,
            }
        }
    return assembly


def _normalize_track(item: TrackEntry) -> JsonDict:
    """Expand a `tracks=[...]` entry to a loose spec the view can consume.

    A bare data-file URI or a `(uri, index)` pair becomes `{"uri": ...}`; a dict
    (a loose spec, or a full JBrowse track config) is passed through untouched.
    """
    if isinstance(item, str):
        return {"uri": item}
    if isinstance(item, (tuple, list)):
        uri, index = item
        return {"uri": uri, "index": index}
    return item


def track(
    uri: str,
    name: str | None = None,
    track_id: str | None = None,
    assembly_name: str | None = None,
    index: str | None = None,
    **extra: Any,
) -> JsonDict:
    """Describe a track by its data-file URI (the declarative shorthand).

    Returns a loose spec — `{"uri": uri}` plus whatever you pass — that the view
    expands into a full track config when it loads, inferring the track type and
    adapter from the file extension with JBrowse's own format plugins (the same
    inference the "Add track" flow uses). No extension table lives here, so every
    format a bundled plugin recognizes works: .bam/.cram, .bw/.bigwig,
    .bb/.bigbed, .vcf(.gz), .gff(.gz)/.gff3(.gz), .gtf(.gz), .bed(.gz), .hic, and
    more; a bgzipped file resolves to its indexed adapter, a plain one to the
    whole-file adapter.

    Extra keyword args ride onto the resulting config and override the inferred
    defaults, so a display name, color, category — even a `type` override — is
    just a keyword; it's the same JBrowse config JSON, not a Python wrapper::

        track("https://.../reads.cram", name="Tumor")
        track("https://.../peaks.bed.gz", category=["Genes"])

    `index=` names a non-sibling index (a `.csi` index is detected by extension);
    otherwise the adapter derives its `.bai`/`.crai`/`.tbi` sibling from the uri.
    `assembly_name=` sets assemblyNames; left off, the view backfills it from its
    own assembly.
    """
    spec = {"uri": uri, **extra}
    if name is not None:
        spec["name"] = name
    if track_id is not None:
        spec["trackId"] = track_id
    if index is not None:
        spec["index"] = index
    if assembly_name is not None:
        spec["assemblyNames"] = [assembly_name]
    return spec


def _to_features(features: FeatureSource, track_id: str) -> list[JsonDict]:
    rows = _rows(features)
    out = []
    for i, row in enumerate(rows):
        refname = row.get("refName", row.get("chrom", row.get("chr")))
        if refname is None:
            raise ValueError("each feature needs a refName (or chrom/chr) column")
        feature = {k: v for k, v in row.items() if k not in ("chrom", "chr")}
        feature["refName"] = refname
        feature["start"] = int(row["start"])
        feature["end"] = int(row["end"])
        feature["uniqueId"] = f"{track_id}-{i}"
        out.append(feature)
    return out


def _rows(features: FeatureSource) -> list[JsonDict]:
    # Accept a pandas DataFrame without importing pandas as a hard dependency.
    if hasattr(features, "to_dict"):
        return features.to_dict(orient="records")
    return list(features)


def _slug(text: str) -> str:
    return "".join(c if c.isalnum() else "-" for c in str(text).lower()).strip("-")


# sequence extensions the view's own guesser recognizes; kept in sync with
# makeAssembly.ts in @jbrowse/embedded-linear-genome-view
_SEQUENCE_EXT_RE = re.compile(r"\.(fa|fasta|fas|fna|mfa|2bit)(\.b?gz)?$", re.I)


def _clean_uri(uri: str) -> str:
    return re.split(r"[?#]", uri, maxsplit=1)[0]


def _is_sequence_uri(uri: str) -> bool:
    # true when a string names a sequence file (vs. a hub name like "hg38")
    return bool(_SEQUENCE_EXT_RE.search(_clean_uri(uri)))


def _assembly_name_from_uri(uri: str) -> str:
    # strip path and sequence extension: ".../hg19.fa.gz" -> "hg19"
    return _SEQUENCE_EXT_RE.sub("", _clean_uri(uri).rstrip("/").rsplit("/", 1)[-1])


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
        with urllib.request.urlopen(url) as response:
            config = json.load(response)
    except urllib.error.HTTPError as e:
        raise ValueError(
            f'hub "{hub}" not found ({e.code} from {url}). '
            "See https://genomes.jbrowse.org for available assemblies."
        ) from e
    # Hosted configs reference data with URIs relative to the config's own
    # location; stamp each with baseUri so they resolve (the same pass
    # jbrowse-web runs when it loads a config from a URL).
    _stamp_base_uri(config, url)
    return config


def _stamp_base_uri(node: Any, base: str) -> None:
    if isinstance(node, dict):
        if "uri" in node and "baseUri" not in node:
            node["baseUri"] = base
        for value in node.values():
            _stamp_base_uri(value, base)
    elif isinstance(node, list):
        for value in node:
            _stamp_base_uri(value, base)
