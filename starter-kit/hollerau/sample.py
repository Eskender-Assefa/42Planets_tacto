"""Extract 3 representative samples from the data package into data/samples/*.json.

    cd starter-kit && uv run python -m hollerau.sample

- leverage:        a local simulator case (supplier + part from its case file)
- strategic:       a practice case's trigger document (supplier + part from the documents table)
- baseline_email:  a supplier letter / e-mail as plain text plus its structured fields

IDs below are defaults, not data: override them with the CLI options.
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from arena_kit.cli import load_env

from .package import Package, PackageError
from .package_types import SampleBundle

log = logging.getLogger("hollerau.sample")

SIM_CASES = Path(__file__).resolve().parent.parent / "arena_kit" / "sim_cases"
OUT = Path("data/samples")


def from_sim_case(pkg: Package, case_id: str, role: str) -> SampleBundle:
    path = SIM_CASES / f"{case_id.removeprefix('case:')}.json"
    try:
        case = json.loads(path.read_text(encoding="utf-8"))
        supplier_id, part_id = str(case["suppliers"][0]), str(case["parts"][0])
    except (OSError, ValueError, KeyError, IndexError) as e:
        raise PackageError(f"cannot read sim case {path}: {e}") from e
    return {"role": role, "case_id": case_id, "document": None, "bundle": pkg.supplier_bundle(supplier_id, part_id)}


def from_document(pkg: Package, doc_id: str, role: str, case_id: str | None) -> SampleBundle:
    doc = pkg.trigger_document(doc_id)
    if not doc["supplier_id"]:
        raise PackageError(f"{doc_id} names no supplier")
    part_id = (doc["part_ids"] or "").split(";")[0] or None
    bundle = pkg.supplier_bundle(doc["supplier_id"], part_id)
    return {"role": role, "case_id": case_id, "document": doc, "bundle": bundle}


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")
    load_env()  # type: ignore[no-untyped-call]  # upstream arena_kit is unannotated
    ap = argparse.ArgumentParser(prog="hollerau.sample", description=__doc__.split("\n\n")[0])
    ap.add_argument("--leverage-case", default="case:S01")
    ap.add_argument("--strategic-doc", default="doc:20260914-70510-P02")
    ap.add_argument("--strategic-case", default="case:P02")
    ap.add_argument("--email-doc", default="doc:20260911-70110-P01")
    ap.add_argument("--email-case", default="case:P01")
    a = ap.parse_args(argv)
    try:
        pkg = Package()
        samples = [
            from_sim_case(pkg, a.leverage_case, "leverage"),
            from_document(pkg, a.strategic_doc, "strategic", a.strategic_case),
            from_document(pkg, a.email_doc, "baseline_email", a.email_case),
        ]
    except PackageError as e:
        print(f"FAIL {e}")
        return 1
    OUT.mkdir(parents=True, exist_ok=True)
    for s in samples:
        b = s["bundle"]
        path = OUT / f"{s['role']}.json"
        path.write_text(json.dumps(s, indent=2, ensure_ascii=False), encoding="utf-8")
        part = b["part"]["description"] if b["part"] else "-"
        sc = b["latest_scorecard"]
        print(
            f"{s['role']:<15} {b['supplier']['id']} {b['supplier']['name']} ({b['supplier']['country']}, "
            f"{b['supplier']['category']}) | part: {part} | scorecard: {sc['colour'] if sc else '-'} | "
            f"history: {len(b['negotiation_history'])} events -> {path}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
