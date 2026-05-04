from pathlib import Path
import json

DATA_DIR = Path('D:/ai coach fonus/code_test_fonus/fonus/data/books')

# All files in data/books/
all_files = list(DATA_DIR.glob('*'))
all_files = [f for f in all_files 
             if f.suffix in ['.pdf', '.txt']]

# DGCA regulatory patterns used in indexer
patterns = [
    '*1937*', '*1994*', '*2003*', 
    '*2011*', '*2025*', 'CAR_*', 
    'APM_*', '*DGCA*'
]

# Find what WAS indexed
seen = set()
indexed = []
for pattern in patterns:
    found = list(DATA_DIR.glob(pattern))
    for f in found:
        if f.suffix in ['.pdf', '.txt']:
            if str(f) not in seen:
                seen.add(str(f))
                indexed.append(f.name)

# Find what was NOT matched
not_indexed = [
    f.name for f in all_files 
    if f.name not in indexed
]

result = {
    "total_files": len(all_files),
    "indexed_count": len(indexed),
    "not_indexed_count": len(not_indexed),
    "missing_files": sorted(not_indexed)
}

with open("audit_results.json", "w") as f:
    json.dump(result, f, indent=4)

print("Audit complete. Results saved to audit_results.json")
