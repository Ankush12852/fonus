"""
check_questions.py — Fonus Module Question Status Checker
Loop through all folders in data/Modules/, load questions.json, and print a status table.
Run with: python check_questions.py
"""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
MODULES_DIR = PROJECT_ROOT / "data" / "Modules"


def count_pyq_files(module_dir: Path) -> int:
    """Count PDF, DOCX, and DOC files across dated_papers and question_banks."""
    count = 0
    for sub in ("dated_papers", "question_banks"):
        folder = module_dir / "questions" / sub
        if folder.exists():
            for pattern in ("*.pdf", "*.docx", "*.doc"):
                count += len(list(folder.glob(pattern)))
    return count


def get_status(num_questions: int) -> str:
    if num_questions >= 500:
        return "Good"
    elif num_questions >= 100:
        return "Low"
    else:
        return "Empty"


def main():
    if not MODULES_DIR.exists():
        print(f"ERROR: Modules directory not found: {MODULES_DIR}")
        return

    rows = []
    total_questions = 0

    for mod_dir in sorted(MODULES_DIR.iterdir()):
        if not mod_dir.is_dir():
            continue

        module_name = mod_dir.name
        questions_json = mod_dir / "processed" / "questions.json"
        pyq_count = count_pyq_files(mod_dir)

        if questions_json.exists():
            try:
                with open(questions_json, "r", encoding="utf-8") as f:
                    data = json.load(f)
                num_q = len(data.get("questions", []))
            except Exception:
                num_q = 0
        else:
            num_q = 0

        status = get_status(num_q)
        rows.append((module_name, num_q, pyq_count, status))
        total_questions += num_q

    if not rows:
        print("No modules found.")
        return

    # Print table
    col_widths = [10, 12, 12, 8]
    header = (
        f"{'Module':<{col_widths[0]}} "
        f"{'Questions':>{col_widths[1]}} "
        f"{'PYQ Files':>{col_widths[2]}} "
        f"{'Status':<{col_widths[3]}}"
    )
    separator = "-" * (sum(col_widths) + 3)

    print("\n" + separator)
    print(header)
    print(separator)

    for module_name, num_q, pyq_count, status in rows:
        status_label = f"[{status}]"
        print(
            f"{module_name:<{col_widths[0]}} "
            f"{num_q:>{col_widths[1]}} "
            f"{pyq_count:>{col_widths[2]}} "
            f"{status_label:<{col_widths[3]}}"
        )

    print(separator)
    print(f"{'TOTAL':<{col_widths[0]}} {total_questions:>{col_widths[1]}}")
    print(separator)
    print("\nStatus:  Good = >500 questions | Low = 100-500 | Empty = <100\n")


if __name__ == "__main__":
    main()
