"""JBrowseApp opens views declared as plain JBrowse JSON.

A view spec is `{"type", "init"}` — the same vocabulary JBrowse Web serializes
into its `?session=spec-…` URLs, and the same shape a config.json's
`defaultSession.views` holds. There are no Python builders for it: writing the
dict is barely longer than a call would be, and what you write transfers
straight to a config file or the docs.
"""

from jbrowse_anywidget import JBrowseApp

PAF = {
    "type": "SyntenyTrack",
    "trackId": "hg38_mm39",
    "name": "hg38 vs mm39",
    "assemblyNames": ["hg38", "mm39"],
    "adapter": {
        "type": "PAFAdapter",
        "targetAssembly": "hg38",
        "queryAssembly": "mm39",
        "uri": "hg38_mm39.paf",
    },
}

SYNTENY_VIEW = {
    "type": "LinearSyntenyView",
    "init": {
        # a comparative view's panels are {"assembly", "loc"?} per side
        "views": [{"assembly": "hg38"}, {"assembly": "mm39"}],
        "tracks": ["hg38_mm39"],
    },
}


def test_jbrowse_app_stores_declarative_config():
    app = JBrowseApp(
        assemblies=[{"name": "hg38"}, {"name": "mm39"}],
        tracks=[PAF],
        views=[SYNTENY_VIEW],
    )
    assert [a["name"] for a in app.assemblies] == ["hg38", "mm39"]
    assert app.tracks == [PAF]
    assert app.views[0]["type"] == "LinearSyntenyView"


def test_any_view_type_opens_with_no_python_change():
    # the reason there is no builder: a view type JBrowse gains, or one a
    # runtime plugin registers, needs nothing added here
    app = JBrowseApp(
        assemblies=[{"name": "hg38"}],
        views=[{"type": "CircularView", "init": {"assembly": "hg38"}}],
    )
    assert app.views[0]["type"] == "CircularView"


def test_jbrowse_app_carries_a_session_snapshot():
    snapshot = {"name": "saved", "views": [{"type": "LinearGenomeView"}]}
    app = JBrowseApp(assemblies=[{"name": "hg38"}], views=[], session=snapshot)
    assert app.session == snapshot


def test_jbrowse_app_opens_its_views_when_no_session_is_given():
    app = JBrowseApp(assemblies=[{"name": "hg38"}], views=[])
    assert app.session == {}
    # the read-back is a separate trait, so live state never overwrites the
    # session that was handed in
    assert app.current_session == {}


def test_a_bare_uri_track_is_refused_with_the_reason():
    # the app's tracks seed the config catalog, which takes full configs only;
    # left alone this is an entry with no type that simply never displays
    import pytest

    with pytest.raises(ValueError, match="full track config dicts"):
        JBrowseApp(assemblies=["hg38"], tracks=["https://x.org/r.bam"])


def test_the_configuration_block_rides_along():
    # JBrowse's root config, the same one a config.json carries — `theme` is the
    # reason it is reachable at all, and there is no Python shape for it
    theme = {"theme": {"palette": {"secondary": {"main": "#ff0000"}}}}
    app = JBrowseApp(assemblies=["hg38"], configuration=theme)
    assert app.configuration == theme
