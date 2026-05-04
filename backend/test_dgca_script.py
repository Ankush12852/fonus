from pathlib import Path
import sys

with open("output_utf8.txt", "w", encoding="utf-8") as f:
    PROJECT_ROOT = Path('D:/ai coach fonus/code_test_fonus/fonus')
    DATA_DIR = PROJECT_ROOT / 'data' / 'books'
    f.write(f'DATA_DIR: {DATA_DIR}\n')
    f.write(f'Exists: {DATA_DIR.exists()}\n')

    # List all files
    all_files = list(DATA_DIR.glob('*'))
    f.write(f'Total files: {len(all_files)}\n')

    # Find DGCA regulatory files
    import re
    dgca = [p for p in all_files if any(
        x in p.name for x in 
        ['1937','1994','2003','2011','2025',
         'CAR_','APM_','DGCA']
    )]
    f.write(f'DGCA regulatory files found: {len(dgca)}\n')
    for p in dgca:
        f.write(f'  {p.name}\n')
