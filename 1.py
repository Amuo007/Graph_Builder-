#!/usr/bin/env python3
import time, subprocess, datetime, json

LOG_FILE = "baseline_metrics.txt"

def sh(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True, stderr=subprocess.DEVNULL).strip()

def get_cpu_percent():
    # Try to extract overall CPU usage from top output
    out = sh("top -b -n 1 | head -n 5")
    # Common formats vary; just return the header block so you always log something useful
    return out

def get_mem_info():
    # Works reliably on Termux
    return sh("free -h")

def get_battery():
    try:
        return sh("termux-battery-status")
    except:
        return "Battery info not available (install termux-api + Termux:API app)"

def get_thermal():
    try:
        # millidegree C -> C
        temps = sh("cat /sys/class/thermal/thermal_zone*/temp").splitlines()
        temps_c = [f"{int(t)/1000:.1f}C" for t in temps if t.isdigit()]
        return temps_c if temps_c else temps
    except:
        return ["Thermal not available"]

with open(LOG_FILE, "a") as f:
    f.write("\n===== Monitoring Started =====\n")

while True:
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cpu_block = get_cpu_percent()
    mem_block = get_mem_info()
    battery = get_battery()
    temps = get_thermal()

    log = f"""
Time: {now}

[CPU(top)]
{cpu_block}

[RAM(free)]
{mem_block}

[Battery]
{battery}

[Thermal]
{temps}
----------------------------------------
"""
    print(log)
    with open(LOG_FILE, "a") as f:
        f.write(log)

    time.sleep(1)
