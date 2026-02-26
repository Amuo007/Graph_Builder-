#!/usr/bin/env python3
"""
termux_sys_stats.py
Prints a bunch of useful system stats on Android/Termux (no root needed).
Optional: if Termux:API is installed, it will also print battery status.

Run:
  python termux_sys_stats.py
"""

import os
import platform
import shutil
import subprocess
import time
import json
from datetime import datetime

def run(cmd: str) -> str:
    """Run shell command and return stdout (or empty string)."""
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        out = (p.stdout or "").strip()
        return out
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
        # Usually in kB
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
    for name in sorted(os.listdir(cpu_base)) if os.path.isdir(cpu_base) else []:
        if not name.startswith("cpu") or not name[3:].isdigit():
            continue
        cur = read_file(os.path.join(cpu_base, name, "cpufreq", "scaling_cur_freq"))
        if cur.isdigit():
            # scaling_cur_freq is usually in kHz
            mhz = int(cur) / 1000.0
            freqs.append((name, mhz))
    return freqs

def main():
    print("=" * 70)
    print("TERMUX / ANDROID SYSTEM STATS")
    print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 70)

    # Basic OS / arch
    print("\n[OS]")
    print("Kernel:", platform.release())
    print("Machine (uname -m):", platform.machine())
    print("Platform:", platform.platform())

    # Android props (these usually work even when /proc is restricted)
    print("\n[ANDROID PROPERTIES]")
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
    for p in props:
        v = run(f"getprop {p}")
        if v:
            print(f"{p}: {v}")

    # CPU info (may fail in some environments)
    print("\n[CPU]")
    cpuinfo = read_file("/proc/cpuinfo")
    if cpuinfo:
        # Print a small summary (not the whole huge file)
        # Extract a few common fields if present
        lines = cpuinfo.splitlines()
        interesting = []
        keys = ("Hardware", "model name", "Processor", "CPU implementer", "CPU part", "Features")
        for line in lines:
            if any(line.startswith(k) for k in keys):
                interesting.append(line)
        if interesting:
            for line in interesting[:20]:
                print(line)
        else:
            print("(cpuinfo present but no common summary keys found)")
    else:
        print("/proc/cpuinfo not accessible in this environment (common in proot/containers).")

    # CPU online cores
    online = read_file("/sys/devices/system/cpu/online")
    present = read_file("/sys/devices/system/cpu/present")
    if present or online:
        print("CPU present:", present or "(unknown)")
        print("CPU online :", online or "(unknown)")

    # CPU frequencies
    freqs = get_cpu_freqs()
    if freqs:
        print("Current CPU freqs:")
        for cpu, mhz in freqs:
            print(f"  {cpu}: {mhz:.0f} MHz")
    else:
        print("CPU freq: not available (device may restrict cpufreq info).")

    # Load average + uptime (may be restricted -> nan/unknown sometimes)
    print("\n[LOAD / UPTIME]")
    la = read_file("/proc/loadavg")
    if la:
        print("loadavg:", la)
    else:
        print("loadavg: not available")
    up = read_file("/proc/uptime")
    if up:
        try:
            sec = float(up.split()[0])
            print(f"uptime: {sec/3600:.2f} hours")
        except Exception:
            print("uptime(raw):", up)
    else:
        print("uptime: not available")

    # Memory / Swap
    print("\n[MEMORY]")
    mi = parse_meminfo()
    if mi:
        total = mi.get("MemTotal", 0)
        free = mi.get("MemFree", 0)
        avail = mi.get("MemAvailable", 0)
        swap_total = mi.get("SwapTotal", 0)
        swap_free = mi.get("SwapFree", 0)
        print("MemTotal     :", fmt_gb(total))
        print("MemFree      :", fmt_gb(free))
        if avail:
            print("MemAvailable :", fmt_gb(avail))
        if swap_total:
            used = max(0, swap_total - swap_free)
            print("SwapTotal    :", fmt_gb(swap_total))
            print("SwapUsed     :", fmt_gb(used))
            print("SwapFree     :", fmt_gb(swap_free))
    else:
        print("/proc/meminfo not accessible")

    # Storage (Termux home + internal storage if present)
    print("\n[STORAGE]")
    paths = [
        ("Termux home", os.path.expanduser("~")),
        ("Internal shared", "/storage/emulated/0"),
    ]
    for label, path in paths:
        if os.path.exists(path):
            try:
                du = shutil.disk_usage(path)
                print(f"{label} ({path})")
                print(f"  Total: {du.total/1e9:.1f} GB  Used: {du.used/1e9:.1f} GB  Free: {du.free/1e9:.1f} GB")
            except Exception:
                print(f"{label}: cannot read disk usage")
        else:
            print(f"{label}: {path} not found (permission needed? try `termux-setup-storage`).")

    # Battery via Termux:API (optional)
    print("\n[BATTERY] (optional)")
    batt = run("termux-battery-status")
    if batt:
        try:
            jb = json.loads(batt)
            for k in ["percentage", "status", "plugged", "health", "temperature", "current", "voltage"]:
                if k in jb:
                    print(f"{k}: {jb[k]}")
        except Exception:
            print(batt)
    else:
        print("termux-battery-status not available.")
        print("Fix: install Termux:API app (from F-Droid) + run `pkg install termux-api`.")

    # Top processes (best effort)
    print("\n[TOP PROCESSES]")
    # Busybox/toybox 'ps' differs; try a few variants.
    ps_cmds = [
        "ps -A -o PID,NAME,CPU%,RSS --sort=-CPU% | head -n 15",
        "ps -eo pid,comm,%cpu,rss --sort=-%cpu | head -n 15",
        "top -b -n 1 | head -n 25",
    ]
    shown = False
    for c in ps_cmds:
        out = run(c)
        if out:
            print(f"$ {c}")
            print(out)
            shown = True
            break
    if not shown:
        print("Could not list processes (ps/top output restricted on this device).")

    print("\nDone.")
    print("=" * 70)

if __name__ == "__main__":
    main()
