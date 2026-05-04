# Fonus — Production Deployment Guide

> **Who this is for:** This guide assumes you are a non-coder who has purchased a VPS
> (Virtual Private Server) and wants to deploy the Fonus app on it.
> Every step is explained in plain English.

---

## What You Need Before Starting

| Requirement | Where to Get It |
|---|---|
| A VPS running Ubuntu 22.04 | DigitalOcean, AWS, Hostinger, or any provider |
| A domain name (e.g. `fonus.co.in`) | GoDaddy, Namecheap, or your registrar |
| Your domain pointed to the server IP | See Step 1 below |
| Your `.env` files filled in | Use the `.env.example` files in `backend/` and `fonus-frontend/` |

---

## Step 1 — Point Your Domain to the Server

Before anything, your domain must point to your server's IP address.

1. Log in to your domain registrar (e.g. GoDaddy, Namecheap, Hostinger)
2. Go to **DNS Settings** for your domain
3. Add these records:

   | Type | Name | Value | TTL |
   |------|------|-------|-----|
   | A | `@` (or blank) | `YOUR_SERVER_IP` | Automatic |
   | A | `www` | `YOUR_SERVER_IP` | Automatic |

4. Wait 5-30 minutes for DNS to propagate globally
5. Verify: Run `ping fonus.co.in` — it should show your server IP

> **How to find your server IP:** Log in to your VPS provider dashboard.
> The IP is usually shown on the server overview page (e.g. `165.22.182.45`).

---

## Step 2 — SSH Into Your Server

SSH is how you remotely control your Ubuntu server from your computer.

**On Windows (PowerShell):**
```bash
ssh root@YOUR_SERVER_IP
# Example: ssh root@165.22.182.45
```

**On Mac/Linux (Terminal):**
```bash
ssh root@YOUR_SERVER_IP
```

When asked "Are you sure you want to continue?", type `yes` and press Enter.

---

## Step 3 — Update Ubuntu and Install Docker

Run these commands one by one on your server:

```bash
# Step 3a: Update Ubuntu's package list (like Windows Update)
apt-get update && apt-get upgrade -y

# Step 3b: Install Docker (the container engine)
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh

# Step 3c: Verify Docker installed correctly
docker --version
# Should show: Docker version 24.x.x

# Step 3d: Install Docker Compose plugin
apt-get install -y docker-compose-plugin

# Verify Docker Compose
docker compose version
# Should show: Docker Compose version v2.x.x
```

---

## Step 4 — Upload the Fonus Project to the Server

You have two options:

### Option A: Git Clone (Recommended)
```bash
# Install git if not already installed
apt-get install -y git

# Clone your repository
git clone https://github.com/YOUR_GITHUB_USERNAME/fonus.git /opt/fonus

# Go into the project folder
cd /opt/fonus
```

### Option B: Upload via SFTP (FileZilla)
1. Download FileZilla (free): https://filezilla-project.org/
2. Connect to your server: Host = `YOUR_SERVER_IP`, Username = `root`, Port = `22`
3. Upload the entire project folder to `/opt/fonus/`

---

## Step 5 — Set Up Your Environment Variables

```bash
# Go to the project folder
cd /opt/fonus

# Create the backend .env file from the template
cp backend/.env.example backend/.env

# Open it for editing (nano is a simple text editor)
nano backend/.env
```

Fill in all the values:
- `SUPABASE_URL` — from your Supabase project settings
- `SUPABASE_ANON_KEY` — from your Supabase project settings
- `GROQ_API_KEY_1` — from https://console.groq.com/keys
- `ALLOWED_ORIGINS` — `https://fonus.co.in,https://www.fonus.co.in`
- `JWT_SECRET` — generate one: `python3 -c "import secrets; print(secrets.token_hex(64))"`

Save and exit: Press `Ctrl+X`, then `Y`, then `Enter`.

```bash
# Create the frontend .env from the template
cp fonus-frontend/.env.example fonus-frontend/.env.local

# Edit it
nano fonus-frontend/.env.local
```

Fill in:
- `NEXT_PUBLIC_SUPABASE_URL` — same as backend
- `NEXT_PUBLIC_SUPABASE_ANON_KEY` — same as backend
- `NEXT_PUBLIC_API_URL` — `https://fonus.co.in`

---

## Step 6 — Get Free SSL Certificates

This gets a free HTTPS certificate from Let's Encrypt.

```bash
# Go into the project folder
cd /opt/fonus

# Set your domain as an environment variable
export DOMAIN=fonus.co.in
export CERTBOT_EMAIL=your-email@gmail.com

# Make the setup script executable
chmod +x scripts/setup-ssl.sh

# Run the SSL setup script
./scripts/setup-ssl.sh
```

> **Important:** This only works if your domain is already pointing to this server (Step 1).

