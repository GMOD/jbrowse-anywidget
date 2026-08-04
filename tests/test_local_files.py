"""Tests for pushing real files from the kernel into the browser.

`add_features` inlines every row into the widget state as JSON, which stops
scaling somewhere past a few thousand features. `add_local_file` is the other
path: a real indexed file crosses as binary and is read *by byte range* in the
browser, so it stays indexed. These cover the Python half — registration and
naming. That the bytes arrive as a seekable blob is product-core's
localFiles.test.ts, and the read path is exercised for real by
scripts/screenshot_examples.mjs, which jsdom cannot do (its Blob.slice() has no
arrayBuffer()).
"""

import pytest

from jbrowse_anywidget import LinearGenomeView


def test_add_local_file_registers_bytes_under_the_file_name(tmp_path):
    peaks = tmp_path / "peaks.bed.gz"
    peaks.write_bytes(b"fake-bgzip")

    view = LinearGenomeView(assembly="hg38")
    name = view.add_local_file(peaks)

    assert name == "peaks.bed.gz"
    assert view.local_files == {"peaks.bed.gz": b"fake-bgzip"}


def test_add_local_file_picks_up_a_sibling_index(tmp_path):
    # the adapter derives its index location as a sibling of the uri string, so
    # the index has to be registered under exactly that name to be found
    peaks = tmp_path / "peaks.bed.gz"
    peaks.write_bytes(b"data")
    (tmp_path / "peaks.bed.gz.tbi").write_bytes(b"index")

    view = LinearGenomeView(assembly="hg38")
    view.add_local_file(peaks)

    assert view.local_files == {
        "peaks.bed.gz": b"data",
        "peaks.bed.gz.tbi": b"index",
    }


def test_add_local_file_takes_an_explicit_name(tmp_path):
    src = tmp_path / "tmp123.bed.gz"
    src.write_bytes(b"data")

    view = LinearGenomeView(assembly="hg38")

    assert view.add_local_file(src, name="peaks.bed.gz") == "peaks.bed.gz"
    assert set(view.local_files) == {"peaks.bed.gz"}


def test_registering_a_second_file_keeps_the_first(tmp_path):
    # traitlets syncs per trait, so this has to be a new dict, not a mutation
    for stem in ("a", "b"):
        (tmp_path / f"{stem}.bw").write_bytes(stem.encode())

    view = LinearGenomeView(assembly="hg38")
    view.add_local_file(tmp_path / "a.bw")
    view.add_local_file(tmp_path / "b.bw")

    assert view.local_files == {"a.bw": b"a", "b.bw": b"b"}


def test_a_local_file_is_referenced_like_any_url(tmp_path):
    # the whole point of naming rather than inventing a scheme: the track entry
    # is the same loose spec a remote file would use, so extension inference and
    # index-sibling derivation are unchanged
    peaks = tmp_path / "peaks.bed.gz"
    peaks.write_bytes(b"data")

    view = LinearGenomeView(assembly="hg38")
    view.add_track(view.add_local_file(peaks))

    assert view.tracks == [{"uri": "peaks.bed.gz"}]


def test_missing_file_raises(tmp_path):
    view = LinearGenomeView(assembly="hg38")
    with pytest.raises(FileNotFoundError):
        view.add_local_file(tmp_path / "nope.bed.gz")
