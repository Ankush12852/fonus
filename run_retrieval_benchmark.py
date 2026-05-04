import json
from pathlib import Path
from typing import Any

import requests


PROJECT_ROOT = Path(__file__).resolve().parent
CASES_FILE = PROJECT_ROOT / "retrieval_benchmark_cases.json"
ENDPOINT = "http://localhost:8000/chat"


def load_cases() -> list[dict[str, Any]]:
    with open(CASES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def run_case(case: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "question": case["question"],
        "module": case["module"],
        "stream": "B1.1",
        "history": [],
    }
    try:
        resp = requests.post(ENDPOINT, json=payload, timeout=35)
        if resp.status_code != 200:
            return {
                "id": case["id"],
                "ok": False,
                "status": resp.status_code,
                "reason": f"http_{resp.status_code}",
                "answer_head": (resp.text or "")[:220],
                "score": 0.0,
            }
        data = resp.json()
    except Exception as e:
        return {
            "id": case["id"],
            "ok": False,
            "status": 0,
            "reason": f"request_error: {e}",
            "answer_head": "",
            "score": 0.0,
        }

    answer = (data.get("answer") or "").lower()
    sources = data.get("source") or []
    must_contain_any = [s.lower() for s in case.get("must_contain_any", [])]
    min_sources = int(case.get("expect_sources_min", 0))

    text_hit = True if not must_contain_any else any(k in answer for k in must_contain_any)
    source_hit = len(sources) >= min_sources

    # Weighted scoring per case: text relevance 70%, source presence 30%.
    score = (0.7 if text_hit else 0.0) + (0.3 if source_hit else 0.0)

    return {
        "id": case["id"],
        "ok": text_hit and source_hit,
        "status": 200,
        "reason": "ok" if (text_hit and source_hit) else (
            "text+source_miss" if (not text_hit and not source_hit)
            else "text_miss" if not text_hit
            else "source_miss"
        ),
        "score": round(score, 3),
        "llm_used": data.get("llm_used"),
        "sources": len(sources),
        "answer_head": (data.get("answer") or "")[:220].replace("\n", " "),
    }


def main() -> None:
    cases = load_cases()
    results = [run_case(c) for c in cases]

    total = len(results)
    passed = sum(1 for r in results if r["ok"])
    avg_score = (sum(r["score"] for r in results) / total) if total else 0.0
    percent = round(avg_score * 100, 2)

    print("RETRIEVAL BENCHMARK")
    print("=" * 60)
    for r in results:
        flag = "PASS" if r["ok"] else "FAIL"
        print(f"[{flag}] {r['id']} | score={r['score']:.2f} | reason={r['reason']}")
        print(f"       llm={r.get('llm_used')} | sources={r.get('sources')}")
        print(f"       answer: {r.get('answer_head')}")
    print("=" * 60)
    print(f"Passed: {passed}/{total}")
    print(f"Average retrieval quality: {percent}%")
    print(f"Quality score (10-point): {round((percent / 100) * 10, 2)}/10")

    report = {
        "passed": passed,
        "total": total,
        "quality_percent": percent,
        "quality_10_point": round((percent / 100) * 10, 2),
        "results": results,
    }
    out_path = PROJECT_ROOT / "retrieval_benchmark_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Saved report: {out_path}")


if __name__ == "__main__":
    main()
