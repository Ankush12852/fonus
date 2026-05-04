from pathlib import Path

DATA_DIR = Path('D:/ai coach fonus/code_test_fonus/fonus/data/books')

# Current patterns used for DGCA indexing
patterns = [
    '*1937*', '*1994*', '*2003*', 
    '*2011*', '*2025*', 'CAR_*', 
    'APM_*', '*DGCA*'
]

# Find what IS matched
seen = set()
for pattern in patterns:
    for f in DATA_DIR.glob(pattern):
        if f.suffix in ['.pdf', '.txt']:
            seen.add(f.name)

# Find what is NOT matched
all_files = [
    f for f in DATA_DIR.glob('*')
    if f.suffix in ['.pdf', '.txt']
]

not_matched = [
    f.name for f in all_files 
    if f.name not in seen
]

print(f'Not matched by DGCA patterns:')
for name in sorted(not_matched):
    print(f'  {repr(name)}')
print(f'Total: {len(not_matched)}')
