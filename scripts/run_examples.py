"""Execute the example notebooks and photograph the widgets they actually built.

    python scripts/run_examples.py            # every notebook, then render
    python scripts/run_examples.py 01 02      # just those, by number
    python scripts/run_examples.py --no-render  # capture specs, skip the browser

Each notebook runs top-to-bottom in a real kernel, in a scratch directory, with
network. Afterwards one extra cell runs in that same kernel and reads the traits
off every widget still bound to a name — so a figure is what the notebook
produced, not a second description of it maintained alongside. The specs land in
scripts/screenshot_specs.json, which scripts/screenshot_examples.mjs renders.

That is the point of doing it this way. The figures used to come from
gen_screenshot_specs.py, which rebuilt each example's config in parallel with
the notebook that showed it: the two agreed only while someone kept them
agreeing, and the README's claim to show "what the notebooks actually produce"
rested on that.

Executing is also the only check that a notebook *runs* — `pytest` never opens
one, and a cell that raises is invisible until a reader hits it in Colab.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import certifi
import nbformat
from nbclient import NotebookClient
from nbclient.exceptions import CellExecutionError

REPO = Path(__file__).resolve().parent.parent
EXAMPLES = REPO / "examples"
SPECS = REPO / "scripts" / "screenshot_specs.json"
# Deliberately NOT scripts/fixtures, which holds committed files that
# verify_bundle_runtime.mjs reads: notebook 13 writes a `signal.bw` of its own,
# and capturing into the same directory silently overwrote the fixture of that
# name. Generated per run, gitignored, and cleared before each one.
CAPTURED = REPO / "scripts" / "captured"

# A notebook that fetches a 17GB BAM's index and queries it, or builds every
# human exon, is not a 60-second cell. This is the ceiling for a whole notebook.
TIMEOUT = 1800


def _trust_certificates() -> None:
    """Point pysam's bundled libcurl at a CA bundle.

    Its wheels ship their own libcurl with no CA path compiled in, so an https
    BAM fails with `Libcurl reported error 77 (Problem with the SSL CA cert)` —
    which reads like a broken URL and is not. Notebooks 05 and 10 open a 1000
    Genomes BAM over https and die here on any environment that has not already
    set this, CI included. An existing value wins.
    """
    for var in ("CURL_CA_BUNDLE", "SSL_CERT_FILE"):
        if os.environ.get(var):
            continue
        for candidate in (certifi.where(), "/etc/ssl/certs/ca-certificates.crt"):
            if candidate and Path(candidate).exists():
                os.environ[var] = candidate
                break


# What each notebook is a figure of. A notebook missing here still runs — it is
# just not photographed, which is right for the ones whose point is the printed
# numbers rather than the view. The name is the image stem, so it is also what
# the README links; `variable` picks one widget out of a notebook that builds
# several.
FIGURES = {
    "01_quickstart": {"caption": "01 · quickstart: an assembly and a bigWig"},
    "02_dataframe_analysis": {
        "name": "02_bioframe",
        "caption": "02 · bioframe result: CpG islands + shores",
    },
    "03_alignments": {"caption": "03 · GPU-rendered CRAM alignments"},
    "04_multisample_variants": {
        "name": "04_variants",
        "caption": "04 · multi-sample variants, colored by cohort",
        "variable": "view",
    },
    "05_bam_coverage": {"caption": "05 · pysam read depth over BRCA1"},
    "06_popgen_selection": {"caption": "06 · Fst scan over the Cyp6g1 sweep"},
    "07_differential_expression": {"caption": "07 · differential expression"},
    "08_hosted_assembly_hub": {"caption": "08 · a hosted assembly hub"},
    "09_interactive_controls": {"caption": "09 · a slider driving the track"},
    "10_region_reactive": {"caption": "10 · coverage for the visible region"},
    "11_synteny_ecoli": {
        "name": "11_synteny",
        "caption": "11 · synteny: four E. coli strains (JBrowseApp)",
    },
    "12_large_data": {
        "caption": "12 · 2.1M exons from a tabix file in this kernel",
        "variable": "view",
    },
    "13_large_wiggle": {
        "caption": "13 · a chromosome of signal, recomputed per view",
        "variable": "live",
    },
}


# The two README figures no notebook builds. Written out here rather than in a
# generator of their own, because a second file describing configs is exactly
# what this script replaced — and kept honest by being the short list it is. A
# figure that grows a notebook should move out of here into FIGURES.
ECOLI = "https://jbrowse.org/demos/ecoli_pangenome"
STRAINS = ["K12", "Sakai", "CFT073", "NCTC86"]

NO_NOTEBOOK = {
    # notebook 11's closing prose says "change the view's type to DotplotView";
    # this is that sentence, rendered
    "12_dotplot": {
        "bundle": "app.js",
        "caption": "the same PAF as a dotplot",
        "traits": {
            "assemblies": [
                {"name": s, "uri": f"{ECOLI}/{s}.fa.gz"} for s in STRAINS[:2]
            ],
            "tracks": [
                {
                    "type": "SyntenyTrack",
                    "trackId": "ecoli_ava",
                    "name": "E. coli all-vs-all (minimap2 PAF)",
                    "assemblyNames": STRAINS,
                    "adapter": {
                        "type": "AllVsAllPAFAdapter",
                        "assemblyNames": STRAINS,
                        "pafLocation": {"uri": f"{ECOLI}/all_vs_all.paf.gz"},
                    },
                }
            ],
            "views": [
                {
                    "type": "DotplotView",
                    "init": {
                        "views": [{"assembly": s} for s in STRAINS[:2]],
                        "tracks": ["ecoli_ava"],
                    },
                }
            ],
        },
    },
    # the README's "Plots" section, which shows a display doing the plotting
    "13_manhattan": {
        "bundle": "index.js",
        "caption": "GWAS summary stats as a Manhattan plot",
        "traits": {
            "assembly": "hg19",
            "location": "2",
            "tracks": [
                {
                    "type": "GWASTrack",
                    "trackId": "gwas_track",
                    "name": "GWAS",
                    "adapter": {
                        "type": "GWASAdapter",
                        "scoreColumn": "neg_log_pvalue",
                        "uri": "https://jbrowse.org/genomes/hg19/gwas/summary_stats.txt.gz",
                    },
                    "displays": [{"type": "LinearManhattanDisplay", "height": 250}],
                }
            ],
        },
    },
}


def with_defaults(spec: dict) -> dict:
    """Fill every trait the widget declares, so the fake model has them all.

    The harness reads traits straight off this JSON, and one the bundle indexes
    but the spec omits comes back `undefined` — which is how adding `plugins`
    once broke every figure. A notebook-captured spec gets them from
    `_sync_traits`; a hand-written one gets them here, off a real widget.
    """
    from jbrowse_anywidget import JBrowseApp, LinearGenomeView, _sync_traits

    blank = JBrowseApp() if spec["bundle"] == "app.js" else LinearGenomeView()
    traits = {n: getattr(blank, n) for n in sorted(_sync_traits(blank))}
    return {**spec, "traits": {**traits, **spec["traits"]}}


# Runs in the notebook's own kernel once its cells are done. Reads the widgets
# off the namespace rather than reconstructing them, and lifts `local_files`
# bytes out to disk, since the spec is JSON and those are megabytes of binary.
CAPTURE = """
import json as _json, pathlib as _pl
from jbrowse_anywidget import JBrowseApp, LinearGenomeView, _sync_traits

