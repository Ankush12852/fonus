import os

# ============================================================
# CLOUDFLARE R2 STORAGE CONFIGURATION
# ============================================================
# 
# What is Cloudflare R2?
# It is a "Cloud Storage" service. Instead of keeping 3.5GB of 
# PDFs on our small server, we upload them to Cloudflare.
# This makes our server faster and saves disk space.
#
# R2 is compatible with "S3" (Amazon's storage standard),
# so we use a library called 'boto3' to talk to it.
# ============================================================

# This is the public web address where your PDFs will be visible.
# We read it from the .env file (R2_PUBLIC_URL).
R2_BASE_URL = os.getenv("R2_PUBLIC_URL", "https://your-r2-url.r2.dev")

def get_pdf_url(filename):
    """
    Takes a filename like 'Module_10.pdf' and returns the full 
    internet link to that file on Cloudflare R2.
    """
    if not filename:
        return ""
    
    # Remove any local path parts if they exist (just in case)
    clean_filename = os.path.basename(filename)
    
    # Return the full URL
    # Example: https://your-r2-url.r2.dev/Module_10.pdf
    return f"{R2_BASE_URL}/{clean_filename}"
