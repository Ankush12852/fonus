#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Audit processed/questions.json per module:
  - Duplicate question stems with conflicting marked correct answers
  - Duplicate stems with same answer but differing option sets
  - Rows that fail the app's "usable PYQ" rules (Structural rejects)
  - Obvious schema issues (correct_answer key missing from options)
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

_PLACEHOLDER_MCQ_OPT = re.compile(r"^(none|null|n/?a|--?|[.])\s*$", re.I)


def _meaningful_option_text(val) -> bool:
    if val is None:
        return False
    t = str(val).strip()
    if len(t) < 2:
        return False
    return _PLACEHOLDER_MCQ_OPT.fullmatch(t) is None


def _substantive_option_count(opts: dict) -> int:
    if not isinstance(opts, dict):
        return 0
    return sum(1 for v in opts.values() if _meaningful_option_text(v))


def _canonical_correct_key(opts: dict, raw) -> str | None:
    if raw is None:
        return None
    ca = str(raw).strip().lower()
    if not ca:
        return None
    for key in (ca, ca[:1]):
        if key in opts and _meaningful_option_text(opts[key]):
            return key
    return None


def norm_stem(question: str) -> str:
    return " ".join(str(question).strip().lower().split())


def options_fingerprint(opts) -> str:
    if not isinstance(opts, dict):
        return ""
    parts = [f"{k}:{str(v).strip()}" for k, v in sorted(opts.items())]
    return "||".join(parts)


def is_usable_pyq(q: dict) -> bool:
    if not q.get("question"):
        return False
    opts = q.get("options")
    if not isinstance(opts, dict):
        return False
    if _substantive_option_count(opts) < 3:
        return False
    return _canonical_correct_key(opts, q.get("correct_answer")) is not None


def audit_module(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    questions = data.get("questions") or []
    module_id = path.parent.parent.name

    by_stem: dict[str, list[dict]] = defaultdict(list)
    unusable = 0
    bad_correct_key = 0

    for i, q in enumerate(questions):
        stem = norm_stem(q.get("question", ""))
        if stem:
            by_stem[stem].append({"index_in_file": i, "raw": q})
        if not is_usable_pyq(q):
            unusable += 1
        opts = q.get("options")
        ca = (q.get("correct_answer") or "").strip().lower()
        if isinstance(opts, dict) and ca:
            keys = list(opts.keys())
            if ca not in opts and ca[:1] not in opts:
                bad_correct_key += 1

    conflicting: list[dict] = []
    same_answer_diff_opts: list[dict] = []
    trivial_stems: list[str] = []

    for stem, rows in by_stem.items():
        if len(rows) < 2:
            continue
        answers = []
        for r in rows:
            opts = r["raw"].get("options") or {}
            ck = None
            if isinstance(opts, dict):
                ck = _canonical_correct_key(opts, r["raw"].get("correct_answer"))
            answers.append((ck or str(r["raw"].get("correct_answer")).lower(), options_fingerprint(opts)))

        distinct_answers = sorted({a for a, _ in answers if a})
        distinct_fps = sorted({fp for _, fp in answers})

        if len(distinct_answers) > 1:
            conflicting.append({
                "stem": stem[:200] + ("…" if len(stem) > 200 else ""),
                "distinct_marked_correct": distinct_answers,
                "variants": len(rows),
                "sample_sources": sorted({
                    str(r["raw"].get("source_file") or "?") for r in rows
                }),
            })
        elif len(distinct_fps) > 1 and len(distinct_answers) <= 1:
            same_answer_diff_opts.append({
                "stem": stem[:200] + ("…" if len(stem) > 200 else ""),
                "marked_answer": distinct_answers[0] if distinct_answers else None,
                "option_set_variants": len(distinct_fps),
                "row_count": len(rows),
                "sample_sources": sorted({
                    str(r["raw"].get("source_file") or "?") for r in rows
                }),
            })

    short_q = sum(1 for q in questions if len(str(q.get("question") or "").strip()) < 20)

    return {
        "module": module_id,
        "path": str(path),
        "total_rows": len(questions),
        "unusable_pyq_rules": unusable,
        "bad_correct_answer_key": bad_correct_key,
        "distinct_stems": len(by_stem),
        "conflicting_duplicate_stems": len(conflicting),
        "duplicate_same_answer_diff_options": len(same_answer_diff_opts),
        "very_short_questions_lt20chars": short_q,
        "conflicting_examples": conflicting[:30],
        "same_answer_diff_options_examples": same_answer_diff_opts[:20],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Audit PYQ processed JSON files.")
    ap.add_argument(
        "--modules-root",
        type=Path,
        default=None,
        help="Defaults to repo data/Modules",
    )
    ap.add_argument(
        "--json-out",
        type=Path,
        default=None,
        help="Optional full JSON report path",
    )
    args = ap.parse_args()

    repo = Path(__file__).resolve().parent.parent
    root = args.modules_root or repo / "data" / "Modules"
    paths = sorted(root.glob("**/processed/questions.json"))
    if not paths:
        print(f"No questions.json under {root}")
        return

    reports = [audit_module(p) for p in paths]
    totals = {
        "modules": len(reports),
        "total_rows": sum(r["total_rows"] for r in reports),
        "unusable_pyq_rules": sum(r["unusable_pyq_rules"] for r in reports),
        "bad_correct_answer_key": sum(r["bad_correct_answer_key"] for r in reports),
        "conflicting_duplicate_stems": sum(r["conflicting_duplicate_stems"] for r in reports),
        "duplicate_same_answer_diff_options": sum(r["duplicate_same_answer_diff_options"] for r in reports),
    }

    print("=== PYQ audit summary ===")
    for k, v in totals.items():
        print(f"  {k}: {v}")
    print()

    for r in reports:
        if r["conflicting_duplicate_stems"] or r["unusable_pyq_rules"] > 50:
            print(
                f"[{r['module']}] rows={r['total_rows']} unusable={r['unusable_pyq_rules']} "
                f"conflicting_stems={r['conflicting_duplicate_stems']} "
                f"same_ans_diff_opts={r['duplicate_same_answer_diff_options']} "
                f"bad_key={r['bad_correct_answer_key']}"
            )
            for ex in r["conflicting_examples"][:5]:
                print(f"    CONFLICT: {ex['stem']!r}")
                print(f"      answers={ex['distinct_marked_correct']} variants={ex['variants']} sources={ex['sample_sources'][:4]}")
            for ex in r["same_answer_diff_options_examples"][:3]:
                print(f"    DUP_OPTS: {ex['stem']!r} ans={ex['marked_answer']} option_sets={ex['option_set_variants']}")

    if args.json_out:
        args.json_out.write_text(
            json.dumps({"totals": totals, "modules": reports}, indent=2),
            encoding="utf-8",
        )
        print(f"\nFull report: {args.json_out}")


if __name__ == "__main__":
    main()
