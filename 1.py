#!/usr/bin/env python3
import subprocess, time, json

INTERVAL = 3

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except:
        return ""

# -------- SYSTEM RAM --------
def ram():
    total = free = 0
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith("MemTotal"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable"):
                free = int(line.split()[1])

    total_mb = total // 1024
    used_mb = total_mb - (free // 1024)
    return used_mb, total_mb


# -------- BATTERY + VOLTAGE + TEMP --------
def battery():
    out = run("termux-battery-status")
    if not out:
        return "N/A", "N/A", "N/A", "N/A"

    try:
        j = json.loads(out)
        percent = j.get("percentage", "N/A")
        temp = j.get("temperature", "N/A")
        status = j.get("status", "N/A")
        voltage = j.get("voltage", "N/A")

        # convert mV → V
        if isinstance(voltage, int):
            voltage = voltage / 1000

        return percent, temp, status, voltage
    except:
        return "N/A", "N/A", "N/A", "N/A"


# -------- TOP RAM PROCESSES --------
def top_ram():
    out = run("ps -A -o NAME,RSS --sort=-RSS | head -n 10")
    procs = []

    for line in out.splitlines()[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 2:
            name = parts[0]
            rss_kb = int(parts[1])
            rss_mb = rss_kb // 1024
            procs.append((name, rss_mb))

    return procs


# -------- MAIN --------
print("=== IIAB RAM + BATTERY MONITOR (Ctrl+C to stop) ===")

try:
    while True:
        used, total = ram()
        bat, temp, status, volt = battery()
        procs = top_ram()

        print("\nRAM  :", used, "/", total, "MB")
        print("Bat  :", bat, "% |", status)
        print("Temp :", temp, "°C")
        print("Volt :", volt, "V")

        print("\nTop RAM processes:")
        for p in procs:
            print(" ", p[0], ":", p[1], "MB")

        print("-" * 40)

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nStopped.")