_out, _fixtures = _pl.Path({out!r}), _pl.Path({fixtures!r})
_fixtures.mkdir(parents=True, exist_ok=True)

# Named widgets, then the ones a cell only *displayed*: a notebook that ends on
# a bare `JBrowseApp(...)` expression — which is how you show one without
# keeping it — binds no name, and IPython's Out is the only place it survives.
_candidates = [(_n, _o) for _n, _o in globals().items() if not _n.startswith("_")]
_candidates += [
    ("Out[%d]" % _k, _o) for _k, _o in sorted(globals().get("Out", {{}}).items())
]
_seen, _found = set(), {{}}
for _name, _obj in _candidates:
    if not isinstance(_obj, (LinearGenomeView, JBrowseApp)) or id(_obj) in _seen:
        continue
    _seen.add(id(_obj))
    _traits = {{n: getattr(_obj, n) for n in sorted(_sync_traits(_obj))}}
    _urls = {{}}
    for _fn, _data in (_traits.get("local_files") or {{}}).items():
        (_fixtures / _fn).write_bytes(_data)
        _urls[_fn] = "/scripts/captured/" + _fn
    _traits["local_files"] = {{}}
    _found[_name] = {{
        "bundle": "app.js" if isinstance(_obj, JBrowseApp) else "index.js",
        "traits": _traits,
        **({{"localFileUrls": _urls}} if _urls else {{}}),
    }}
