# FAQ

---

### Where do I get Joan devices?

Joan displays are made by [Visionect](https://www.visionect.com/). They were primarily sold as meeting room booking panels.

The best source is **eBay and Facebook Marketplace** — used Joan 6 devices regularly appear for $10–$40 each, dramatically less than the $500+ retail price. Search for: `"Joan 6"`, `"Visionect e-ink"`, `"E Ink meeting room display"`.

Look for devices that include the power cable. The Joan 6 uses USB-C 5V and is very low-power (full refresh uses about as much energy as a camera flash).

---

### What Joan models work with this setup?

Tested with **Joan 6** (1024×758px landscape). Other models should work the same way since VSS handles all of them — adjust your HTML dimensions accordingly:

| Model | Resolution | Notes |
|-------|-----------|-------|
| Joan 6 | 1024 × 758 | Tested ✅ |
| Joan 13 | 1600 × 1200 | Not tested |
| Joan Manager | 1024 × 758 | Different housing |

The VSS software is the same for all models.

---

### Can I use other e-ink displays (not Joan)?

Not with this setup. VSS is Visionect's proprietary server and only works with their hardware. However, the HTML display pages (scripture, hangman, etc.) are plain HTML/CSS/JS and could theoretically work with any display that has a browser — including:

- Raspberry Pi + small display running a kiosk browser
- Kindle browser hacks
- Any tablet in kiosk mode

The VSS-specific parts (device registration script, HMAC auth) would not apply.

---

### Do I need Home Assistant?

**No.** Home Assistant is included in the Docker Compose for future integration potential, but none of the current display pages require it. Everything runs off static HTML files served by nginx.

You can safely remove the HA service from `docker-compose.yml` if you don't want it.

---

### Do I need Pi-hole?

**No.** Pi-hole is included because it was already running on the same server. The system monitor display (`sysmon.html`) has a section that shows Pi-hole stats — that section will just show zeros if Pi-hole isn't running.

Remove the Pi-hole service from `docker-compose.yml` and comment out the Pi-hole section in `sysmon-update.py` if you don't want it.

---

### How do I add my own custom display?

1. Create an HTML file in your static files directory (`/home/ubuntu/homeassistant/config/www/` or wherever you configured `WWW_PATH`):

```html
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
  body {
    width: 1024px; height: 758px;
    margin: 0; overflow: hidden;
    font-family: sans-serif;
    background: white; color: black;
  }
</style>
</head>
<body>
  <h1>Hello Joan!</h1>
</body>
</html>
```

2. Register a session pointing to your file:

```python
# In your registration script, set:
"url": f"http://{SERVER_IP}:{WWW_PORT}/myfile.html"
```

3. Push the session to your device using the device registration script.

Tips:
- Always design for exactly **1024×758px**
- Use `overflow: hidden` — scrollbars confuse the renderer
- Test in Chrome at 1024×758 first (DevTools → device emulation → custom size)
- Avoid emoji — WebKit in VSS may not have emoji fonts

---

### How long do updates take to appear?

The full round-trip for a display update is:

1. VSS detects file/session change → renders via headless WebKit (**~2–5 seconds**)
2. Image queued for device → device polls VSS on its heartbeat schedule (**up to 15 seconds**)
3. Device receives image → performs e-ink refresh (**~1–2 seconds**)

**Total: 5–20 seconds** from file save to pixels changing. This is normal for e-ink.

If you want faster updates, you can trigger a manual session restart via the VSS API immediately after updating your file — this forces VSS to re-render and queue the update without waiting for the next heartbeat.

---

### Do the displays work during internet outages?

**Mostly yes.** The setup is designed to be LAN-only:

- VSS, nginx, and all HTML files run locally
- The current displayed image stays on screen indefinitely (e-ink holds without power)
- `menu.html`, `quotes.html`, `hangman.html` work entirely offline

What breaks during internet outage:
- `scripture.html` fetches from `bible-api.com` — it will show cached verse or blank
- `sysmon.html` DNS stats (Pi-hole) will stop updating (still shows last values)
- Pi-hole itself keeps blocking ads from its local database

---

### How much power do the devices use?

Very little. Joan 6 specs:
- Display refresh: ~8mA peak for ~1 second
- Standby (between refreshes): essentially zero
- Connected WiFi (polling): ~1–2mA average

For comparison: a single LED night light uses more power than 10 Joan displays actively refreshing.

---

### Can I add live data like weather or stock prices?

Yes. There are two approaches:

**Client-side (simpler):** Fetch the API directly from JavaScript in your HTML:
```javascript
fetch("https://wttr.in/?format=j1")
  .then(r => r.json())
  .then(data => { /* update the DOM */ });
```
Works fine for public APIs. The Joan device connects to your LAN; it can reach the internet through your router.

**Server-side (better for auth):** Add a collector script (like `sysmon-update.py`) that fetches from external APIs, writes to a JSON file, and your HTML reads from that. Keeps API keys off the client.

---

### The display is frozen / stuck on old content. How do I force a refresh?

Trigger a session restart via the API:
```python
with urlopen(signed("POST", f"/api/session/{uuid}/restart", b""), timeout=10) as r:
    print(r.status)  # 204 = success
```

If the device is offline (not connected), this will return 500 — that's normal. The device will refresh on its own when it reconnects.

---

### Can multiple devices show the same content?

Yes. Multiple devices can have sessions pointing to the same URL. They'll each independently poll VSS and refresh on their own schedule.

---

### How do I find a new device's UUID?

Two ways:

1. **VSS Admin panel** → `http://YOUR_SERVER_IP:8081` → Devices page. New devices appear automatically when powered on and connected to your WiFi.

2. **API:**
```bash
# List all devices
python3 -c "
import hmac, hashlib, time, json
from urllib.request import urlopen, Request

KEY = 'YOUR_VSS_API_KEY'
SECRET = 'YOUR_VSS_API_SECRET'
HOST = 'YOUR_SERVER_IP'

def sign(method, path):
    ts = str(int(time.time()))
    msg = method + ' /api' + path + ' ' + ts
    sig = hmac.new(SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return Request(f'http://{HOST}:8081/api{path}',
        headers={'Authorization': f'{KEY}:{ts}:{sig}'})

with urlopen(sign('GET', '/device/'), timeout=10) as r:
    for d in json.loads(r.read()):
        print(d.get('Uuid'), '|', d.get('State'), '|', d.get('Options', {}).get('Name', '(unnamed)'))
"
```

---

### The device connects to WiFi but doesn't appear in VSS

Joan devices must be configured to point at your VSS server IP. This is done via the **Joan app** (iOS/Android) during initial setup, or by resetting the device and reconfiguring it.

The device needs to know your server's IP and port (default: `11113`). Make sure:
- Port `11113` is open/not blocked by firewall: `sudo ufw allow 11113`
- The device and server are on the same subnet
- VSS gateway container is running: `docker compose ps visionect-server`

---

### I'm getting a lot of errors in the VSS logs

First, check which process is erroring:
```bash
docker exec visionect-server supervisorctl status
docker exec visionect-server supervisorctl tail -1000 engine 2>&1 | grep -i "error\|warn" | tail -20
```

The most common non-critical log noise:
- `certificate has expired or is not yet valid` — VSS uses self-signed certs; ignore
- `render timeout` — Display couldn't fetch content within deadline; verify your HTML URL is accessible
- `device offline` — Normal when device is sleeping or physically unplugged

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for critical errors.
