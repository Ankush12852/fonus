#!/bin/bash

# ============================================================
# FONUS — SSL Certificate Setup Script
# 
# This script runs on your Ubuntu VPS to get a FREE SSL
# certificate from Let's Encrypt for your domain.
#
# What this does:
#   1. Installs certbot (the Let's Encrypt tool)
#   2. Gets a certificate for your domain
#   3. Copies certs to the nginx/ssl/ folder
#   4. Sets up automatic renewal every 90 days
#
# HOW TO USE:
#   1. SSH into your VPS: ssh root@YOUR_SERVER_IP
#   2. Clone your project to the server
#   3. Set your domain: export DOMAIN=fonus.co.in (or your domain)
#   4. Run: chmod +x scripts/setup-ssl.sh && ./scripts/setup-ssl.sh
#
# IMPORTANT: Your domain MUST be pointing to this server's IP
# BEFORE running this script! (Set this in your domain registrar's
# DNS settings: A record → your server's public IP address)
# ============================================================

# ── Safety: Exit immediately on any error ────────────────────
# If any command fails, the whole script stops.
# This prevents partial setup which is worse than no setup.
set -e

# ── Colour helpers for readable output ───────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'   # No Color (reset)

print_step() {
    echo -e "\n${GREEN}[STEP]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}


# ── Check: Must be run as root (or with sudo) ────────────────
if [ "$EUID" -ne 0 ]; then
    print_error "Please run this script as root: sudo ./scripts/setup-ssl.sh"
    exit 1
fi


# ── Step 0: Read the domain name ─────────────────────────────
# The domain should be set as an environment variable.
# Example: export DOMAIN=fonus.co.in
# Or you can edit this line to hardcode it (not recommended).
DOMAIN="${DOMAIN:-}"

if [ -z "$DOMAIN" ]; then
    print_error "Domain not set! Run: export DOMAIN=yourdomain.com"
    print_error "Then run this script again."
    exit 1
fi

# Email for Let's Encrypt renewal notifications.
# Change this to your real email.
EMAIL="${CERTBOT_EMAIL:-admin@${DOMAIN}}"

# The nginx/ssl folder where we'll copy certs for Docker.
SSL_DIR="$(dirname "$0")/../nginx/ssl"

print_step "Setting up SSL for domain: ${DOMAIN}"
print_step "Certificate renewal alerts will go to: ${EMAIL}"


# ── Step 1: Update package lists ─────────────────────────────
# Always run `apt update` before installing anything on Ubuntu.
# This refreshes the list of available packages.
print_step "Updating Ubuntu package list..."
apt-get update -y


# ── Step 2: Install certbot ──────────────────────────────────
# Certbot is the official Let's Encrypt client.
# snap is the recommended way to install certbot on Ubuntu 20/22/24.
print_step "Installing snapd (required for certbot)..."
apt-get install -y snapd

print_step "Installing certbot via snap..."
snap install --classic certbot

# Create a symlink so we can just type "certbot" anywhere
ln -sf /snap/bin/certbot /usr/bin/certbot

certbot --version
print_step "Certbot installed successfully!"


# ── Step 3: Stop any existing web server on port 80 ─────────
# Certbot's "standalone" mode needs port 80 free.
# If Nginx is already running (bare metal, not Docker), stop it.
# If using Docker, docker-compose should be stopped first.
print_warn "Stopping any existing Nginx on this server (if any)..."
systemctl stop nginx 2>/dev/null || true
docker-compose down 2>/dev/null || true


# ── Step 4: Get the SSL certificate from Let's Encrypt ───────
# certbot certonly → get cert but don't auto-configure a web server
# --standalone → certbot runs its own temporary web server on port 80
# --agree-tos → agree to Let's Encrypt terms of service
# --no-eff-email → don't share email with EFF (optional)
# -d → specify the domain(s) to get cert for
print_step "Obtaining SSL certificate for ${DOMAIN}..."
certbot certonly \
    --standalone \
    --agree-tos \
    --no-eff-email \
    --email "${EMAIL}" \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}"

print_step "Certificate obtained!"
echo "  Certificate: /etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
echo "  Private key: /etc/letsencrypt/live/${DOMAIN}/privkey.pem"


