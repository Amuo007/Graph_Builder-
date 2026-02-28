#!/usr/bin/env python3
import subprocess, time

INTERVAL = 3

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except:
        return ""

# -------- RAM --------
def ram():
    total = free = 0
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable"):
                free = int(line.split()[1])
    return total // 1024, free // 1024


# -------- CPU (Android safe using top) --------
def cpu_percent():
    out = run("top -bn1 | grep -m1 -E 'CPU|Cpu|cpu'")
    if not out:
        return "N/A"

    try:
        # works for most Android formats
        parts = out.replace(",", " ").split()
        for i, p in enumerate(parts):
            if "%" in p:
                return p
    except:
        pass

    return "N/A"


# -------- SERVICES --------
def services():
    out = run("ps -eo comm=,%cpu= --sort=-%cpu")
    data = {"kolibri": 0.0, "nginx": 0.0, "mariadbd": 0.0}

    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 2:
            continue

        name = parts[0]
        try:
            cpu = float(parts[1])
        except:
            continue

        for k in data:
            if k in name:
                data[k] = cpu

    return data


# -------- BATTERY + TEMP --------
def battery():
    out = run("termux-battery-status")
    if not out:
        return "N/A", "N/A", "N/A"

    try:
        import json
        j = json.loads(out)
        return j["percentage"], j["temperature"], j["status"]
    except:
        return "N/A", "N/A", "N/A"


# -------- MAIN LOOP --------
print("=== IIAB SIMPLE MONITOR (Ctrl+C to stop) ===")

try:
    while True:
        total, free = ram()
        used = total - free

        cpu = cpu_percent()
        bat, temp, status = battery()
        s = services()

        print(f"\nRAM  : {used} / {total} MB")
        print(f"CPU  : {cpu}")
        print(f"Bat  : {bat}% | {status}")
        print(f"Temp : {temp} °C")
        print("Srv  :", s)
        print("-" * 40)

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nStopped.")
