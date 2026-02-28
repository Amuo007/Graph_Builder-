#!/usr/bin/env python3
"""
termux_sys_stats.py
Same output as before, but:
- Appends output to a log file (TXT)
- Runs continuously until you exit (Ctrl+C)
- Adds a timestamp header for each snapshot

Run:
  python termux_sys_stats.py
Stop:
  Ctrl + C
"""

import os
import platform
import shutil
import subprocess
import json
import time
from datetime import datetime


LOG_FILE = "termux_sys_stats_log.txt"
INTERVAL_SECONDS = 5  # change to 1, 2, 10, etc.


def run(cmd: str) -> str:
    """Run shell command and return stdout (or empty string)."""
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        return (p.stdout or "").strip()
    except Exception:
        return ""


def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""


def parse_meminfo() -> dict:
    data = {}
    txt = read_file("/proc/meminfo")
    for line in txt.splitlines():
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip().split()
        if v and v[0].isdigit():
            data[k] = int(v[0])  # kB
    return data


def kb_to_gb(kb: int) -> float:
    return kb / (1024 * 1024)


def fmt_gb(kb: int) -> str:
    return f"{kb_to_gb(kb):.2f} GB"


def get_cpu_freqs() -> list:
    freqs = []
    cpu_base = "/sys/devices/system/cpu"
    if not os.path.isdir(cpu_base):
        return freqs

    for name in sorted(os.listdir(cpu_base)):
        if not name.startswith("cpu") or not name[3:].isdigit():
            continue
        cur = read_file(os.path.join(cpu_base, name, "cpufreq", "scaling_cur_freq"))
        if cur.isdigit():
            mhz = int(cur) / 1000.0  # kHz -> MHz
            freqs.append((name, mhz))
    return freqs


def parse_thermal_zones() -> list:
    """
    Returns list of (zone_name, temp_c, raw_path).
    temp is commonly in millidegree C. We normalize to °C.
    """
    zones = []
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return zones

    for z in sorted(os.listdir(base)):
        if not z.startswith("thermal_zone"):
            continue
        zpath = os.path.join(base, z)
        t_type = read_file(os.path.join(zpath, "type")) or z
        t_raw = read_file(os.path.join(zpath, "temp"))
        if not t_raw:
            continue

        try:
            val = float(t_raw)
            temp_c = val / 1000.0 if val > 1000 else val
            zones.append((t_type.strip(), temp_c, os.path.join(zpath, "temp")))
        except Exception:
            continue

    return zones


def pick_interesting_temps(zones: list) -> list:
    if not zones:
        return []

    keywords = [
        "cpu", "soc", "ap", "big", "little", "cluster", "gpu",
        "tsens", "qcom", "pmic", "skin", "battery"
    ]

    def score(name: str) -> int:
        n = name.lower()
        return sum(1 for k in keywords if k in n)

    zones_sorted = sorted(zones, key=lambda x: (score(x[0]), x[1]), reverse=True)
    preferred = [z for z in zones_sorted if score(z[0]) > 0]
    return preferred[:8] if preferred else zones_sorted[:8]


