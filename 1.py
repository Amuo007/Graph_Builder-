#!/usr/bin/env python3
import os
import time
import json
import subprocess


# ---------- run shell ----------
def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except:
        return ""


# ---------- RAM ----------
def ram():
    mem = run("free -m")
    for line in mem.splitlines():
        if "Mem:" in line:
            p = line.split()
            return int(p[2]), int(p[1])
    return 0, 0


# ---------- Battery ----------
def battery():
    try:
        out = run("termux-battery-status")
        if not out:
            return "N/A", "N/A", "N/A", "N/A"

        j = json.loads(out)

        pct = j.get("percentage", "N/A")
        status = j.get("status", "N/A")
        temp = j.get("temperature", "N/A")
        volt = j.get("voltage", "N/A")

        if volt != "N/A":
            volt = round(volt / 1000, 3)

        return pct, status, temp, volt
    except:
        return "N/A", "N/A", "N/A", "N/A"


# ---------- Top RAM ----------
def top_ram(n=8):
    # Termux compatible
    out = run(f"ps -eo pid,comm,rss --sort=-rss | head -n {n+1}")
    rows = []

    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 3 and parts[0].isdigit() and parts[2].isdigit():
            pid = int(parts[0])
            comm = parts[1]
            rss = int(parts[2]) // 1024
            rows.append((comm, pid, rss))

    return rows


# ---------- Service RAM ----------
def service_ram():
    wanted = {"kolibri", "nginx", "mariadbd", "mysqld", "php-fpm", "node", "python"}

    out = run("ps -eo comm,rss")
    totals = {}

    for line in out.splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[-1].isdigit():
            name = parts[0]
            rss = int(parts[-1])

            if name in wanted:
                totals[name] = totals.get(name, 0) + rss

    return {k: round(v / 1024, 1) for k, v in sorted(totals.items(), key=lambda x: -x[1])}


# ---------- Main ----------
print("=== IIAB RAM + BATTERY MONITOR (Ctrl+C to stop) ===")

while True:
    used, total = ram()
    pct, status, temp, volt = battery()

    print()
    print(f"RAM  : {used} / {total} MB")
    print(f"Bat  : {pct}% | {status}")
    print(f"Temp : {temp} °C")
    print(f"Volt : {volt} V")

    print("\nSrv RAM (MB):", service_ram())

    print("\nTop RAM processes:")
    for name, pid, mb in top_ram(8):
        print(f"  {name:12s} {mb:4d} MB  (pid {pid})")

    print("----------------------------------------")

    time.sleep(3)
