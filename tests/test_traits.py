"""The JS side reads config off the anywidget model, so every trait a widget
declares has to reach it. The screenshot harness fakes that model from
scripts/gen_screenshot_specs.py, and a trait missing there reads back as
`undefined` in the bundle — which broke every figure when `plugins` was added.
These pin the trait sets the bundle indexes into (src/index.ts, src/app.ts).
"""

import json
import re
from pathlib import Path

import anywidget

from jbrowse_anywidget import JBrowseApp, LinearGenomeView

SRC = Path(__file__).resolve().parent.parent / "src"


def own_traits(widget):
    names = set()
    for cls in type(widget).__mro__:
        if cls is anywidget.AnyWidget:
            break
        names |= set(cls.class_own_traits(sync=True))
    return {n for n in names if not n.startswith("_")}


def test_linear_genome_view_syncs_its_config_traits():
    assert own_traits(LinearGenomeView()) == {
        "assembly",
        "tracks",
        "default_session",
        "aggregate_text_search_adapters",
        "plugins",
        "location",
        "selected_feature",
    }


def test_jbrowse_app_syncs_its_config_traits():
    assert own_traits(JBrowseApp()) == {
        "assemblies",
        "tracks",
        "views",
        "plugins",
        "view_locations",
        "selected_feature",
    }


def test_traits_are_json_ready_at_defaults():
    # the harness serializes these straight to JSON; a widget instance or other
    # non-JSON default would not survive the trip
    for widget in (LinearGenomeView(), JBrowseApp()):
        values = {n: getattr(widget, n) for n in own_traits(widget)}
        json.dumps(values)


def traits_read_by(entrypoint):
    # model.get('x') and model.on('change:x') name the traits the bundle indexes
    source = (SRC / entrypoint).read_text()
    return set(re.findall(r"model\.get\('([a-z_]+)'\)", source)) | set(
        re.findall(r"'change:([a-z_]+)'", source)
    )


def test_js_reads_only_traits_python_declares():
    # the other direction of the same invariant: a trait the bundle reads but
    # the widget never declares is `undefined` at render time
    for entrypoint, widget in (
        ("index.ts", LinearGenomeView()),
        ("app.ts", JBrowseApp()),
    ):
        assert traits_read_by(entrypoint) <= own_traits(widget), entrypoint
