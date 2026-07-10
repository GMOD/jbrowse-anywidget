"""JBrowse 2 linear genome view as an anywidget.

Renders in Jupyter, JupyterLab, VS Code, Colab, and marimo from a single bundle,
and supports two-way sync of the visible region between Python and the view.

The interface is JBrowse's own config: assemblies, tracks, and sessions are the
same JSON-like dicts documented at https://jbrowse.org/jb2/docs/config_guide/,
handed straight to the view. `assembly=` also accepts a hub name (``"hg38"``,
``"GCF_..."``) that the view fetches and resolves. Python adds only what JSON
can't express itself — turning an in-memory DataFrame into a track
(`add_features`) and a little assembly boilerplate (`make_assembly`).

For the common case, `track(uri)` infers the track type and adapter from the
file extension — the declarative shorthand `@jbrowse/img`'s `--bam`/`--bigwig`
flags give the CLI — so a whole view is one flat, config-free call::

    view = LinearGenomeView(
        assembly="hg38",
        location="10:29,838,565..29,838,850",
        tracks=[
            track("https://.../ncbiRefSeq.sort.gff.gz"),
            track("https://.../phyloP100way.bw"),
            track("https://.../reads.cram"),
        ],
    )
"""

import json
import re
import urllib.request
from pathlib import Path

import anywidget
import traitlets

_STATIC = Path(__file__).parent / "static"

__all__ = ["LinearGenomeView", "track", "make_assembly", "fetch_hub"]


class LinearGenomeView(anywidget.AnyWidget):
    _esm = _STATIC / "index.js"
    _css = _STATIC / "jbrowse-anywidget.css"

    # Config, pushed Python -> JS. tracks/default_session are JBrowse config
    # dicts; a change to them updates the view. assembly is either a config dict
    # or a hub name ("hg38", "GCF_..."), which the JS side fetches and resolves.
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
        assembly=None,
        location="",
        tracks=None,
        default_session=None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if assembly is not None:
            self.assembly = assembly
        if tracks is not None:
            self.tracks = list(tracks)
        if default_session is not None:
            self.default_session = default_session
        if location:
            self.location = location

    def add_track(self, track):
        """Add a JBrowse track config dict; it opens in the view.

        `track` is any JBrowse track config — the same JSON you'd put in a
        config file — so every track type and adapter works with no Python
        wrapper. Pick one out of a `fetch_hub(...)` catalog, or write your own::

            view.add_track({
                "type": "AlignmentsTrack", "trackId": "reads", "name": "reads",
                "assemblyNames": ["hg38"],
                "adapter": {"type": "CramAdapter", "uri": ".../reads.cram"},
            })
        """
        self.tracks = [*self.tracks, track]

    def add_features(
        self,
        features,
        name="features",
        track_id=None,
        assembly_name=None,
        color=None,
    ):
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

    def _resolved_assembly_name(self):
        # a hub-name string ("hg38") is both the input and the resolved name; a
        # config dict carries its name under "name". Returns None when unset.
        if isinstance(self.assembly, str):
            return self.assembly or None
        return self.assembly.get("name") or None

    def _assembly_name(self, assembly_name):
        name = assembly_name or self._resolved_assembly_name()
        if not name:
            raise ValueError("no assembly set; pass assembly_name=")
        return name

    @traitlets.validate("tracks")
    def _fill_assembly_names(self, proposal):
        # A track config needs assemblyNames, but making the caller repeat the
        # assembly on every track() is noise — backfill it from the view's own
        # assembly so tracks=[track(uri), ...] just works. Explicit
        # assemblyNames (e.g. a synteny track) is left untouched.
        name = self._resolved_assembly_name()
        tracks = proposal["value"]
        if name:
            return [
                t if t.get("assemblyNames") else {**t, "assemblyNames": [name]}
                for t in tracks
            ]
        return tracks


def make_assembly(
    name,
    fasta_uri,
    fai_uri=None,
    gzi_uri=None,
    aliases=None,
    refname_aliases_uri=None,
):
    """Build an assembly config dict for an (optionally bgzipped) indexed FASTA.

    A convenience over writing the assembly JSON by hand; the return value is a
    plain dict you can edit or pass as `assembly=`. `refname_aliases_uri` points
    at a tab-separated aliases file (as UCSC publishes) so a track whose
    reference names differ from the FASTA — e.g. a BAM using `chr1` against a
    `1`-named reference — still lines up.
    """
    bgzipped = fasta_uri.endswith(".gz")
    adapter = {
        "type": "BgzipFastaAdapter" if bgzipped else "IndexedFastaAdapter",
        "uri": fasta_uri,
        "faiLocation": {"uri": fai_uri if fai_uri else fasta_uri + ".fai"},
    }
    if bgzipped:
        adapter["gziLocation"] = {"uri": gzi_uri if gzi_uri else fasta_uri + ".gzi"}
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


