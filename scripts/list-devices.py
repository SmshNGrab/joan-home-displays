#!/usr/bin/env python3
"""
list-devices.py — List all devices registered in VSS

Usage:
  python3 list-devices.py

Prints all devices with UUID, state, and name.
Use this to find the UUID of a newly connected device.
"""

import hmac
import hashlib
import json
import time
import os
from urllib.request import urlopen, Request

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

VSS_HOST   = os.environ.get("VSS_HOST",       "YOUR_SERVER_IP")
VSS_PORT   = int(os.environ.get("VSS_PORT",   "8081"))
API_KEY    = os.environ.get("VSS_API_KEY",    "YOUR_VSS_API_KEY")
API_SECRET = os.environ.get("VSS_API_SECRET", "YOUR_VSS_API_SECRET")

BASE = f"http://{VSS_HOST}:{VSS_PORT}/api"


def sign(method, path):
    ts  = str(int(time.time()))
    msg = f"{method} /api{path} {ts}"
    sig = hmac.new(API_SECRET.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return Request(f"{BASE}{path}",
        headers={"Authorization": f"{API_KEY}:{ts}:{sig}"})


def main():
    with urlopen(sign("GET", "/device/"), timeout=10) as r:
        devices = json.loads(r.read())

    if not devices:
        print("No devices found. Make sure devices are powered on and connected to VSS.")
        return

    print(f"{'UUID':<44} {'State':<10} {'Name'}")
    print("-" * 80)
    for d in devices:
        uuid  = d.get("Uuid", "").lower()
        state = d.get("State", "unknown")
        name  = d.get("Options", {}).get("Name", "(unnamed)")
        print(f"{uuid:<44} {state:<10} {name}")


if __name__ == "__main__":
    main()