If successful, you'll see:
```
SSL Setup Complete for fonus.co.in!
Certificates are in: ./nginx/ssl/
Auto-renewal: daily at 3am and 3pm via cron
```

---

## Step 7 — Start the Application

```bash
# Go into the project folder
cd /opt/fonus

# Build all containers and start them in the background
# -d means "detached" (runs in background, keeps running after you close SSH)
docker compose up -d --build
```

This will:
1. Build the Python backend container
2. Build the Next.js frontend container
3. Pull the Nginx container
4. Start all 3 containers connected to each other

Wait 1-2 minutes for everything to start (loading AI indexes takes time).

**Verify it's running:**
```bash
docker compose ps
```

You should see all three containers showing `running` status:
```
NAME              STATUS
fonus-nginx       running
fonus-backend     running
fonus-frontend    running
```

**Test the health endpoint:**
```bash
curl http://localhost/health
# Should return: {"status":"ok","service":"fonus-backend"}
```

**Visit your site:**
Open `https://fonus.co.in` in your browser — you should see the Fonus login page!

---

## Step 8 — Verify Everything Works

Run these quick checks:

```bash
# Check the backend is responding
curl https://fonus.co.in/health

# Check Nginx is forwarding correctly
curl -I https://fonus.co.in   # Should show "200 OK"

# Check SSL certificate is valid
curl -v https://fonus.co.in 2>&1 | grep "SSL certificate verify"
# Should show: SSL certificate verify ok
```

---

## Checking Logs When Something Breaks

### View all container logs:
```bash
cd /opt/fonus
docker compose logs
```

### View logs for a specific service:
```bash
# Backend (Python/FastAPI) logs
docker compose logs backend

# Frontend (Next.js) logs
docker compose logs frontend

# Nginx logs
docker compose logs nginx

# Follow logs in real-time (like watching a live feed)
docker compose logs -f backend
```

### View Nginx access/error logs directly:
```bash
# All recent requests
cat nginx/logs/access.log | tail -50

# Recent errors
cat nginx/logs/error.log | tail -50
```

---

## Common Troubleshooting

### Problem: Site not loading - browser shows connection refused

**Check:** Is the server running?
```bash
docker compose ps
```

**Fix:** Restart everything:
```bash
docker compose down
docker compose up -d
```

---

### Problem: SSL/HTTPS not working - "Not Secure" in browser

**Check:** Did the SSL setup script run successfully?
```bash
ls nginx/ssl/
# Should list: fullchain.pem  privkey.pem
```

**Fix:** Re-run the SSL setup:
```bash
export DOMAIN=fonus.co.in
./scripts/setup-ssl.sh
docker compose restart nginx
```

---

### Problem: Backend gives 500 error - AI not working

**Check:** Are the Groq API keys set?
```bash
grep GROQ backend/.env
```

**Check backend logs:**
```bash
docker compose logs backend | tail -30
```

---

### Problem: CORS error in browser (frontend can't talk to backend)

**Check:** Is `ALLOWED_ORIGINS` set correctly in `backend/.env`?
```bash
grep ALLOWED_ORIGINS backend/.env
```

It should contain your domain:
```
ALLOWED_ORIGINS=https://fonus.co.in,https://www.fonus.co.in
```

**Fix:** Edit the file and restart:
```bash
nano backend/.env
docker compose restart backend
```

---

### Problem: Rate limit errors (429 Too Many Requests)

This is expected behaviour — it means the rate limiting is working.
A single IP is making too many requests in a short time.

Nginx allows 30 requests/second with bursts up to 50.
SlowAPI allows 200 requests/minute per IP.

If legitimate users are being blocked, increase the limits in:
- `nginx/nginx.conf` — find `rate=30r/s` and `burst=50`
- `backend/main.py` — find `default_limits=["200/minute"]`

Then restart: `docker compose restart nginx backend`

---

### Problem: Changes not showing after editing code

After editing code, you need to rebuild the containers:
```bash
docker compose up -d --build
```

---

## Keeping the App Running After Reboot

By default, Docker containers stop when the server reboots.
Enable Docker to auto-start:

```bash
systemctl enable docker
```

The `restart: always` setting in `docker-compose.yml` ensures
each container automatically restarts if it crashes or if the
server reboots.

---

## Quick Reference Commands

```bash
# Start everything
docker compose up -d

# Stop everything
docker compose down

# Restart one service
docker compose restart backend

# Rebuild and restart after code changes
docker compose up -d --build

# View live logs
docker compose logs -f

# Check status
docker compose ps

# Open a shell inside a container (for debugging)
docker compose exec backend bash
docker compose exec frontend sh
```

---

## Updating the App

```bash
# 1. Pull latest code from GitHub
git pull origin main

# 2. Rebuild and restart
docker compose up -d --build

# 3. Verify it's running
docker compose ps
docker compose logs --tail=20
```

---

*Built with love for India's first AI-powered DGCA AME exam platform.*
