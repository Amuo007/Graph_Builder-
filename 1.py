#!/usr/bin/env python3
import os, subprocess, json, time
from datetime import datetime

INTERVAL = 2
LOG_FILE = "iiab_perf.jsonl"

def run(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True)
    except:
        return ""

def cpu_freqs():
    freqs = []
    base = "/sys/devices/system/cpu"
    for c in sorted(os.listdir(base)):
        if c.startswith("cpu") and c[3:].isdigit():
            f = run(f"cat {base}/{c}/cpufreq/scaling_cur_freq")
            if f.strip().isdigit():
                freqs.append(int(f.strip()) // 1000)
    return freqs

def top_services():
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
    m = {}
    with open("/proc/meminfo") as f:
        for line in f:
            if line.startswith(("MemTotal","MemAvailable")):
                k,v = line.split(":")
                m[k] = int(v.split()[0])
    return m

print("Logging to", LOG_FILE, "every", INTERVAL, "seconds")

try:
    while True:
        rec = {
            "time": datetime.now().isoformat(),
            "cpu_freq_mhz": cpu_freqs(),
            "services": top_services(),
            "mem_kb": mem()
        }

        with open(LOG_FILE,"a") as f:
            f.write(json.dumps(rec)+"\n")

        time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("Stopped.")
