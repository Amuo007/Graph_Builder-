import subprocess
import time
import json
import signal
import sys

session = []

def adb(cmd):
    result = subprocess.run(["adb", "shell"] + cmd.split(), capture_output=True, text=True)
    return result.stdout.strip()

def get_cpu():
    def read_stat():
        out = adb("cat /proc/stat")
        line = out.splitlines()[0].split()
        values = list(map(int, line[1:]))
        return values[3], sum(values)
    idle1, total1 = read_stat()
    time.sleep(0.5)
    idle2, total2 = read_stat()
    diff = total2 - total1
    if diff == 0:
        return 0.0
    return round(100.0 * (1 - (idle2 - idle1) / diff), 1)

def get_loadavg():
    out = adb("cat /proc/loadavg")
    parts = out.split()
    return {"1min": float(parts[0]), "5min": float(parts[1]), "15min": float(parts[2])}

def get_ram():
    out = adb("cat /proc/meminfo")
    mem = {}
    for line in out.splitlines():
        parts = line.split()
        if parts[0] in ("MemTotal:", "MemAvailable:"):
            mem[parts[0]] = int(parts[1])
    total = mem.get("MemTotal:", 0) // 1024
    available = mem.get("MemAvailable:", 0) // 1024
    return {"used_mb": total - available, "total_mb": total}

def get_battery():
    out = adb("dumpsys battery")
    result = {}
    for line in out.splitlines():
        line = line.strip()
        if "level:" in line:
            result["percent"] = int(line.split(":")[1].strip())
        elif "temperature:" in line:
            result["temp_c"] = round(int(line.split(":")[1].strip()) / 10, 1)
        elif "voltage:" in line:
            result["volt_v"] = round(int(line.split(":")[1].strip()) / 1000, 3)
        elif "status:" in line:
            code = line.split(":")[1].strip()
            result["status"] = "CHARGING" if code == "2" else "DISCHARGING" if code == "3" else code
        elif "current now" in line.lower():
            try:
                result["current_ua"] = int(line.split(":")[1].strip())
            except:
                pass
    return result

def get_top_processes(n=8):
    out = adb("top -b -n 1 -o PID,USER,%CPU,%MEM,RES,ARGS")
    procs = []
    for line in out.splitlines():
        line = line.strip()
        parts = line.split()
        if len(parts) < 6:
            continue
        try:
            pid = int(parts[0])
            cpu = float(parts[2])
            mem_pct = float(parts[3])
            res = parts[4]
            name = parts[5].split("/")[-1]

            if "[" in name or name == "top" or name == "sh":
                continue

            if res.endswith("M"):
                ram_mb = float(res[:-1])
            elif res.endswith("G"):
                ram_mb = round(float(res[:-1]) * 1024, 1)
            elif res.endswith("K"):
                ram_mb = round(float(res[:-1]) / 1024, 1)
            else:
                ram_mb = round(int(res) / 1024, 1)

            if cpu == 0.0 and ram_mb < 1:
                continue

            procs.append({
                "pid": pid,
                "name": name,
                "cpu_pct": cpu,
                "ram_mb": ram_mb,
                "mem_pct": mem_pct
            })
        except:
            continue

    procs.sort(key=lambda x: x["cpu_pct"], reverse=True)
    return procs[:n]

def handle_exit(sig, frame):
    duration = session[-1]["timestamp_s"] if session else 0
    drop = session[0]["battery"]["percent"] - session[-1]["battery"]["percent"] if len(session) > 1 else 0

    print("\n\n--- SESSION SUMMARY ---")
    print(f"Duration:      {duration}s")
    print(f"Battery drop:  {drop}%")
    print(f"Avg CPU:       {round(sum(r['cpu_percent'] for r in session) / len(session), 1)}%")
    print(f"Avg RAM:       {round(sum(r['ram']['used_mb'] for r in session) / len(session))} MB")
    print(f"Avg Batt Temp: {round(sum(r['battery'].get('temp_c', 0) for r in session) / len(session), 1)} C")

    with open("session.json", "w") as f:
        json.dump(session, f, indent=2)
    print("\nSaved to session.json")
    sys.exit(0)

signal.signal(signal.SIGINT, handle_exit)

print("Monitor started | Ctrl+C to stop & save to session.json\n")
print(f"{'Time':>6} {'CPU%':>6} {'RAM MB':>8} {'Batt%':>6} {'Volt V':>7} {'Temp C':>7} {'Load 1m':>8}")
print("-" * 60)

tick = 0
start = time.time()

while True:
    timestamp = round(time.time() - start)
    cpu   = get_cpu()
    ram   = get_ram()
    batt  = get_battery()
    load  = get_loadavg()
    procs = get_top_processes()

    record = {
        "tick":          tick,
        "timestamp_s":   timestamp,
        "cpu_percent":   cpu,
        "load_avg":      load,
        "ram":           ram,
        "battery":       batt,
        "top_processes": procs
    }
    session.append(record)

    print(f"{timestamp:>6} {cpu:>6.1f} {ram['used_mb']:>8} "
          f"{batt.get('percent','?'):>6} {batt.get('volt_v','?'):>7} "
          f"{batt.get('temp_c','N/A'):>7} {load['1min']:>8}")

    tick += 1
    time.sleep(2.5)
