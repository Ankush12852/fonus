import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def find_all_index_locations():
    locations = []
    # 1. Search recursively for folders containing docstore.json
    for root, dirs, files in os.walk(PROJECT_ROOT):
        # skip useless dirs
        if any(skip in root for skip in ['node_modules', '.git', '.next', '__pycache__', 'venv']):
            continue
        if 'docstore.json' in files:
            locations.append(Path(root))
    return locations

def extract_paths_from_main_py():
    paths = []
    main_py_path = PROJECT_ROOT / "backend" / "main.py"
    if main_py_path.exists():
        with open(main_py_path, "r", encoding="utf-8") as f:
            content = f.read()
            # simple regex to find Paths
            if 'PROJECT_ROOT / "dgca_index_store"' in content:
                paths.append(PROJECT_ROOT / "dgca_index_store")
            if 'PROJECT_ROOT / "indexes"' in content:
                paths.append(PROJECT_ROOT / "indexes")
    return paths

def get_source_files():
    data_dir = PROJECT_ROOT / "data" / "Modules"
    sources = {}
    warning_files = []
    
    if not data_dir.exists():
        return sources, warning_files
        
    for mod_dir in data_dir.iterdir():
        if mod_dir.is_dir():
            files = []
            for root, _, filenames in os.walk(mod_dir):
                for f in filenames:
                    if f.lower().endswith(('.pdf', '.txt', '.docx', '.csv', '.md')):
                        files.append(os.path.basename(f))
            
            if files:
                mod_name = mod_dir.name.split()[0].upper()
                if mod_name.startswith('M'):
                    sources[mod_name] = sources.get(mod_name, []) + files
                else:
                    warning_files.extend(files)
                    
    return sources, warning_files

def get_indexed_files(index_locations):
    indexed = {}
    
    def extract_files_robust(json_path):
        extracted = set()
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                
            def find_file_names(obj):
                if isinstance(obj, dict):
                    for k, v in obj.items():
                        if k == 'file_name':
                            extracted.add(os.path.basename(str(v)))
                        else:
                            find_file_names(v)
                elif isinstance(obj, list):
                    for item in obj:
                        find_file_names(item)
                        
            find_file_names(data)
        except Exception:
            pass
        return list(extracted)

    for loc in index_locations:
        docstore_path = loc / "docstore.json"
        if docstore_path.exists():
            files = extract_files_robust(docstore_path)
            if files:
                # determine module key from folder name if applicable
                if loc.name == 'dgca_index_store':
                    mod_key = 'M10'
                else:
                    mod_key = loc.name.upper()
                
                indexed[mod_key] = indexed.get(mod_key, []) + files
    return indexed

def main():
    print("STEP 1: Searching for actual index locations recursively...")
    found_locations = find_all_index_locations()
    
    print("\nSTEP 2: Checking backend/main.py for loaded index paths...")
    main_py_paths = extract_paths_from_main_py()
    
    print("\nSTEP 3: Compiling found locations:")
    report_lines = []
    report_lines.append("═══════════════════════════════")
    report_lines.append("FONUS INDEX AUDIT REPORT (v2)")
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("═══════════════════════════════\n")
    
    report_lines.append("🔍 INDEX LOCATIONS FOUND:")
    report_lines.append(f"From main.py configuration:")
    for p in main_py_paths:
        report_lines.append(f"  - {p.relative_to(PROJECT_ROOT) if p.is_relative_to(PROJECT_ROOT) else p}")
        
    report_lines.append(f"\nDiscovered docstore.json locations recursively:")
    for loc in sorted(found_locations):
        report_lines.append(f"  - {loc.relative_to(PROJECT_ROOT) if loc.is_relative_to(PROJECT_ROOT) else loc}")
        
    print("Gathering source files from data/Modules...")
    sources, warning_files = get_source_files()
    
    print("Extracting exact file metadata from all docstore.json files...")
    indexed = get_indexed_files(found_locations)
    
    success_files = []
    missing_files = []
    
    for mod_key, files in sources.items():
        mod_indexed = indexed.get(mod_key, [])
        mod_indexed_lower = {f.lower(): f for f in mod_indexed}
        
        for f in files:
            f_lower = f.lower()
            if f_lower in mod_indexed_lower:
                success_files.append((mod_key, mod_indexed_lower[f_lower]))
            else:
                missing_files.append((mod_key, f))
    
    indexed_by_mod = {}
    for mod_key, f in success_files:
        indexed_by_mod.setdefault(mod_key, []).append(f)
        
    report_lines.append("\n\n✅ ACTUALLY INDEXED FILES IN INDEX STORES:")
    # We will also print files from index that might not be in our source list, to be comprehensive
    all_indexed_total = sum(len(set(v)) for v in indexed.values())
    report_lines.append(f"[Total unique files found inside docstores: {all_indexed_total}]\n")
    
    for mod_key in sorted(indexed_by_mod.keys(), key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)):
        report_lines.append(f"- {mod_key} (Matched with source data/Modules):")
        for f in sorted(set(indexed_by_mod[mod_key])):
            report_lines.append(f"  - {f}")
    if not indexed_by_mod:
        report_lines.append("  (None)")
    report_lines.append("\n")
    
    report_lines.append(f"❌ MISSING FROM INDEX ({len(missing_files)}):")
    for mod_key, f in sorted(missing_files, key=lambda x: (int(''.join(filter(str.isdigit, x[0])) or 0), x[1])):
        report_lines.append(f"- {f} → should be in {mod_key}")
    if not missing_files:
        report_lines.append("  (None)")
        
    total_sources = sum(len(v) for v in sources.values())
    total_missing = len(missing_files)
    total_matched = len(success_files)
    coverage = (total_matched / total_sources * 100) if total_sources > 0 else 0

    report_lines.append("\n═══════════════════════════════")
    report_lines.append("SUMMARY:")
    report_lines.append(f"Total source files found in data/Modules: {total_sources}")
    report_lines.append(f"Total currently matching in index: {total_matched}")
    report_lines.append(f"Index coverage: {coverage:.1f}%")
    report_lines.append("═══════════════════════════════")
    
    report_text = "\n".join(report_lines)
    try:
        sys.stdout.buffer.write(report_text.encode('utf-8'))
    except Exception:
        print(report_text.encode('utf-8', errors='ignore').decode())
    
    out_path = Path(__file__).resolve().parent / "index_audit_report.txt"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    print(f"\nReport saved successfully to: {out_path}")

if __name__ == '__main__':
    main()
