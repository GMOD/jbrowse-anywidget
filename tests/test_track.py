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
    assert view.tracks == [{"uri": "https://x.org/r.cram"}]


def test_uri_index_pair_track_entry_becomes_loose_spec():
    # JSON has no tuple, so this is the one entry form Python has to unpack:
    # left alone it reaches the view as a 2-element array read as a config
    view = LinearGenomeView(
        assembly="hg38", tracks=[("https://x.org/r.bam", "https://x.org/r.bam.bai")]
    )
    assert view.tracks == [
        {"uri": "https://x.org/r.bam", "index": "https://x.org/r.bam.bai"}
    ]


def test_track_config_dict_entry_passed_through_untouched():
    conf = {
        "type": "AlignmentsTrack",
        "trackId": "custom",
        "name": "custom",
        "adapter": {"type": "CramAdapter", "uri": "https://x.org/r.cram"},
    }
    view = LinearGenomeView(assembly="hg38", tracks=[conf])
    assert view.tracks == [conf]


def test_explicit_assembly_name_is_preserved():
    view = LinearGenomeView(
        assembly="hg38", tracks=[track("https://x.org/r.bam", assembly_name="other")]
    )
    assert view.tracks[0]["assemblyNames"] == ["other"]


def test_assembly_names_are_left_to_the_view():
    # The view stamps its own resolved assembly onto a track that omits it, and
    # knows that name even when assembly= was a hub name it had to fetch. Doing
    # it here instead could not survive an assembly swap, since the view only
    # fills an ABSENT assemblyNames.
    view = LinearGenomeView(assembly="hg38", tracks=["https://x.org/r.bam"])
    assert "assemblyNames" not in view.tracks[0]


def test_tracks_are_not_pinned_to_the_assembly_they_arrived_under():
    view = LinearGenomeView(assembly="hg38", tracks=["https://x.org/r.bam"])
    view.assembly = "mm39"
    assert "assemblyNames" not in view.tracks[0]


def test_tracks_set_before_the_assembly_are_not_second_class():
    view = LinearGenomeView(tracks=["https://x.org/r.bam"])
    view.assembly = "hg38"
    assert view.tracks == [{"uri": "https://x.org/r.bam"}]


def test_track_entry_pair_of_wrong_length_is_reported():
    with pytest.raises(ValueError, match="uri, index"):
        LinearGenomeView(tracks=[("a.bam", "a.bai", "extra")])
