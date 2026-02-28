#!/usr/bin/env python3
import time
import os

def read_file(path, default="N/A"):
    try:
        with open(path) as f:
            return f.read().strip()
    except:
        return default

def get_ram():
    try:
        with open("/proc/meminfo") as f:
            lines = {l.split(":")[0]: int(l.split()[1]) for l in f if ":" in l}
        total = lines.get("MemTotal", 0)
        available = lines.get("MemAvailable", 0)
        used = total - available
        return used // 1024, total // 1024  # MB
    except:
        return 0, 0

def get_cpu():
    try:
        def read_stat():
            with open("/proc/stat") as f:
                parts = f.readline().split()
            idle = int(parts[4])
            total = sum(int(x) for x in parts[1:])
            return idle, total

        idle1, total1 = read_stat()
        time.sleep(0.5)
        idle2, total2 = read_stat()
        usage = 100 * (1 - (idle2 - idle1) / (total2 - total1))
        return round(usage, 1)
    except:
        return "N/A"

def get_battery():
    # Common sysfs paths — may vary by device
    bases = [
        "/sys/class/power_supply/battery",
        "/sys/class/power_supply/BAT0",
        "/sys/class/power_supply/BAT1",
    ]
    
    base = next((b for b in bases if os.path.exists(b)), None)
    if not base:
        return {"voltage": "N/A", "temp": "N/A", "status": "N/A", "capacity": "N/A"}

    voltage_raw = read_file(f"{base}/voltage_now")
    temp_raw    = read_file(f"{base}/temp")
    status      = read_file(f"{base}/status")
    capacity    = read_file(f"{base}/capacity")

    voltage = f"{int(voltage_raw) / 1_000_000:.3f}V" if voltage_raw.isdigit() else "N/A"
    temp    = f"{int(temp_raw) / 10:.1f}°C"           if temp_raw.isdigit()    else "N/A"

    return {"voltage": voltage, "temp": temp, "status": status, "capacity": capacity}

prev_ram_used = None

print("=== IIAB Android Monitor (Ctrl+C to stop) ===\n")

while True:
    ram_used, ram_total = get_ram()
    cpu = get_cpu()
    bat = get_battery()

    # Track RAM delta
    ram_delta = ""
    if prev_ram_used is not None:
        diff = ram_used - prev_ram_used
        ram_delta = f"  ({'+' if diff >= 0 else ''}{diff} MB)"
    prev_ram_used = ram_used

    # Battery trend
    status_icon = {"Charging": "⬆", "Discharging": "⬇", "Full": "✓"}.get(bat["status"], "?")

    print(f"[{time.strftime('%H:%M:%S')}]")
    print(f"  RAM  : {ram_used} / {ram_total} MB{ram_delta}")
    print(f"  CPU  : {cpu}%")
    print(f"  Bat  : {bat['capacity']}% | {bat['voltage']} {status_icon} {bat['status']}")
    print(f"  Temp : {bat['temp']}")
    print("-" * 35)

    time.sleep(3)
