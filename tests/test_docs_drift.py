"""Every Python snippet a reader copies still matches the package.

The README's blocks, the notebooks' code cells and the public docstrings' `::`
examples are parsed, never run: an import the package no longer exports, a
keyword a widget or helper no longer takes, and a view nesting its settings
under `init` each fail here instead of in a reader's notebook.
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
WIDGETS = (jb.LinearGenomeView, jb.JBrowseApp)


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
    accepted = {}
    for name in jb.__all__:
        obj = getattr(jb, name)
        if inspect.isfunction(obj):
            accepted[name] = set(inspect.signature(obj).parameters)
    for widget in WIDGETS:
        accepted[widget.__name__] = set(
            inspect.signature(widget.__init__).parameters
        ) | set(widget.class_trait_names())
        for cls in widget.__mro__:
            if cls.__module__ == jb.__name__:
                for attr, member in vars(cls).items():
                    if not attr.startswith("_") and inspect.isfunction(member):
                        accepted[attr] = set(inspect.signature(member).parameters)
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
                if (
                    called in accepted
                    and keyword.arg
                    and keyword.arg not in accepted[called]
                ):
                    yield f"{called}(...) takes no {keyword.arg}="
        elif isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant)]
            if "init" in keys:
                yield 'a view nests its settings under "init"; write them flat'


SNIPPETS = list(_snippets())


@pytest.mark.parametrize(("where", "source"), SNIPPETS, ids=[w for w, _ in SNIPPETS])
def test_snippet_matches_the_package(where, source):
    try:
        problems = list(_drift(source))
    except SyntaxError as e:
        problems = [f"does not parse: {e}"]
    assert not problems, f"{where}: " + "; ".join(problems)
