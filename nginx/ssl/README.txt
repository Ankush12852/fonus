# This folder holds your SSL certificates for HTTPS.
# These files are created automatically by running:
#   ./scripts/setup-ssl.sh
#
# Files that will appear here after running the SSL script:
#   fullchain.pem  — Your SSL certificate (public, safe to share)
#   privkey.pem    — Your private key (KEEP SECRET, never share!)
#
# Both files are excluded from Git via .gitignore
# (*.pem is in the gitignore — you are safe)
#
# For local development without HTTPS, use nginx-local.conf instead.
# That config only uses port 80 (HTTP) and doesn't need these files.
