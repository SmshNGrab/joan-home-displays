# Troubleshooting Guide

Solutions to every issue encountered during real-world setup and operation.

---

## 🔴 Critical: VSS Error Loop — `missing ']' in address`

**Symptom:**
```
dial tcp: address [:32990: missing ']' in address
```
Repeats in the VSS networkmanager log every 5 seconds. Devices may connect but never receive content.

**Root Cause:**
VSS config has `"MasterHost": "localhost"`. On Linux, `localhost` resolves to `::1` (IPv6 via `/etc/hosts`). The Go binary calls `LocalAddr()` on the IPv6 connection, which returns `[::1]:32990`. A naive string split on `:` produces `[` as the address — causing the loop.

**Fix:**
Change `MasterHost` from `"localhost"` to `"127.0.0.1"` in `vss-config.json` and mount it into the container:

```json
{
  "MasterHost": "127.0.0.1"
}
```

Mount it at BOTH config paths (VSS checks two locations depending on version):
```yaml
volumes:
  - ./vss-config.json:/opt/visionect/vss/config.json
  - ./vss-config.json:/opt/visionect/vss/config/config.json
```

**Verify fix:**
```bash
docker exec visionect-server supervisorctl tail -5000 engine 2>&1 | tail -5
# Should show: Engine up (X devices, X sessions)
```

---

## 🔴 Display Shows "Failed to load preview"

**Symptom:** Black screen with a ⊘ icon and "Failed to load preview" in the VSS admin panel. Physical device shows nothing or old content.

**Cause 1: Wrong Backend type**
Session `Backend.Name` is set to `"HTTP"` (external renderer) instead of `"HTML"` (WebKit renderer).

```bash
# Check what backend is set
# GET /api/session/YOUR-UUID  →  look at Backend.Name
```

Fix: Re-PUT the session with `"Name": "HTML"`.

**Cause 2: Wrong URL field casing**
Field key is `"Url"` (capital U) instead of `"url"` (lowercase). VSS silently accepts the wrong casing but stores it empty.

Fix: Use lowercase `"url"` in the Fields object:
```json
"Fields": {
    "url": "http://YOUR_SERVER_IP:8124/page.html"
}
```

**Cause 3: HTML file not accessible**
The file doesn't exist at the path nginx is serving.

```bash
# Verify
curl -s http://YOUR_SERVER_IP:8124/page.html | head -3
# Should return HTML, not a 404 page
```

---

## 🟡 Session PUT Returns 204 but URL Not Saved

**Symptom:** `PUT /api/session/UUID` returns 204 (success) but a subsequent GET shows empty Fields.

**Cause:** Wrong field key casing. VSS returns 204 even when it ignores unknown fields.

**Fix:** Always use lowercase `"url"` — not `"Url"`, `"URL"`, or `"href"`.

**Verify after every PUT:**
```python
with urlopen(signed("GET", f"/api/session/{uuid}"), timeout=10) as r:
    s = json.loads(r.read())
    print("Backend:", s["Backend"]["Name"])
    print("Fields:", s["Backend"]["Fields"])
# Fields should NOT be empty {}
```

---

## 🟡 Session Restart Returns 500

**Symptom:** `POST /api/session/UUID/restart` returns HTTP 500.

**Cause:** The device is currently offline (not connected to VSS). VSS cannot push a restart to a disconnected device.

**This is not a real error.** The session config was already saved by the previous PUT. The device will apply the new session automatically when it next connects (usually within 60 seconds on heartbeat).

**Fix:** Wait 60 seconds, then unplug and replug the device to force an immediate reconnect.

---

## 🟡 Touch Not Working / Wrong Area Responds

**Symptom:** Touching the screen plays the device click sound but the display doesn't update. Or the wrong element activates.

**Cause 1: Touch coordinates are rotated**
When `Rotation=2`, touch coordinates from the device may not map correctly to HTML element positions, especially near screen edges.

**Fix:** Use very large tap zones. Instead of small buttons:
```css
/* Bad - small button at bottom */
button { width: 120px; height: 50px; }

/* Good - half the screen */
#tap-left  { position: absolute; left: 0;   top: 0; width: 512px; height: 758px; }
#tap-right { position: absolute; right: 0;  top: 0; width: 512px; height: 758px; }
```

**Cause 2: Touch latency confusion**
E-ink touch has 5–15 second end-to-end latency. Users may tap multiple times thinking nothing happened.

**Fix:** Design UI that acknowledges this. Display a "Processing..." state if possible.

---

## 🟡 Display Not Updating After File Change

**Symptom:** You edited an HTML file on the server but the device still shows old content.