# ── Step 5: Copy certificates to nginx/ssl/ folder ───────────
# Docker mounts ./nginx/ssl into the Nginx container.
# So we copy the certs there so Nginx can find them.
print_step "Copying certificates to ${SSL_DIR}..."
mkdir -p "${SSL_DIR}"

# Copy the full certificate chain (cert + intermediate certs)
cp "/etc/letsencrypt/live/${DOMAIN}/fullchain.pem" "${SSL_DIR}/fullchain.pem"

# Copy the private key (KEEP THIS SECURE — never share it!)
cp "/etc/letsencrypt/live/${DOMAIN}/privkey.pem" "${SSL_DIR}/privkey.pem"

# Set secure permissions on the private key
chmod 600 "${SSL_DIR}/privkey.pem"
chmod 644 "${SSL_DIR}/fullchain.pem"

print_step "Certificates copied to ${SSL_DIR}!"


# ── Step 6: Create a renewal hook ───────────────────────────
# Let's Encrypt certs expire every 90 days.
# This hook automatically copies new certs after renewal.
# It runs whenever certbot successfully renews the cert.
print_step "Setting up automatic renewal hook..."
HOOK_FILE="/etc/letsencrypt/renewal-hooks/post/fonus-copy-certs.sh"

# Detect the project directory (where docker-compose.yml is)
PROJECT_DIR="$(realpath "$(dirname "$0")/..")"

cat > "${HOOK_FILE}" << HOOKSCRIPT
#!/bin/bash
# Auto-renewal hook for Fonus SSL certificates
# This runs automatically after certbot renews the certificate.
echo "[Fonus SSL Renewal] Copying new certs to Docker nginx volume..."
cp /etc/letsencrypt/live/${DOMAIN}/fullchain.pem ${PROJECT_DIR}/nginx/ssl/fullchain.pem
cp /etc/letsencrypt/live/${DOMAIN}/privkey.pem   ${PROJECT_DIR}/nginx/ssl/privkey.pem
chmod 600 ${PROJECT_DIR}/nginx/ssl/privkey.pem
chmod 644 ${PROJECT_DIR}/nginx/ssl/fullchain.pem

# Reload Nginx inside Docker container (no downtime)
echo "[Fonus SSL Renewal] Reloading Nginx..."
docker exec fonus-nginx nginx -s reload || true
echo "[Fonus SSL Renewal] Done!"
HOOKSCRIPT

chmod +x "${HOOK_FILE}"
print_step "Renewal hook installed at ${HOOK_FILE}"


# ── Step 7: Set up auto-renewal via cron ─────────────────────
# Let's Encrypt recommends renewing twice a day (certbot only
# actually renews when the cert is within 30 days of expiry).
# This cron job checks every day at 3:00 AM and 3:00 PM.
print_step "Setting up automatic renewal cron job..."

CRON_LINE="0 3,15 * * * certbot renew --quiet --post-hook '${HOOK_FILE}'"

# Add the cron job only if it doesn't already exist
if ! crontab -l 2>/dev/null | grep -q "certbot renew"; then
    (crontab -l 2>/dev/null; echo "${CRON_LINE}") | crontab -
    print_step "Cron job added: certbot will check for renewal daily at 3am and 3pm"
else
    print_warn "Certbot cron job already exists, skipping..."
fi


# ── Step 8: Test the renewal process ─────────────────────────
# This does a "dry run" — simulates renewal without actually doing it.
# If this passes, real renewal will work fine.
print_step "Testing certificate renewal (dry run)..."
certbot renew --dry-run && echo -e "${GREEN}Renewal test PASSED!${NC}"


# ── Done! ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}============================================${NC}"
echo -e "${GREEN}  SSL Setup Complete for ${DOMAIN}!${NC}"
echo -e "${GREEN}============================================${NC}"
echo ""
echo "  Certificates are in: ${SSL_DIR}/"
echo "  Auto-renewal: daily at 3am and 3pm via cron"
echo ""
echo "  Next steps:"
echo "  1. Make sure your domain's A record points to this server's IP"
echo "  2. Start the app: docker-compose up -d"
echo "  3. Visit: https://${DOMAIN}"
echo ""
