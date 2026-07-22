"""Tests for the hub config baseUri stamping.

Assemblies themselves need no Python builder: an assembly config is the flat
`{"name", "uri"}` dict core expands, so there is nothing here to test.
"""

from jbrowse_anywidget import _stamp_base_uri


def test_stamp_base_uri_fills_absent_base():
    config = {"adapter": {"uri": "seq.fa"}}
    _stamp_base_uri(config, "https://host/config.json")
    assert config["adapter"]["baseUri"] == "https://host/config.json"


def test_stamp_base_uri_replaces_explicit_null():
    # a node carrying baseUri=None must still be stamped; a bare `in` check would
    # wrongly skip it (the divergence stampBaseUri.ts guards against)
    config = {"adapter": {"uri": "seq.fa", "baseUri": None}}
    _stamp_base_uri(config, "https://host/config.json")
    assert config["adapter"]["baseUri"] == "https://host/config.json"


def test_stamp_base_uri_preserves_existing_base():
    config = {"adapter": {"uri": "seq.fa", "baseUri": "https://other/"}}
    _stamp_base_uri(config, "https://host/config.json")
    assert config["adapter"]["baseUri"] == "https://other/"
