import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data" / "books"

print(f"DATA_DIR: {DATA_DIR}")
print(f"DATA_DIR exists: {DATA_DIR.exists()}")
print(f"Files in DATA_DIR: {len(list(DATA_DIR.glob('*')))}")

dgca_files = []
regulatory_patterns = [
    "*1937*", "*1994*", "*2003*", 
    "*2011*", "*2025*", "CAR_*", 
    "APM_*", "*DGCA*"
]

for pattern in regulatory_patterns:
    found_pdf = list(DATA_DIR.glob(pattern + ".pdf"))
    found_txt = list(DATA_DIR.glob(pattern + ".txt"))
    found_any = list(DATA_DIR.glob(pattern))
    found = found_pdf + found_txt + found_any
    
    for f in found:
        if f.suffix.lower() in ['.pdf', '.txt']:
            dgca_files.append(str(f))
            print(f"  ✓ {f.name}")

dgca_files = list(set(dgca_files))
print(f"\nTotal DGCA files: {len(dgca_files)}")
