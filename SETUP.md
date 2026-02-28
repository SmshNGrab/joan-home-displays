# Setup Guide

This guide walks you through setting up a full Joan e-ink display network from scratch.

---

## Prerequisites

- Ubuntu Server (20.04 or 22.04 LTS recommended)
- Docker + Docker Compose installed
- One or more Visionect Joan 6 devices on your local network
- Basic comfort with the Linux terminal

---

## Step 1 — Prepare Your Server

### Install Docker
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker
```

### Clone this repo
```bash
git clone https://github.com/YOUR_USERNAME/joan-home-display-network
cd joan-home-display-network
```

### Create your config
```bash
cp .env.example .env
nano .env
```

Fill in your values — at minimum you need `SERVER_IP` (your server's LAN IP address).

---

## Step 2 — Start the Docker Stack

```bash
cp docker-compose.example.yml docker-compose.yml
docker compose up -d
```

Verify all containers are running:
```bash
docker compose ps
```

You should see these containers all showing `Up`:
- `visionect-server`
- `visionect-db`
- `visionect-redis`
- `ha-static`
- `homeassistant` (optional)
- `pihole` (optional)

---

## Step 3 — Fix the VSS IPv6 Bug (Critical)

> ⚠️ **This step is required.** Without it, VSS enters an error loop and devices cannot receive content.

By default, VSS config sets `MasterHost` to `"localhost"`. On Linux, `localhost` resolves to `::1` (IPv6), which breaks VSS's internal address parsing.

**The fix:**

```bash
# Create the patched config
cat vss-config.json | python3 -c "
import json, sys
c = json.load(sys.stdin)
c['MasterHost'] = '127.0.0.1'
print(json.dumps(c, indent=2))
" > vss-config-patched.json
```

The `docker-compose.example.yml` already mounts this patched config into the container. This is handled automatically if you use the provided compose file.

**Verify the fix is working:**
```bash
docker exec visionect-server supervisorctl tail -5000 engine 2>&1 | tail -5
```

You should see `Engine up (X devices, X sessions)` — NOT `missing ']' in address`.

---

## Step 4 — Copy Display Pages

```bash
# Create the www directory if it doesn't exist
mkdir -p /path/to/www

# Copy all display HTML files
cp displays/*.html /path/to/www/

# Verify they're accessible
curl -s http://YOUR_SERVER_IP:8124/scripture.html | head -3
```

Replace `/path/to/www` with the actual path you configured in your `.env` file.

---

## Step 5 — Get Your VSS API Credentials

Open the VSS admin panel in your browser:
```
http://YOUR_SERVER_IP:8081
```

Navigate to **Settings → API** and note your:
- API Key
- API Secret

Add these to your `.env` file.

---

## Step 6 — Connect a Joan Device

1. Power on your Joan device
2. It will appear in the VSS admin panel at `http://YOUR_SERVER_IP:8081`
3. Note the device UUID (shown in the admin panel)
4. Run the registration script:

```bash
# Edit register-device.py with your device UUID and desired display name
python3 scripts/register-device.py
```

Or use the manual Python snippet (substitute your values):

```bash
docker exec -i homeassistant python3 - << 'PY'
import time, hmac, hashlib, base64, wsgiref.handlers, json
from urllib.request import Request, urlopen

BASE      = "http://visionect-server:8081"
API_KEY   = "YOUR_VSS_API_KEY"
API_SECRET= "YOUR_VSS_API_SECRET"
uuid      = "your-device-uuid-lowercase"

def signed(method, path, body=b""):
    date = wsgiref.handlers.format_date_time(time.time())
    ct = "application/json"
    sig = base64.b64encode(
        hmac.new(API_SECRET.encode(), f"{method}\n\n{ct}\n{date}\n{path}".encode(), hashlib.sha256).digest()
    ).decode()
    return Request(BASE + path,
        headers={"Date": date, "Content-Type": ct, "Authorization": f"{API_KEY}:{sig}"},
        data=body or None, method=method)

# Name the device and set landscape rotation
with urlopen(signed("GET", f"/api/device/{uuid}"), timeout=10) as r:
    device = json.loads(r.read())
device["Options"]["Name"] = "My Display Name"
device["Displays"][0]["Rotation"] = 2   # 2 = correct landscape orientation
with urlopen(signed("PUT", f"/api/device/{uuid}", json.dumps(device).encode()), timeout=10) as r:
    print(f"Device updated: {r.status}")

time.sleep(1)

# Point it at an HTML page
session = {
    "Uuid": uuid,
    "Backend": {
        "Name": "HTML",        # MUST be "HTML" — NOT "HTTP"
        "Fields": {
            "url": "http://YOUR_SERVER_IP:8124/scripture.html",  # lowercase "url"
            "ReloadTimeout": "3600"
        }
    },
    "Options": {
        "Beautify": "pretty,gamma=1.1",
        "ChangesAutodetect": "true,threshold=0",
        "DefaultDithering": "none",
        "DefaultEncoding": "4"
    }
}
with urlopen(signed("PUT", f"/api/session/{uuid}", json.dumps(session).encode()), timeout=10) as r:
    print(f"Session set: {r.status}")

time.sleep(1)

with urlopen(signed("POST", f"/api/session/{uuid}/restart", b""), timeout=10) as r:
    print(f"Restarted: {r.status}")
PY
```

---

## Step 7 — Set Up the System Monitor (Optional)

If you want the System Monitor display with Pi-hole stats:

```bash
# Install requests library
pip3 install requests

# Edit the script with your Pi-hole IP and password
nano scripts/sysmon-update.py

# Test it
python3 scripts/sysmon-update.py

# Verify output
curl -s http://YOUR_SERVER_IP:8124/sysmon.json | python3 -m json.tool | head -15

# Add to cron (runs every 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/bin/python3 /path/to/scripts/sysmon-update.py >> /tmp/sysmon.log 2>&1") | crontab -
```

---

## Key Things to Know

### Display dimensions
All HTML pages should be exactly **1024×758 pixels** in landscape orientation.

### Touch zones
E-ink touch has 5–15 second latency (device → VSS → render → push back). Always use **large tap zones** (half-screen or more). Small buttons are unreliable.

### Emoji warning
Avoid emoji characters in display HTML — the VSS headless renderer may crash or render blank if emoji fonts are missing.

### Timezone
The server likely runs in UTC. If your displays show time, subtract your UTC offset in JavaScript:
```javascript
// Example: CST = UTC - 6
const localDate = new Date(new Date().getTime() - 6 * 3600000);
```

### Expanding disk space
If you installed Ubuntu with default LVM partitioning, you may have unused disk space. Check with:
```bash
lsblk
sudo docker system df
```
If your LVM volume is smaller than your physical partition, you can expand it online with no downtime:
```bash
sudo pvresize /dev/sda3
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
df -h /
```

---

## Next Steps

- Customize your weekly menu in `displays/menu.html`
- Add your own quotes to `displays/quotes.html`
- Add your own Bible verses to `displays/scripture.html`
- Build a new display page and share it!