def build_report() -> str:
    lines = []
    lines.append("=" * 70)
    lines.append("TERMUX / ANDROID SYSTEM STATS")
    lines.append("Time: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 70)

    # OS / arch
    lines.append("\n[OS]")
    lines.append(f"Kernel: {platform.release()}")
    lines.append(f"Machine (uname -m): {platform.machine()}")
    lines.append(f"Platform: {platform.platform()}")

    # Android props
    lines.append("\n[ANDROID PROPERTIES]")
    props = [
        "ro.product.model",
        "ro.product.manufacturer",
        "ro.build.version.release",
        "ro.build.version.sdk",
        "ro.product.cpu.abi",
        "ro.product.cpu.abilist",
        "ro.soc.manufacturer",
        "ro.soc.model",
        "ro.hardware",
        "ro.boot.hardware",
    ]
    any_prop = False
    for p in props:
        v = run(f"getprop {p}")
        if v:
            any_prop = True
            lines.append(f"{p}: {v}")
    if not any_prop:
        lines.append("(no getprop output — common inside proot-distro containers)")

    # CPU info
    lines.append("\n[CPU]")
    cpuinfo = read_file("/proc/cpuinfo")
    if cpuinfo:
        interesting = []
        keys = ("Hardware", "model name", "Processor", "CPU implementer", "CPU part", "Features")
        for line in cpuinfo.splitlines():
            if any(line.startswith(k) for k in keys):
                interesting.append(line)
        if interesting:
            lines.extend(interesting[:20])
        else:
            lines.append("(cpuinfo present but no common summary keys found)")
    else:
        lines.append("/proc/cpuinfo not accessible in this environment (common in some containers).")

    # CPU online cores
    online = read_file("/sys/devices/system/cpu/online")
    present = read_file("/sys/devices/system/cpu/present")
    if present or online:
        lines.append(f"CPU present: {present or '(unknown)'}")
        lines.append(f"CPU online : {online or '(unknown)'}")

    # CPU frequencies
    freqs = get_cpu_freqs()
    if freqs:
        lines.append("Current CPU freqs:")
        for cpu, mhz in freqs:
            lines.append(f"  {cpu}: {mhz:.0f} MHz")
    else:
        lines.append("CPU freq: not available (device may restrict cpufreq info).")

    # Temperatures
    lines.append("\n[TEMPERATURES]")
    zones = parse_thermal_zones()
    if zones:
        chosen = pick_interesting_temps(zones)
        for name, temp_c, path in chosen:
            lines.append(f"{name}: {temp_c:.1f} °C  ({path})")
        max_zone = max(zones, key=lambda x: x[1])
        lines.append(f"Max thermal zone: {max_zone[0]} = {max_zone[1]:.1f} °C")
    else:
        lines.append("No thermal zones readable (Samsung/Android may restrict /sys/class/thermal).")
        lines.append("Fallback: use battery temp via termux-battery-status (below).")

    # Load average + uptime
    lines.append("\n[LOAD / UPTIME]")
    la = read_file("/proc/loadavg")
    lines.append("loadavg: " + (la if la else "not available"))
    up = read_file("/proc/uptime")
    if up:
        try:
            sec = float(up.split()[0])
            lines.append(f"uptime: {sec/3600:.2f} hours")
        except Exception:
            lines.append("uptime(raw): " + up)
    else:
        lines.append("uptime: not available")

    # Memory / Swap
    lines.append("\n[MEMORY]")
    mi = parse_meminfo()
    if mi:
        total = mi.get("MemTotal", 0)
        free = mi.get("MemFree", 0)
        avail = mi.get("MemAvailable", 0)
        swap_total = mi.get("SwapTotal", 0)
        swap_free = mi.get("SwapFree", 0)
        lines.append("MemTotal     : " + fmt_gb(total))
        lines.append("MemFree      : " + fmt_gb(free))
        if avail:
            lines.append("MemAvailable : " + fmt_gb(avail))
        if swap_total:
            used = max(0, swap_total - swap_free)
            lines.append("SwapTotal    : " + fmt_gb(swap_total))
            lines.append("SwapUsed     : " + fmt_gb(used))
            lines.append("SwapFree     : " + fmt_gb(swap_free))
    else:
        lines.append("/proc/meminfo not accessible")

    # Storage
    lines.append("\n[STORAGE]")
    paths = [
        ("Termux home", os.path.expanduser("~")),
        ("Internal shared", "/storage/emulated/0"),
    ]
    for label, path in paths:
        if os.path.exists(path):
            try:
                du = shutil.disk_usage(path)
                lines.append(f"{label} ({path})")
                lines.append(f"  Total: {du.total/1e9:.1f} GB  Used: {du.used/1e9:.1f} GB  Free: {du.free/1e9:.1f} GB")
            except Exception:
                lines.append(f"{label}: cannot read disk usage")
        else:
            lines.append(f"{label}: {path} not found (permission needed? try `termux-setup-storage`).")

    # Battery (optional)
    lines.append("\n[BATTERY] (optional)")
    batt = run("termux-battery-status")
    if batt:
        try:
            jb = json.loads(batt)
            for k in ["percentage", "status", "plugged", "health", "temperature", "current", "voltage"]:
                if k in jb:
                    lines.append(f"{k}: {jb[k]}")
        except Exception:
            lines.append(batt)
    else:
        lines.append("termux-battery-status not available.")
        lines.append("Fix: install Termux:API app (from F-Droid) + run `pkg install termux-api`.")

    # Top processes
    lines.append("\n[TOP PROCESSES]")
    ps_cmds = [
        "ps -A -o PID,NAME,CPU%,RSS --sort=-CPU% | head -n 15",
        "ps -eo pid,comm,%cpu,rss --sort=-%cpu | head -n 15",
        "top -b -n 1 | head -n 25",
    ]
    for c in ps_cmds:
        out = run(c)
        if out:
            lines.append(f"$ {c}")
            lines.append(out)
            break
    else:
        lines.append("Could not list processes (ps/top output restricted on this device).")

    lines.append("\nDone.")
    lines.append("=" * 70)
    return "\n".join(lines) + "\n"


def main():
    print(f"Logging to: {os.path.abspath(LOG_FILE)}")
    print(f"Interval: {INTERVAL_SECONDS}s  (Stop with Ctrl+C)\n")

    try:
        while True:
            report = build_report()

            # Print to screen
            print(report)

            # Append to txt file
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(report)

            time.sleep(INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped. Log saved to:", os.path.abspath(LOG_FILE))


if __name__ == "__main__":
    main()
