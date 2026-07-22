"""Tests for the declarative track() shorthand and assemblyNames backfill.

Track-type/adapter inference now lives in JBrowse core: the view expands a loose
`{uri, index?, ...}` spec at display time via the same format plugins the
"Add track" flow uses. So these tests cover only the Python-side spec building
and the assemblyNames backfill — the extension inference itself is core's, and
core owns those tests.
"""

import pytest

from jbrowse_anywidget import LinearGenomeView, track


def test_track_is_a_loose_uri_spec():
    assert track("https://x.org/reads.bam") == {"uri": "https://x.org/reads.bam"}


def test_track_carries_name_track_id_and_index():
    assert track(
        "https://x.org/r.bam",
        name="Reads",
        track_id="reads",
        index="https://x.org/other.bai",
    ) == {
        "uri": "https://x.org/r.bam",
        "name": "Reads",
        "trackId": "reads",
        "index": "https://x.org/other.bai",
    }


def test_track_extra_config_rides_along():
    assert track(
        "https://x.org/peaks.bed.gz", category=["Genes"], type="FeatureTrack"
    ) == {
        "uri": "https://x.org/peaks.bed.gz",
        "category": ["Genes"],
        "type": "FeatureTrack",
    }


def test_track_assembly_name_sets_assembly_names():
    assert track("https://x.org/r.bam", assembly_name="hg38")["assemblyNames"] == [
        "hg38"
    ]


def test_bare_uri_track_entry_becomes_loose_spec():
    view = LinearGenomeView(assembly="hg38", tracks=["https://x.org/r.cram"])
    (t,) = view.tracks
    assert t == {"uri": "https://x.org/r.cram", "assemblyNames": ["hg38"]}


def test_uri_index_pair_track_entry_becomes_loose_spec():
    view = LinearGenomeView(
        assembly="hg38", tracks=[("https://x.org/r.bam", "https://x.org/r.bam.bai")]
    )
    (t,) = view.tracks
    assert t == {
        "uri": "https://x.org/r.bam",
        "index": "https://x.org/r.bam.bai",
        "assemblyNames": ["hg38"],
    }


def test_track_config_dict_entry_passed_through_with_backfill():
    conf = {
        "type": "AlignmentsTrack",
        "trackId": "custom",
        "name": "custom",
        "adapter": {"type": "CramAdapter", "uri": "https://x.org/r.cram"},
    }
    view = LinearGenomeView(assembly="hg38", tracks=[conf])
    assert view.tracks[0]["trackId"] == "custom"
    assert view.tracks[0]["assemblyNames"] == ["hg38"]


def test_assembly_names_backfilled_from_config_dict_name():
    view = LinearGenomeView(assembly={"name": "volvox"}, tracks=["https://x.org/r.bam"])
    assert view.tracks[0]["assemblyNames"] == ["volvox"]


def test_add_track_backfills_assembly_names():
    view = LinearGenomeView(assembly="hg38")
    view.add_track(track("https://x.org/g.gff.gz"))
    assert view.tracks[-1]["assemblyNames"] == ["hg38"]


def test_explicit_assembly_name_not_overwritten():
    view = LinearGenomeView(
        assembly="hg38", tracks=[track("https://x.org/r.bam", assembly_name="other")]
    )
    assert view.tracks[0]["assemblyNames"] == ["other"]


def test_sequence_url_assembly_backfills_derived_name():
    # a bare FASTA URL as assembly= builds an assembly named after the file (the
    # view's makeAssembly does the same), so backfilled tracks must match
    view = LinearGenomeView(
        assembly="https://x.org/data/hg38.fa.gz?t=1", tracks=["https://x.org/r.bam"]
    )
    assert view.tracks[0]["assemblyNames"] == ["hg38"]


def test_hub_name_assembly_still_backfills_verbatim():
    view = LinearGenomeView(
        assembly="GCF_000001405.40", tracks=["https://x.org/r.bam"]
    )
    assert view.tracks[0]["assemblyNames"] == ["GCF_000001405.40"]


def test_assembly_set_after_tracks_backfills_them():
    # the backfill runs when tracks are validated, so an assembly that arrives
    # later has to reach back over the tracks already set
    view = LinearGenomeView(tracks=["https://x.org/r.bam"])
    assert "assemblyNames" not in view.tracks[0]
    view.assembly = "hg38"
    assert view.tracks[0]["assemblyNames"] == ["hg38"]


def test_track_entry_pair_of_wrong_length_is_reported():
    with pytest.raises(ValueError, match="uri, index"):
        LinearGenomeView(tracks=[("a.bam", "a.bai", "extra")])
