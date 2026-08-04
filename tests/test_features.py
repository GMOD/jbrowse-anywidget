"""Tests for add_features — the DataFrame/rows -> track path.

Everything here has to survive `json.dumps` on the way to the kernel, so the
value coercion matters as much as the shape of the config.
"""

import json

import pytest

from jbrowse_anywidget import LinearGenomeView


def features_track(rows, **kwargs):
    view = LinearGenomeView(assembly="hg38")
    view.add_features(rows, **kwargs)
    return view.tracks[-1]


def test_rows_become_a_from_config_feature_track():
    track = features_track([{"chrom": "chr1", "start": 10, "end": 20, "score": 5}])
    # a score column means signal, so it comes back as a wiggle
    assert track["type"] == "QuantitativeTrack"
    # assemblyNames is left to the view
    assert "assemblyNames" not in track
    assert track["adapter"]["type"] == "FromConfigAdapter"
    (feature,) = track["adapter"]["features"]
    assert feature == {
        "start": 10,
        "end": 20,
        "score": 5,
        "refName": "chr1",
        "uniqueId": "features-0",
    }


def test_non_finite_values_become_null():
    # a missing value in a pandas column arrives as NaN, which json.dumps writes
    # as bare `NaN` — invalid JSON the kernel's packer rejects
    track = features_track(
        [{"refName": "chr1", "start": 0, "end": 1, "score": float("nan")}]
    )
    (feature,) = track["adapter"]["features"]
    assert feature["score"] is None
    assert "NaN" not in json.dumps(track)


def test_dataframe_is_accepted():
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame({"chrom": ["chr1"], "start": [1], "end": [2], "gc": [0.42]})
    track = features_track(df, name="cpg islands")
    assert track["trackId"] == "cpg-islands"
    assert track["adapter"]["features"][0]["gc"] == 0.42


def test_color_becomes_a_display_block():
    track = features_track(
        [{"refName": "chr1", "start": 0, "end": 1}], color="jexl:'red'"
    )
    assert track["displays"] == [{"type": "LinearBasicDisplay", "color": "jexl:'red'"}]


def test_missing_refname_is_reported():
    with pytest.raises(ValueError, match="refName"):
        features_track([{"start": 0, "end": 1}])


def test_missing_coordinate_is_reported():
    with pytest.raises(ValueError, match="end"):
        features_track([{"refName": "chr1", "start": 0}])


def test_duplicate_track_id_is_refused():
    # calling this twice without a name is the easy way to collide, and two
    # tracks sharing a trackId break the view rather than showing both
    view = LinearGenomeView(assembly="hg38")
    rows = [{"refName": "chr1", "start": 0, "end": 1}]
    view.add_features(rows)
    with pytest.raises(ValueError, match="already on this view"):
        view.add_features(rows)
    view.add_features(rows, name="other")
    assert [t["trackId"] for t in view.tracks] == ["features", "other"]


def test_add_features_works_without_an_assembly():
    # this used to raise ValueError("no assembly set; pass assembly_name="); the
    # name was only ever needed to stamp a field the view fills in itself
    view = LinearGenomeView()
    view.add_features([{"refName": "chr1", "start": 0, "end": 1}])
    assert view.tracks[-1]["trackId"] == "features"


def test_a_score_column_makes_a_real_wiggle():
    # JBrowse's own name for the plotted value. Without this an in-memory signal
    # renders as boxes you have to color by hand, never a wiggle with an axis.
    track = features_track([{"refName": "1", "start": 0, "end": 10, "score": 5.0}])
    assert track["type"] == "QuantitativeTrack"


def test_no_score_column_stays_a_feature_track():
    track = features_track([{"refName": "1", "start": 0, "end": 10}])
    assert track["type"] == "FeatureTrack"


def test_quantitative_can_be_forced_either_way():
    rows = [{"refName": "1", "start": 0, "end": 10, "score": 5.0}]
    assert features_track(rows, quantitative=False)["type"] == "FeatureTrack"
    plain = [{"refName": "1", "start": 0, "end": 10}]
    assert features_track(plain, quantitative=True)["type"] == "QuantitativeTrack"


def test_color_lands_on_the_display_the_track_type_uses():
    rows = [{"refName": "1", "start": 0, "end": 10, "score": 5.0}]
    wiggle = features_track(rows, color="red")["displays"][0]
    assert wiggle["type"] == "LinearWiggleDisplay"
    boxes = features_track(rows, color="red", quantitative=False)["displays"][0]
    assert boxes["type"] == "LinearBasicDisplay"


def test_features_track_is_usable_without_a_widget():
    # JBrowseApp has no add_features, so the DataFrame path has to exist as a
    # plain config builder or multi-view apps cannot show an analysis result
    from jbrowse_anywidget import features_track as build

    conf = build([{"refName": "1", "start": 1, "end": 9}], name="peaks")
    assert conf["trackId"] == "peaks"
    assert conf["adapter"]["type"] == "FromConfigAdapter"
