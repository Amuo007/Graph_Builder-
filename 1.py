#!/usr/bin/env python3
import os, subprocess, time
from datetime import datetime

INTERVAL = 3   # safer than 2 on Android

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True, timeout=1)
    except:
        return ""

def cpu_freqs():
    freqs = []
    base = "/sys/devices/system/cpu"
    try:
        for c in os.listdir(base):
            if c.startswith("cpu") and c[3:].isdigit():
                f = run(f"cat {base}/{c}/cpufreq/scaling_cur_freq")
                if f.strip().isdigit():
                    freqs.append(int(f)//1000)
    except:
        pass
    return freqs

def services():
    out = run("ps -eo comm,%cpu --sort=-%cpu")
    data = {"kolibri":0,"nginx":0,"mariadbd":0}
    for line in out.splitlines():
        for k in data:
            if k in line:
                try:
                    data[k] = float(line.split()[-1])
                except:
                    pass
    return data

def mem():
    total = avail = 0
    with open("/proc/meminfo") as f:
        for line in f:
            if "MemTotal" in line:
                total = int(line.split()[1])//1024
            if "MemAvailable" in line:
                avail = int(line.split()[1])//1024
    return total, avail

print("Monitoring IIAB (Ctrl+C to stop)\n")

try:
    while True:
        t = datetime.now().strftime("%H:%M:%S")
        total, avail = mem()

        print("------------------------------------------------")
        print("Time:", t)
        print("CPU MHz:", cpu_freqs())
        print("Services:", services())
        print(f"Memory: {avail}MB free / {total}MB total")
        print("------------------------------------------------\n")

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("\nStopped.")
