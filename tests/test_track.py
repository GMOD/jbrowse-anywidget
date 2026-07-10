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


def test_uri_shorthand_by_default():
    # with no explicit index, lean on JBrowse's own `uri` shorthand so the
    # adapter derives its .bai/.crai/.tbi sibling itself
    assert track("https://x.org/r.bam")["adapter"] == {
        "type": "BamAdapter",
        "uri": "https://x.org/r.bam",
    }
    assert track("https://x.org/r.cram")["adapter"] == {
        "type": "CramAdapter",
        "uri": "https://x.org/r.cram",
    }
    assert track("https://x.org/v.vcf.gz")["adapter"] == {
        "type": "VcfTabixAdapter",
        "uri": "https://x.org/v.vcf.gz",
    }


def test_explicit_index_uses_longhand_slots():
    # the uri shorthand rebuilds the index from uri and would clobber the
    # override, so an explicit index switches to the full location slots
    bam = track("https://x.org/r.bam", index="https://x.org/other.bai")["adapter"]
    assert bam["bamLocation"]["uri"] == "https://x.org/r.bam"
    assert bam["index"]["location"]["uri"] == "https://x.org/other.bai"
    assert bam["index"]["indexType"] == "BAI"
    assert "uri" not in bam
    cram = track("https://x.org/r.cram", index="https://x.org/other.crai")["adapter"]
    assert cram["cramLocation"]["uri"] == "https://x.org/r.cram"
    assert cram["craiLocation"]["uri"] == "https://x.org/other.crai"


def test_csi_index_detected_by_extension():
    t = track("https://x.org/v.vcf.gz", index="https://x.org/v.vcf.gz.csi")
    assert t["adapter"]["index"]["indexType"] == "CSI"
    assert t["adapter"]["index"]["location"]["uri"] == "https://x.org/v.vcf.gz.csi"


def test_index_on_unindexed_format_raises():
    with pytest.raises(ValueError, match="no index file"):
        track("https://x.org/sig.bw", index="https://x.org/sig.bw.idx")


def test_gtf_tabix_inferred():
    t = track("https://x.org/genes.gtf.gz")
    assert t["type"] == "FeatureTrack"
    assert t["adapter"]["type"] == "GtfTabixAdapter"


@pytest.mark.parametrize(
    ("uri", "adapter_type"),
    [
        ("https://x.org/g.gff.gz", "Gff3TabixAdapter"),
        ("https://x.org/g.gff", "Gff3Adapter"),
        ("https://x.org/g.gtf.gz", "GtfTabixAdapter"),
        ("https://x.org/g.gtf", "GtfAdapter"),
        ("https://x.org/r.bed.gz", "BedTabixAdapter"),
        ("https://x.org/r.bed", "BedAdapter"),
        ("https://x.org/v.vcf.gz", "VcfTabixAdapter"),
        ("https://x.org/v.vcf", "VcfAdapter"),
    ],
)
def test_plain_vs_bgzipped_adapter(uri, adapter_type):
    # bgzipped -> indexed tabix adapter; plain -> whole-file in-memory adapter
    assert track(uri)["adapter"]["type"] == adapter_type


def test_unknown_extension_raises():
    with pytest.raises(ValueError, match="can't infer"):
        track("https://x.org/mystery.xyz")


def test_query_string_ignored_when_inferring():
    t = track("https://x.org/r.bam?token=abc")
    assert t["adapter"]["type"] == "BamAdapter"
    assert t["adapter"]["uri"] == "https://x.org/r.bam?token=abc"


def test_bare_uri_track_entry_expanded():
    view = LinearGenomeView(assembly="hg38", tracks=["https://x.org/r.cram"])
    (t,) = view.tracks
    assert t["adapter"] == {"type": "CramAdapter", "uri": "https://x.org/r.cram"}
    assert t["assemblyNames"] == ["hg38"]


def test_uri_index_pair_track_entry_expanded():
    view = LinearGenomeView(
        assembly="hg38", tracks=[("https://x.org/r.bam", "https://x.org/r.bam.bai")]
    )
    (t,) = view.tracks
    assert t["adapter"]["bamLocation"]["uri"] == "https://x.org/r.bam"
    assert t["adapter"]["index"]["location"]["uri"] == "https://x.org/r.bam.bai"


def test_track_config_dict_entry_passed_through():
    conf = {
        "type": "AlignmentsTrack",
        "trackId": "custom",
        "name": "custom",
        "adapter": {"type": "CramAdapter", "uri": "https://x.org/r.cram"},
    }
    view = LinearGenomeView(assembly="hg38", tracks=[conf])
    assert view.tracks[0]["trackId"] == "custom"
    assert view.tracks[0]["assemblyNames"] == ["hg38"]


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
