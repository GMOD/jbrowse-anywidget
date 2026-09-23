"""Every Python snippet a reader copies still matches the package.

The README's blocks, the notebooks' code cells and the public docstrings' `::`
examples are parsed, never run: an import the package no longer exports, a
keyword a helper no longer takes, an option the JBrowse product does not have,
and a view nesting its settings under `init` each fail here instead of in a
reader's notebook.

A widget's keywords are the product's option interface, read from the linked
jbrowse-components TypeScript; without that checkout the option half is skipped.
"""

import ast
import inspect
import json
import re
import textwrap
from pathlib import Path

import pytest

import jbrowse_anywidget as jb

REPO = Path(__file__).resolve().parent.parent
PRODUCTS = {
    "LinearGenomeView": (
        "react-linear-genome-view2/src/createLinearGenomeView.ts",
        ("LinearGenomeViewState", "CreateLinearGenomeViewOptions"),
    ),
    "JBrowseApp": ("react-app2/src/JBrowse/JBrowse.tsx", ("JBrowseProps",)),
}


def _option_keys(relative, interfaces):
    path = REPO / "node_modules" / "@jbrowse" / relative
    if not path.exists():
        return None
    source = path.read_text()
    keys = set()
    for name in interfaces:
        body = re.search(rf"export interface {name}\b[^{{]*{{(.*?)\n}}", source, re.S)
        keys |= set(re.findall(r"(?m)^  (\w+)\??:", body[1]))
    return keys


OPTIONS = {widget: _option_keys(*where) for widget, where in PRODUCTS.items()}


def _docstring_examples(obj, label):
    lines = (inspect.getdoc(obj) or "").splitlines()
    for i, line in enumerate(lines):
        if line.rstrip().endswith("::"):
            block = []
            for body in lines[i + 1 :]:
                if body.strip() and not body.startswith(" "):
                    break
                block.append(body)
            yield f"{label} docstring", textwrap.dedent("\n".join(block))


def _snippets():
    readme = (REPO / "README.md").read_text()
    for n, block in enumerate(re.findall(r"```python\n(.*?)```", readme, re.S)):
        yield f"README.md python block {n + 1}", block
    for path in sorted((REPO / "examples").glob("*.ipynb")):
        for n, cell in enumerate(json.loads(path.read_text())["cells"]):
            if cell["cell_type"] == "code":
                source = "".join(cell["source"])
                source = re.sub(r"(?m)^(\s*)[!%].*$", r"\1pass", source)
                yield f"{path.name} cell {n}", source
    yield from _docstring_examples(jb, "module")
    for name in jb.__all__:
        obj = getattr(jb, name)
        if callable(obj):
            yield from _docstring_examples(obj, name)
        if inspect.isclass(obj):
            for attr, member in vars(obj).items():
                if not attr.startswith("_") and inspect.isfunction(member):
                    yield from _docstring_examples(member, f"{name}.{attr}")


def _keywords():
    """The keywords each documented callable takes; None where it takes any."""
    accepted = {}
    for name in jb.__all__:
        obj = getattr(jb, name)
        if inspect.isfunction(obj):
            params = inspect.signature(obj).parameters.values()
            accepted[name] = (
                None
                if any(p.kind is p.VAR_KEYWORD for p in params)
                else {p.name for p in params}
            )
    accepted["add_local_file"] = set(
        inspect.signature(jb.LinearGenomeView.add_local_file).parameters
    )
    if all(OPTIONS.values()):
        accepted.update(OPTIONS)
        accepted["update"] = set().union(*OPTIONS.values())
    return accepted


def _drift(source):
    tree = ast.parse(source)
    accepted = _keywords()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == jb.__name__:
            for alias in node.names:
                if alias.name not in jb.__all__:
                    yield f"imports {alias.name}, which the package does not export"
        elif isinstance(node, ast.Call):
            func = node.func
            called = (
                func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            )
            for keyword in node.keywords:
                takes = accepted.get(called)
                if takes is not None and keyword.arg and keyword.arg not in takes:
                    yield f"{called}(...) takes no {keyword.arg}="
        elif isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if "init" in keys:
                yield 'a view nests its settings under "init"; write them flat'


SNIPPETS = list(_snippets())


@pytest.mark.skipif(not all(OPTIONS.values()), reason="no linked jbrowse-components")
def test_option_interfaces_are_read():
    assert {"assembly", "tracks", "location", "session"} <= OPTIONS["LinearGenomeView"]
    assert {"assemblies", "tracks", "views", "session"} <= OPTIONS["JBrowseApp"]


@pytest.mark.parametrize(("where", "source"), SNIPPETS, ids=[w for w, _ in SNIPPETS])
def test_snippet_matches_the_package(where, source):
    try:
        problems = list(_drift(source))
    except SyntaxError as e:
        problems = [f"does not parse: {e}"]
    assert not problems, f"{where}: " + "; ".join(problems)
