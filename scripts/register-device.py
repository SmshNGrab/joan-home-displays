#!/usr/bin/env python3
"""
register-device.py — Register a Joan device with a Visionect VSS session

Usage:
  python3 register-device.py

Fill in the configuration section below, then run the script.
It will:
  1. Name the device
  2. Set the rotation (0=portrait, 2=landscape)
  3. Create/update a session pointing at your HTML file
  4. Trigger a restart to apply immediately

Requires: Python 3.6+ (no third-party dependencies)
"""

import hmac
import hashlib
import json
import time
import os
from urllib.request import urlopen, Request
from urllib.error import HTTPError

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

# ── CONFIGURATION ──────────────────────────────────────────
VSS_HOST   = os.environ.get("VSS_HOST",       "YOUR_SERVER_IP")
VSS_PORT   = int(os.environ.get("VSS_PORT",   "8081"))
API_KEY    = os.environ.get("VSS_API_KEY",    "YOUR_VSS_API_KEY")
API_SECRET = os.environ.get("VSS_API_SECRET", "YOUR_VSS_API_SECRET")

# The device UUID (find it in VSS admin panel → Devices, or run list-devices.py)
DEVICE_UUID = "YOUR_DEVICE_UUID"

# Display name (shows in VSS admin panel)
DEVICE_NAME = "My Display"

# Rotation: 0=portrait, 2=landscape (Joan 6 should use 2)
ROTATION = 2

# The URL your device should display
# Use http:// and your server's LAN IP — NOT localhost
DISPLAY_URL = f"http://{VSS_HOST}:8124/your-page.html"
# ──────────────────────────────────────────────────────────

BASE = f"http://{VSS_HOST}:{VSS_PORT}/api"


def sign(method, path, body=b""):
    """Generate HMAC-SHA256 signed request for VSS API."""
    ts  = str(int(time.time()))
    msg = f"{method} /api{path} {ts}"
    sig = hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    req = Request(
        f"{BASE}{path}",
        data=body if body else None,
        method=method,
        headers={"Authorization": f"{API_KEY}:{ts}:{sig}"}
    )
    if body:
        req.add_header("Content-Type", "application/json")
    return req


def api_call(method, path, payload=None):
    body = json.dumps(payload).encode() if payload else b""
    try:
        with urlopen(sign(method, path, body), timeout=10) as r:
            status = r.status
            raw    = r.read()
            return status, json.loads(raw) if raw else None
    except HTTPError as e:
        return e.code, None


def main():
    uuid = DEVICE_UUID.lower()

    # Step 1: Check device exists
    print(f"Checking device {uuid}...")
    status, device = api_call("GET", f"/device/{uuid}")
    if status != 200:
        print(f"  Device not found (HTTP {status}). Is it connected to VSS?")
        print("  Check VSS admin: http://{VSS_HOST}:{VSS_PORT}")
        return

    print(f"  Found: {device.get('State', 'unknown')} state")

    # Step 2: Name and configure the device
    print(f"Setting device name to '{DEVICE_NAME}' with rotation {ROTATION}...")
    status, _ = api_call("PUT", f"/device/{uuid}", {
        "Uuid": uuid,
        "Options": {
            "Name": DEVICE_NAME,
            "Rotation": ROTATION
        }
    })
    print(f"  HTTP {status}" + (" (OK)" if status == 204 else " (unexpected)"))

    # Step 3: Create/update the session
    print(f"Setting session URL: {DISPLAY_URL}")
    session_payload = {
        "Uuid": uuid,
        "Backend": {
            "Name": "HTML",           # Must be "HTML" for WebKit renderer
            "Fields": {
                "url": DISPLAY_URL    # Must be lowercase "url"
            }
        },
        "Options": {
            "DefaultDithering": "Floyd-Steinberg",
            "RefreshTime": 900,       # Session timeout in seconds (0 = never)
            "DeviceAccessRule": "None"
        }
    }
    status, _ = api_call("PUT", f"/session/{uuid}", session_payload)
    print(f"  HTTP {status}" + (" (OK)" if status == 204 else " (unexpected)"))

    # Step 4: Verify the URL was saved (common gotcha: wrong key casing)
    _, session = api_call("GET", f"/session/{uuid}")
    if session:
        saved_url = session.get("Backend", {}).get("Fields", {}).get("url", "")
        if saved_url:
            print(f"  Verified URL saved: {saved_url}")
        else:
            print("  WARNING: URL field is empty after save!")
            print("  This usually means 'url' key got set as 'Url' — check the payload.")

    # Step 5: Trigger restart to apply immediately
    print("Triggering restart...")
    status, _ = api_call("POST", f"/session/{uuid}/restart")
    if status == 204:
        print("  Restart queued. Device will update within ~60 seconds.")
    elif status == 500:
        print("  HTTP 500 (device is offline, but config is saved — it'll apply on reconnect)")
    else:
        print(f"  HTTP {status}")

    print(f"\nDone! View device in VSS admin: http://{VSS_HOST}:{VSS_PORT}")


if __name__ == "__main__":
    main()
