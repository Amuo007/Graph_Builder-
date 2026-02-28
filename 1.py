#!/usr/bin/env python3
import os, subprocess, json, time
from datetime import datetime

INTERVAL = 8          # slower → less stress
LOG_FILE = "iiab_perf.jsonl"

def run(cmd):
    try:
        return subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=1
        ).stdout
    except:
        return ""

# safer CPU freq (no cat spam)
def cpu_freqs():
    freqs = []
    base = "/sys/devices/system/cpu"
    try:
        for c in os.listdir(base):
            if c.startswith("cpu") and c[3:].isdigit():
                path = f"{base}/{c}/cpufreq/scaling_cur_freq"
                if os.path.exists(path):
                    with open(path) as f:
                        v = f.read().strip()
                        if v.isdigit():
                            freqs.append(int(v)//1000)
    except:
        pass
    return freqs

# lighter top services (single scan)
def top_services():
    data = {"kolibri":0,"nginx":0,"mariadbd":0}
    try:
        out = subprocess.run(
            ["ps","-eo","comm,%cpu"],
            capture_output=True, text=True, timeout=1
        ).stdout

        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 2:
                name, cpu = parts
                if name in data:
                    data[name] = float(cpu)
    except:
        pass
    return data

def mem():
    m = {}
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith(("MemTotal","MemAvailable")):
                    k,v = line.split(":")
                    m[k] = int(v.split()[0])
    except:
        pass
    return m

print("Logging every", INTERVAL, "sec →", LOG_FILE)

try:
    with open(LOG_FILE, "a", buffering=1) as f:   # line buffered
        while True:
            rec = {
                "time": datetime.now().isoformat(),
                "cpu_freq_mhz": cpu_freqs(),
                "services": top_services(),
                "mem_kb": mem()
            }
            f.write(json.dumps(rec) + "\n")
            time.sleep(INTERVAL)

except KeyboardInterrupt:
    print("Stopped.")
