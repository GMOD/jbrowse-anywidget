"""Tests for the declarative track() shorthand and assemblyNames backfill."""

import pytest

from jbrowse_anywidget import LinearGenomeView, track


@pytest.mark.parametrize(
    ("uri", "track_type", "adapter_type"),
    [
        ("https://x.org/reads.bam", "AlignmentsTrack", "BamAdapter"),
        ("https://x.org/reads.cram", "AlignmentsTrack", "CramAdapter"),
        ("https://x.org/sig.bw", "QuantitativeTrack", "BigWigAdapter"),
        ("https://x.org/sig.bigwig", "QuantitativeTrack", "BigWigAdapter"),
        ("https://x.org/genes.bb", "FeatureTrack", "BigBedAdapter"),
        ("https://x.org/genes.bigbed", "FeatureTrack", "BigBedAdapter"),
        ("https://x.org/vars.vcf.gz", "VariantTrack", "VcfTabixAdapter"),
        ("https://x.org/genes.gff.gz", "FeatureTrack", "Gff3TabixAdapter"),
        ("https://x.org/genes.gff3.gz", "FeatureTrack", "Gff3TabixAdapter"),
        ("https://x.org/peaks.bed.gz", "FeatureTrack", "BedTabixAdapter"),
        ("https://x.org/contact.hic", "HicTrack", "HicAdapter"),
    ],
)
def test_infers_track_and_adapter_from_extension(uri, track_type, adapter_type):
    t = track(uri)
    assert t["type"] == track_type
    assert t["adapter"]["type"] == adapter_type
    assert "assemblyNames" not in t


def test_name_and_track_id_default_to_basename():
    t = track("https://x.org/data/my.reads.cram")
    assert t["name"] == "my.reads.cram"
    assert t["trackId"] == "my-reads-cram"


def test_explicit_name_and_track_id():
    t = track("https://x.org/r.bam", name="Reads", track_id="reads")
    assert t["name"] == "Reads"
    assert t["trackId"] == "reads"


def test_default_index_locations():
    assert track("https://x.org/r.bam")["adapter"]["index"]["indexType"] == "BAI"
    assert (
        track("https://x.org/r.cram")["adapter"]["craiLocation"]["uri"]
        == "https://x.org/r.cram.crai"
    )
    assert track("https://x.org/v.vcf.gz")["adapter"]["index"]["indexType"] == "TBI"


def test_csi_index_detected_by_extension():
    t = track("https://x.org/v.vcf.gz", index="https://x.org/v.vcf.gz.csi")
    assert t["adapter"]["index"]["indexType"] == "CSI"
    assert t["adapter"]["index"]["location"]["uri"] == "https://x.org/v.vcf.gz.csi"


def test_unknown_extension_raises():
    with pytest.raises(ValueError, match="can't infer"):
        track("https://x.org/mystery.xyz")


def test_query_string_ignored_when_inferring():
    t = track("https://x.org/r.bam?token=abc")
    assert t["adapter"]["type"] == "BamAdapter"
    assert t["adapter"]["bamLocation"]["uri"] == "https://x.org/r.bam?token=abc"


def test_assembly_names_backfilled_from_hub_name():
    view = LinearGenomeView(
        assembly="hg38",
        tracks=[track("https://x.org/r.cram"), track("https://x.org/s.bw")],
    )
    assert all(t["assemblyNames"] == ["hg38"] for t in view.tracks)


def test_assembly_names_backfilled_from_config_dict():
    view = LinearGenomeView(
        assembly={"name": "volvox"}, tracks=[track("https://x.org/r.bam")]
    )
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