**Cause:** VSS caches the rendered page. The device won't re-render until a session restart is triggered.

**Fix:** Trigger a restart:
```python
# POST /api/session/UUID/restart  (with empty body b"")
with urlopen(signed("POST", f"/api/session/{uuid}/restart", b""), timeout=10) as r:
    print(r.status)  # Should be 204
```

---

## 🟡 All API Responses Return `None` for Device Fields

**Symptom:** Python script GETs device info but all fields like `IsOnline`, `Name` return `None`.

**Cause:** The actual JSON key names are different from what you're accessing. Common mismatch:
- `IsOnline` → actual key is `State` (value: `"online"` or `"offline"`)
- `Options.Name` → present only if you've set it; absent on new devices

**Fix:** Always dump the raw response first to see actual structure:
```python
with urlopen(signed("GET", f"/api/device/{uuid}"), timeout=10) as r:
    print(r.read().decode())  # See the real JSON structure
```

---

## 🟡 Device UUID Case Issues

**Symptom:** API calls with the UUID from the VSS admin panel return 404 or unexpected results.

**Cause:** VSS stores UUIDs in lowercase internally, but the admin panel and device firmware may display them in uppercase or mixed case.

**Fix:** Always lowercase the UUID before using it in API calls:
```python
uuid = "4D002300-1350-4B4D-5231-302000000000".lower()
# → "4d002300-1350-4b4d-5231-302000000000"
```

---

## 🟡 Emoji Causes Render Failure

**Symptom:** Display shows "Failed to load preview" or renders completely blank after adding emoji to an HTML file.

**Cause:** The VSS headless browser (WebKit) may not have emoji fonts installed in the container.

**Fix:** Remove emoji and use text or HTML entities instead:
```html
<!-- Bad -->
<h1>🍽️ Family Menu</h1>

<!-- Good -->
<h1>Family Menu</h1>

<!-- Or use ASCII art / symbols -->
<h1>[ Family Menu ]</h1>
```

---

## 🟡 Pi-hole API Returns `unauthorized`

**Symptom:**
```json
{"error": {"key": "unauthorized", "message": "Unauthorized"}}
```

**Cause:** Pi-hole v6 requires authentication for all API calls. The old `/admin/api.php` endpoint no longer works.

**Fix:** Authenticate first, then use the session token:
```python
import requests

r = requests.post("http://YOUR_PIHOLE_IP/api/auth",
    json={"password": "YOUR_PIHOLE_PASSWORD"}, timeout=5)
sid = r.json()["session"]["sid"]

# Now use sid in all requests
stats = requests.get("http://YOUR_PIHOLE_IP/api/stats/summary",
    headers={"sid": sid}, timeout=5).json()

# Log out when done (good practice)
requests.delete("http://YOUR_PIHOLE_IP/api/auth",
    headers={"sid": sid}, timeout=5)
```

**Note:** `domains_being_blocked` is under `response["gravity"]["domains_being_blocked"]`, not under `queries`.

---

## 🟡 Disk Space Running Low

**Symptom:** `df -h /` shows 80%+ usage. Docker operations may slow or fail.

**Cause 1: Ubuntu LVM default leaves ~50% unallocated**

Check if you have unallocated space:
```bash
lsblk
# If sda3 (29.8G) is larger than ubuntu-lv (13.4G), you have free space
```

Expand online with no downtime:
```bash
sudo pvresize /dev/sda3
sudo lvextend -l +100%FREE /dev/ubuntu-vg/ubuntu-lv
sudo resize2fs /dev/mapper/ubuntu--vg-ubuntu--lv
df -h /  # Should now show full disk
```

**Cause 2: Docker image bloat**
```bash
sudo docker system df       # See what's using space
docker system prune -f      # Remove unused images/containers/networks
```

---

## 🟢 Checking VSS Health

```bash
# All processes running?
docker exec visionect-server supervisorctl status

# Engine log (device activity, render errors)
docker exec visionect-server supervisorctl tail -5000 engine 2>&1 | tail -30

# Gateway log (device connections)
docker exec visionect-server supervisorctl tail -5000 gateway 2>&1 | tail -30

# Networkmanager log (should show "Engine up", not error loops)
docker exec visionect-server supervisorctl tail -5000 networkmanager 2>&1 | tail -10
```

---

## 🟢 Full Health Check

```bash
# Containers
docker compose ps

# Static files
curl -s http://YOUR_SERVER_IP:8124/scripture.html | head -3

# Disk
df -h /

# Cron jobs
crontab -l

# System monitor data
curl -s http://YOUR_SERVER_IP:8124/sysmon.json | python3 -m json.tool | head -10
```