# Extension → adapter, the same map jb2export applies to its --bam/--bigwig/…
# flags (products/jbrowse-img/src/makeConfigs.ts).
def _index_type(index_uri, default):
    return "CSI" if index_uri.endswith(".csi") else default


def _infer_adapter(uri, index):
    """Map a data-file URI to (track_type, adapter_dict) by extension."""
    lower = uri.split("?")[0].split("#")[0].lower()
    loc = {"uri": uri}
    if lower.endswith(".bam"):
        idx = index or uri + ".bai"
        return "AlignmentsTrack", {
            "type": "BamAdapter",
            "bamLocation": loc,
            "index": {"location": {"uri": idx}, "indexType": _index_type(idx, "BAI")},
        }
    if lower.endswith(".cram"):
        return "AlignmentsTrack", {
            "type": "CramAdapter",
            "cramLocation": loc,
            "craiLocation": {"uri": index or uri + ".crai"},
        }
    if lower.endswith((".bw", ".bigwig")):
        return "QuantitativeTrack", {"type": "BigWigAdapter", "bigWigLocation": loc}
    if lower.endswith((".bb", ".bigbed")):
        return "FeatureTrack", {"type": "BigBedAdapter", "bigBedLocation": loc}
    if lower.endswith(".hic"):
        return "HicTrack", {"type": "HicAdapter", "hicLocation": loc}
    if lower.endswith(".vcf.gz"):
        idx = index or uri + ".tbi"
        return "VariantTrack", {
            "type": "VcfTabixAdapter",
            "vcfGzLocation": loc,
            "index": {"location": {"uri": idx}, "indexType": _index_type(idx, "TBI")},
        }
    if lower.endswith((".gff.gz", ".gff3.gz")):
        idx = index or uri + ".tbi"
        return "FeatureTrack", {
            "type": "Gff3TabixAdapter",
            "gffGzLocation": loc,
            "index": {"location": {"uri": idx}, "indexType": _index_type(idx, "TBI")},
        }
    if lower.endswith(".bed.gz"):
        idx = index or uri + ".tbi"
        return "FeatureTrack", {
            "type": "BedTabixAdapter",
            "bedGzLocation": loc,
            "index": {"location": {"uri": idx}, "indexType": _index_type(idx, "TBI")},
        }
    raise ValueError(
        f"can't infer a track type from {uri!r}; supported extensions: "
        ".bam, .cram, .bw/.bigwig, .bb/.bigbed, .vcf.gz, .gff.gz/.gff3.gz, "
        ".bed.gz, .hic. For anything else write the track config dict directly."
    )


def track(uri, name=None, track_id=None, assembly_name=None, index=None):
    """Build a track config from a data-file URI, inferring type from extension.

    The declarative shorthand — the Python analog of jbrowse-img's `--bam`,
    `--bigwig`, `--cram` flags. Recognizes .bam, .cram, .bw/.bigwig, .bb/.bigbed,
    .vcf.gz, .gff.gz/.gff3.gz, .bed.gz, and .hic; index locations default to the
    conventional sibling (.bai/.crai/.tbi) and `index=` overrides them (a `.csi`
    index is detected by extension). Returns a plain JBrowse track config dict you
    can hand to `tracks=[...]` or `add_track` — so anything beyond the defaults
    (colors, display settings) is a key you add to it, the same JSON JBrowse's
    config guide documents, not another Python wrapper. `assemblyNames` is filled
    from the view's assembly when omitted, so `tracks=[track(uri), ...]` needs no
    per-track assembly.
    """
    track_type, adapter = _infer_adapter(uri, index)
    name = name if name else _basename(uri)
    conf = {
        "type": track_type,
        "trackId": track_id if track_id else _slug(name),
        "name": name,
        "adapter": adapter,
    }
    if assembly_name:
        conf["assemblyNames"] = [assembly_name]
    return conf


def _basename(uri):
    path = uri.split("?")[0].split("#")[0].rstrip("/")
    return path.rsplit("/", 1)[-1]


def _to_features(features, track_id):
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


def _rows(features):
    # Accept a pandas DataFrame without importing pandas as a hard dependency.
    if hasattr(features, "to_dict"):
        return features.to_dict(orient="records")
    return list(features)


def _slug(text):
    return "".join(c if c.isalnum() else "-" for c in str(text).lower()).strip("-")


_GENOMES = "https://jbrowse.org"


def fetch_hub(hub):
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


def _stamp_base_uri(node, base):
    if isinstance(node, dict):
        if "uri" in node and "baseUri" not in node:
            node["baseUri"] = base
        for value in node.values():
            _stamp_base_uri(value, base)
    elif isinstance(node, list):
        for value in node:
            _stamp_base_uri(value, base)