_out.write_text(_json.dumps(_found))
print("captured", ", ".join(_found) or "nothing")
"""


def run(path: Path, capture_to: Path) -> dict:
    """Execute one notebook in a scratch cwd, then capture its widgets."""
    nb = nbformat.read(path, as_version=4)
    work = Path(tempfile.mkdtemp(prefix=f"{path.stem}-"))
    try:
        client = NotebookClient(
            nb,
            timeout=TIMEOUT,
            kernel_name="python3",
            resources={"metadata": {"path": str(work)}},
            # otherwise every notebook opens with ipykernel's unencrypted-TCP
            # warning, which is noise in a tool meant to be watched
            extra_arguments=["--Application.log_level=ERROR"],
        )
        # appended before the run, not handed to execute_cell loose: nbclient
        # writes each executed cell back into nb["cells"][index]
        nb.cells.append(
            nbformat.v4.new_code_cell(
                CAPTURE.format(out=str(capture_to), fixtures=str(CAPTURED))
            )
        )
        with client.setup_kernel():
            for i, cell in enumerate(nb.cells):
                client.execute_cell(cell, i)
        return json.loads(capture_to.read_text()) if capture_to.exists() else {}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def pick(widgets: dict, figure: dict) -> dict | None:
    """The one widget this notebook is a figure of."""
    if not widgets:
        return None
    wanted = figure.get("variable")
    if wanted:
        return widgets.get(wanted)
    # no name given: the notebook built exactly one, or the last one wins —
    # which is the one its closing cells are about
    return list(widgets.values())[-1]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("only", nargs="*", help="notebook number(s) to run, e.g. 01 11")
    parser.add_argument(
        "--no-render", action="store_true", help="write the specs, skip the browser"
    )
    args = parser.parse_args()
    _trust_certificates()
    shutil.rmtree(CAPTURED, ignore_errors=True)

    notebooks = sorted(EXAMPLES.glob("*.ipynb"))
    if args.only:
        wanted = tuple(n.zfill(2) for n in args.only)
        notebooks = [p for p in notebooks if p.stem.startswith(wanted)]
        if not notebooks:
            print(f"no notebook matches {args.only}", file=sys.stderr)
            return 1

    specs, failed = {}, []
    with tempfile.TemporaryDirectory() as tmp:
        capture_to = Path(tmp) / "widgets.json"
        for path in notebooks:
            started = time.monotonic()
            try:
                widgets = run(path, capture_to)
            except CellExecutionError as e:
                # the notebook itself is broken; say which cell and keep going,
                # so one bad notebook does not hide the state of the rest
                print(
                    f"✗ {path.stem}: {str(e).strip().splitlines()[-1][:160]}",
                    flush=True,
                )
                failed.append(path.stem)
                continue
            took = time.monotonic() - started
            figure = FIGURES.get(path.stem)
            spec = pick(widgets, figure) if figure else None
            if spec:
                spec["caption"] = figure["caption"]
                specs[figure.get("name", path.stem)] = spec
                print(
                    f"✓ {path.stem}  {took:5.0f}s  -> {figure.get('name', path.stem)}",
                    flush=True,
                )
            else:
                print(f"✓ {path.stem}  {took:5.0f}s  (ran; no figure)", flush=True)
            capture_to.unlink(missing_ok=True)

    if not args.only:
        for name, spec in NO_NOTEBOOK.items():
            specs[name] = with_defaults(spec)
            print(f"✓ {name}  (no notebook)", flush=True)

    if specs:
        specs = dict(sorted(specs.items()))
        SPECS.write_text(json.dumps(specs, indent=2))
        print(f"\nwrote {SPECS.relative_to(REPO)}: {', '.join(specs)}")

    if specs and not args.no_render:
        print()
        render = subprocess.run(
            ["node", str(REPO / "scripts" / "screenshot_examples.mjs"), *specs],
            cwd=REPO,
            check=False,
        )
        if render.returncode:
            failed.append("render")

    if failed:
        print(f"\n{len(failed)} failed: {', '.join(failed)}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
