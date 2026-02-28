#!/usr/bin/env python3
import subprocess, time
from datetime import datetime

INTERVAL = 3

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except:
        return ""

def ram():
    total = avail = 0
    with open("/proc/meminfo") as f:
        for line in f:
            if "MemTotal" in line:
                total = int(line.split()[1])
            if "MemAvailable" in line:
                avail = int(line.split()[1])
    used = (total - avail) // 1024
    total = total // 1024
    return used, total

def services():
    out = run("ps -eo comm,%cpu,rss")
    data = {
        "kolibri": (0,0),
        "nginx": (0,0),
        "mariadbd": (0,0)
    }

    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue

        name = parts[0]
        cpu = float(parts[1])
        mem = int(parts[2]) // 1024

        for k in data:
            if k in name:
                data[k] = (cpu, mem)

    return data

print("=== IIAB SIMPLE MONITOR (Ctrl+C to stop) ===")

try:
    while True:
        t = datetime.now().strftime("%H:%M:%S")

        used, total = ram()
        s = services()

        print("\n[", t, "]", sep="")
        print(f"RAM: {used} / {total} MB")

        for k in s:
            cpu, mem = s[k]
            print(f"{k:8} CPU: {cpu:5.1f}%   RAM: {mem} MB")

        print("-" * 40)

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nStopped.")
