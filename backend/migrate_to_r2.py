import os
import json
import boto3
from botocore.client import Config
from pathlib import Path

# ============================================================
# CLOUDFLARE R2 MIGRATION SCRIPT
# ============================================================
#
# This script moves your 3.5GB of PDFs from your local computer
# to Cloudflare R2 (the cloud).
#
# BEFORE RUNNING:
# 1. Make sure you have 'boto3' installed: pip install boto3
# 2. Make sure your .env file has the R2 credentials.
# ============================================================

def load_env():
    """Loads variables from .env file manually."""
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.exists():
        print("ERROR: .env file not found at project root!")
        return False
    
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()
    return True

def migrate():
    if not load_env():
        return

    # 1. Get credentials from environment
    account_id = os.getenv("R2_ACCOUNT_ID")
    access_key = os.getenv("R2_ACCESS_KEY")
    secret_key = os.getenv("R2_SECRET_KEY")
    bucket_name = os.getenv("R2_BUCKET_NAME")
    public_url = os.getenv("R2_PUBLIC_URL")

    if not all([account_id, access_key, secret_key, bucket_name]):
        print("ERROR: Missing R2 credentials in .env file!")
        return

    # 2. Setup R2 Client (Cloudflare R2 uses S3-compatible API)
    r2_endpoint = f"https://{account_id}.r2.cloudflarestorage.com"
    s3 = boto3.client(
        service_name="s3",
        endpoint_url=r2_endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(signature_version="s3v4"),
        region_name="auto" # R2 doesn't use regions, so we use 'auto'
    )

    # 3. Get list of files to upload
    books_dir = Path(__file__).resolve().parent.parent / "data" / "books"
    if not books_dir.exists():
        print(f"ERROR: Directory not found: {books_dir}")
        return

    files = list(books_dir.glob("*"))
    total_files = len(files)
    print(f"Found {total_files} files in {books_dir}")

    file_map = {}

    # 4. Upload each file
    for i, file_path in enumerate(files, 1):
        filename = file_path.name
        print(f"Uploading file {i} of {total_files}: {filename}")
        
        try:
            # Upload to R2
            with open(file_path, "rb") as data:
                s3.upload_fileobj(data, bucket_name, filename)
            
            # Save the URL in our map
            r2_url = f"{public_url}/{filename}"
            file_map[filename] = r2_url
            
        except Exception as e:
            print(f"FAILED to upload {filename}: {e}")

    # 5. Save the mapping file
    map_file = Path(__file__).resolve().parent / "r2_file_map.json"
    with open(map_file, "w", encoding="utf-8") as f:
        json.dump(file_map, f, indent=4)

    print("-" * 30)
    print(f"SUCCESS! Migration complete.")
    print(f"Mapping saved to: {map_file}")
    print("-" * 30)

if __name__ == "__main__":
    migrate()
