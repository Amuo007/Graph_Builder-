#!/usr/bin/env python3
import time, psutil, subprocess, datetime

LOG_FILE = "baseline_metrics.txt"

def get_battery():
    try:
        out = subprocess.check_output(["termux-battery-status"]).decode()
        return out.strip()
    except:
        return "Battery info not available"

def get_thermal():
    temps = []
    try:
        out = subprocess.check_output(
            "cat /sys/class/thermal/thermal_zone*/temp",
            shell=True
        ).decode().splitlines()
        temps = [str(int(x)/1000) + "°C" for x in out]
    except:
        temps = ["Thermal not available"]
    return temps

with open(LOG_FILE, "a") as f:
    f.write("\n===== Monitoring Started =====\n")

while True:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # CPU + RAM
    cpu = psutil.cpu_percent(interval=1)
    mem = psutil.virtual_memory()

    # Battery + voltage
    battery = get_battery()

    # Thermal sensors
    temps = get_thermal()

    log = f"""
Time: {now}

[CPU]
Usage: {cpu} %

[RAM]
Used: {mem.used/1e9:.2f} GB
Available: {mem.available/1e9:.2f} GB
Percent: {mem.percent} %

[Battery]
{battery}

[Thermal]
Sensors: {temps}
----------------------------------------
"""

    print(log)
    with open(LOG_FILE, "a") as f:
        f.write(log)

    time.sleep(1)
