"""Tests for the hub config baseUri stamping.

Assemblies themselves need no Python builder: an assembly config is the flat
`{"name", "uri"}` dict core expands, so there is nothing here to test.
"""

import io
import json
import urllib.error
import urllib.request

import pytest

from jbrowse_anywidget import _stamp_base_uri, fetch_hub


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


def test_fetch_hub_takes_a_config_url_and_stamps_it(monkeypatch):
    url = "https://example.org/demos/x/config.json"
    body = {"assemblies": [{"name": "x", "sequence": {"adapter": {"uri": "x.fa"}}}]}
    fetched = []

    def urlopen(u, timeout):
        fetched.append(u)
        return io.BytesIO(json.dumps(body).encode())

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    config = fetch_hub(url)
    assert fetched == [url]
    assert config["assemblies"][0]["sequence"]["adapter"]["baseUri"] == url


def test_fetch_hub_names_a_missing_config_url(monkeypatch):
    url = "https://example.org/nope/config.json"

    def urlopen(u, timeout):
        raise urllib.error.HTTPError(u, 404, "Not Found", None, None)

    monkeypatch.setattr(urllib.request, "urlopen", urlopen)
    with pytest.raises(ValueError, match=r"404 from https://example.org/nope"):
        fetch_hub(url)
