"""Tests for features_track — the DataFrame/rows -> track config path.

Everything here has to survive `json.dumps` on the way to the kernel, so the
value coercion matters as much as the shape of the config.
"""

import json

import pytest

from jbrowse_anywidget import features_track


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


def test_numpy_scalars_survive_the_trip():
    # np.float32 is not a Python float, so the NaN check above misses it and
    # json.dumps refuses the value outright — one such column would break the
    # whole sync at display time, nowhere near the features_track call
    np = pytest.importorskip("numpy")
    track = features_track(
        [
            {
                "refName": "1",
                "start": np.int64(0),
                "end": np.int64(10),
                "score": np.float32("nan"),
                "n": np.int32(7),
            }
        ]
    )
    (feature,) = track["adapter"]["features"]
    assert feature["score"] is None
    assert feature["n"] == 7
    json.dumps(track)


def test_a_value_json_cannot_carry_becomes_text():
    # a datetime column rides along like any other; it must not take the sync
    # down with it
    pd = pytest.importorskip("pandas")
    df = pd.DataFrame(
        {
            "chrom": ["chr1"],
            "start": [1],
            "end": [2],
            "when": [pd.Timestamp("2024-01-01")],
        }
    )
    (feature,) = features_track(df)["adapter"]["features"]
    assert feature["when"].startswith("2024-01-01")


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


def test_extra_keywords_are_track_config():
    # a displays list is how the columns become a plot: the DataFrame's fields
    # feed a mark display's encoding, with nothing here naming the display
    displays = [
        {
            "type": "LinearMarkDisplay",
            "marks": [{"shape": "point", "encoding": {"y": "log2fc"}}],
        }
    ]
    rows = [{"refName": "1", "start": 0, "end": 10, "log2fc": 1.5}]
    track = features_track(rows, displays=displays, height=200)
    assert track["displays"] == displays
    assert track["height"] == 200
    assert track["type"] == "FeatureTrack"
