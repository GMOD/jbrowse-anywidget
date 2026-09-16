"""The Python <-> JS contract: which traits sync, and how options pass through.

The bundle reads these traits by name (src/index.ts, src/app.ts), and the
screenshot harness fakes the model from `_sync_traits`, so a trait missing on
either side reads back as `undefined` at render time.
"""

import json
import re
from pathlib import Path

from jbrowse_anywidget import JBrowseApp, LinearGenomeView, _sync_traits

SRC = Path(__file__).resolve().parent.parent / "src"


def test_linear_genome_view_syncs_options_and_read_backs():
    assert _sync_traits(LinearGenomeView()) == {
        "options",
        "local_files",
        "location",
        "current_session",
        "selected_feature",
    }


def test_jbrowse_app_syncs_options_and_read_backs():
    assert _sync_traits(JBrowseApp()) == {
        "options",
        "local_files",
        "view_locations",
        "current_session",
        "selected_feature",
    }


def test_traits_are_json_ready_at_defaults():
    for widget in (LinearGenomeView(), JBrowseApp()):
        json.dumps({n: getattr(widget, n) for n in _sync_traits(widget)})


def traits_read_by(entrypoint):
    source = "".join((SRC / name).read_text() for name in (entrypoint, "widget.ts"))
    return set(re.findall(r"model\.get\('([a-z_]+)'\)", source)) | set(
        re.findall(r"'change:([a-z_]+)'", source)
    )


def test_js_reads_only_traits_python_declares():
    for entrypoint, widget in (
        ("index.ts", LinearGenomeView()),
        ("app.ts", JBrowseApp()),
    ):
        assert traits_read_by(entrypoint) <= _sync_traits(widget), entrypoint


def test_options_pass_through_verbatim():
    options = {
        "assembly": "hg38",
        "location": "BRCA1",
        "tracks": ["https://x.org/r.cram", {"uri": "r.bam", "index": "r.bai"}],
        "aOptionJBrowseAddsLater": {"any": ["json"]},
    }
    assert LinearGenomeView(**options).options == options
    assert JBrowseApp(**options).options == options


def test_update_merges_into_options_in_one_change():
    view = LinearGenomeView(assembly="hg38", location="BRCA1", tracks=["a.bw"])
    changes = []
    view.observe(lambda change: changes.append(change["new"]), "options")
    view.update(location="TP53", tracks=[])
    assert changes == [{"assembly": "hg38", "location": "TP53", "tracks": []}]


def test_update_with_the_same_values_sends_nothing():
    app = JBrowseApp(assemblies=["hg38"], views=[])
    changes = []
    app.observe(changes.append, "options")
    app.update(views=[])
    assert changes == []


def test_read_backs_are_not_options():
    # writing live state into the options would echo, and would override a later
    # update of the same key
    view = LinearGenomeView(assembly="hg38", location="BRCA1")
    assert view.location == ""
    assert view.current_session == {}
    assert view.selected_feature is None
