"""JBrowse 2 linear genome view as an anywidget.

Renders in Jupyter, JupyterLab, VS Code, Colab, and marimo from a single bundle,
and supports two-way sync of the visible region between Python and the view.

The interface is JBrowse's own config: assemblies, tracks, and sessions are the
same JSON-like dicts documented at https://jbrowse.org/jb2/docs/config_guide/,
handed straight to the view. Python adds only what JSON can't express itself —
turning an in-memory DataFrame into a track (`add_features`) and a little
assembly boilerplate (`make_assembly`).
"""

from pathlib import Path

import anywidget
import traitlets

_STATIC = Path(__file__).parent / "static"

__all__ = ["LinearGenomeView", "make_assembly"]


class LinearGenomeView(anywidget.AnyWidget):
    _esm = _STATIC / "index.js"
    _css = _STATIC / "jbrowse-anywidget.css"

    # Config, pushed Python -> JS. assembly/tracks/default_session are JBrowse
    # config dicts; a change to them updates the view.
    assembly = traitlets.Dict().tag(sync=True)
    tracks = traitlets.List().tag(sync=True)
    default_session = traitlets.Dict().tag(sync=True)

    # The visible region, synced both ways. Reading it after the user has panned
    # gives back their current location.
    location = traitlets.Unicode("").tag(sync=True)

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
        JBrowse config file — so every track type and adapter is available with
        no Python wrapper, e.g.::

            view.add_track({
                "type": "AlignmentsTrack",
                "trackId": "reads",
                "name": "reads",
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

    def _assembly_name(self, assembly_name):
        if assembly_name:
            return assembly_name
        name = self.assembly.get("name")
        if not name:
            raise ValueError("no assembly set; pass assembly_name=")
        return name


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
