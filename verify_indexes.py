import json
from pathlib import Path

PROJECT_ROOT = Path('D:/ai coach fonus/code_test_fonus/fonus')
INDEXES_DIR = PROJECT_ROOT / 'indexes'
DGCA_DIR = PROJECT_ROOT / 'dgca_index_store'
BOOKS_JSON = PROJECT_ROOT / 'data' / 'books.json'

with open(BOOKS_JSON, encoding='utf-8') as f:
    books_data = json.load(f)

modules = books_data.get('modules', {})

print('FONUS FINAL INDEX VERIFICATION REPORT')
print('='*60)

all_ok = True

for mod_id, mod_data in modules.items():
    books = mod_data.get('books', [])
    
    if mod_id == 'M10':
        index_dir = DGCA_DIR
        label = 'dgca_index_store'
    else:
        index_dir = INDEXES_DIR / mod_id
        label = f'indexes/{mod_id}'
    
    report_path = index_dir / 'index_report.json'
    bm25_path = index_dir / 'bm25_nodes.pkl'
    
    index_exists = index_dir.exists()
    report_exists = report_path.exists()
    bm25_exists = bm25_path.exists()
    
    if report_exists:
        with open(report_path) as f:
            report = json.load(f)
        chunks = report.get('total_chunks', 0)
        pages = report.get('total_pages', 0)
        indexed_files = report.get('files_indexed', [])
        file_count = len(indexed_files)
    else:
        chunks = pages = file_count = 0
        indexed_files = []
    
    # Skip books with type 'regulatory'
    expected_books = [b['file'] for b in books if b.get('type') != 'regulatory']
    
    status = 'OK' if (index_exists and report_exists and bm25_exists) else 'FAIL'
    if status == 'FAIL':
        all_ok = False
    
    print(f'\n[{status}] {mod_id} ({label})')
    print(f'  Books expected : {len(expected_books)}')
    print(f'  Files indexed  : {file_count}')
    print(f'  Pages loaded   : {pages}')
    print(f'  Chunks created : {chunks}')
    print(f'  BM25 nodes     : {"YES" if bm25_exists else "MISSING"}')
    
    missing = [b for b in expected_books 
               if not any(b in f for f in indexed_files)]
    if missing:
        all_ok = False
        print(f'  MISSING BOOKS:')
        for m in missing:
            print(f'    - {m}')

print()
print('='*60)
if all_ok:
    print('RESULT: ALL INDEXES VERIFIED OK')
else:
    print('RESULT: SOME ISSUES FOUND - CHECK ABOVE')
print('='*60)
