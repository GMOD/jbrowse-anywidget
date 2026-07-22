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
    assert track["type"] == "FeatureTrack"
    assert track["assemblyNames"] == ["hg38"]
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


def test_assembly_name_is_required_when_the_view_has_none():
    view = LinearGenomeView()
    with pytest.raises(ValueError, match="assembly_name"):
        view.add_features([{"refName": "chr1", "start": 0, "end": 1}])
