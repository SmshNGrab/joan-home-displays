#!/usr/bin/env python3
"""
sysmon-update.py — System Monitor Data Collector
Collects server stats + Pi-hole stats and writes to sysmon.json
for the sysmon.html dashboard display.

SETUP:
  1. Copy .env.example to .env and fill in your values
  2. Install dependencies: pip3 install psutil requests python-dotenv
  3. Schedule with cron: */5 * * * * /usr/bin/python3 /home/ubuntu/sysmon-update.py

OR without .env, just set the variables at the top of this file directly.
"""

import json
import os
import subprocess
import socket
from datetime import datetime, timezone, timedelta

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))
except ImportError:
    pass

# ── CONFIGURATION ──────────────────────────────────────────
# Either set these here or in .env (env vars take priority)
PIHOLE_HOST     = os.environ.get("PIHOLE_HOST",     "localhost")
PIHOLE_PASSWORD = os.environ.get("PIHOLE_PASSWORD",  "")
OUTPUT_FILE     = os.environ.get("SYSMON_OUTPUT",    "/home/ubuntu/homeassistant/config/www/sysmon.json")
# Timezone offset from UTC for the "updated" timestamp display
UTC_OFFSET_HOURS = int(os.environ.get("UTC_OFFSET_HOURS", "-6"))
# ──────────────────────────────────────────────────────────


def get_pihole_stats():
    """Fetch stats from Pi-hole v6 API (requires authentication)."""
    if not HAS_REQUESTS:
        return {}

    base = f"http://{PIHOLE_HOST}/api"
    sid  = None

    try:
        # 1. Authenticate
        r = requests.post(f"{base}/auth", json={"password": PIHOLE_PASSWORD}, timeout=5)
        r.raise_for_status()
        sid = r.json()["session"]["sid"]

        # 2. Fetch summary
        headers = {"sid": sid}
        s = requests.get(f"{base}/stats/summary", headers=headers, timeout=5).json()

        q   = s.get("queries", {})
        g   = s.get("gravity", {})
        cli = s.get("clients",  {})

        return {
            "queries_today":        q.get("total", 0),
            "ads_blocked_today":    q.get("blocked", 0),
            "ads_percentage_today": round(q.get("percent_blocked", 0.0), 2),
            "domains_being_blocked": g.get("domains_being_blocked", 0),
            "queries_forwarded":    q.get("forwarded", 0),
            "queries_cached":       q.get("cached", 0),
            "unique_clients":       cli.get("active", 0),
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        # 3. Always log out
        if sid and HAS_REQUESTS:
            try:
                requests.delete(f"{base}/auth", headers={"sid": sid}, timeout=5)
            except Exception:
                pass


def get_server_stats():
    """Collect local server metrics."""
    stats = {}

    if HAS_PSUTIL:
        stats["cpu_pct"]  = round(psutil.cpu_percent(interval=0.5), 1)
        vm = psutil.virtual_memory()
        stats["mem_pct"]  = round(vm.percent, 1)
        stats["mem_used"] = vm.used
        stats["mem_total"] = vm.total
        du = psutil.disk_usage("/")
        stats["disk_pct"]  = round(du.percent, 1)
        stats["disk_used"] = du.used
        stats["disk_total"] = du.total
        la = psutil.getloadavg()
        stats["load_1"] = round(la[0], 2)
        stats["load_5"] = round(la[1], 2)
        bt = psutil.boot_time()
        up_secs = (datetime.now().timestamp() - bt)
        days    = int(up_secs // 86400)
        hours   = int((up_secs % 86400) // 3600)
        mins    = int((up_secs % 3600) // 60)
        if days > 0:
            stats["uptime_str"] = f"{days}d {hours}h"
        else:
            stats["uptime_str"] = f"{hours}h {mins}m"
    else:
        # Fallback using /proc (Linux only)
        try:
            with open("/proc/loadavg") as f:
                parts = f.read().split()
                stats["load_1"] = float(parts[0])
                stats["load_5"] = float(parts[1])
        except Exception:
            pass
        try:
            with open("/proc/uptime") as f:
                up_secs = float(f.read().split()[0])
            days  = int(up_secs // 86400)
            hours = int((up_secs % 86400) // 3600)
            stats["uptime_str"] = f"{days}d {hours}h"
        except Exception:
            pass

    # CPU temperature (Linux thermal zone)
    try:
        for zone in range(10):
            path = f"/sys/class/thermal/thermal_zone{zone}/temp"
            if os.path.exists(path):
                with open(path) as f:
                    temp = int(f.read().strip()) / 1000.0
                if 10 < temp < 120:
                    stats["temp_c"] = round(temp, 1)
                    break
    except Exception:
        pass

    return stats


def get_docker_containers():
    """List Docker containers and their status."""
    try:
        out = subprocess.check_output(
            ["docker", "ps", "-a", "--format", "{{.Names}}|{{.Status}}"],
            stderr=subprocess.DEVNULL, timeout=10
        ).decode().strip()
        containers = []
        for line in out.splitlines():
            if not line.strip():
                continue
            parts   = line.split("|", 1)
            name    = parts[0].strip()
            status  = parts[1].strip() if len(parts) > 1 else "unknown"
            running = status.lower().startswith("up")
            # Shorten status for display
            if running:
                display = "UP"
            else:
                display = "DOWN"
            containers.append({"name": name, "status": display, "running": running})
        return sorted(containers, key=lambda x: (not x["running"], x["name"]))
    except Exception as e:
        return [{"name": "docker error", "status": str(e), "running": False}]


def main():
    local_now = datetime.now(timezone.utc) + timedelta(hours=UTC_OFFSET_HOURS)
    updated   = local_now.strftime("%-I:%M %p").lower()  # e.g. "3:45 pm"

    data = {
        "updated":    updated,
        "pihole":     get_pihole_stats(),
        "server":     get_server_stats(),
        "containers": get_docker_containers(),
    }

    with open(OUTPUT_FILE, "w") as f:
        json.dump(data, f, indent=2)

    print(f"[sysmon] Updated at {updated}")


if __name__ == "__main__":
    main()
