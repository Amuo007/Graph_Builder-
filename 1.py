#!/usr/bin/env python3
import time, os, json, subprocess

def sh(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, text=True).strip()
    except Exception:
        return ""

def get_ram_mb():
    try:
        mem = {}
        with open("/proc/meminfo") as f:
            for line in f:
                if ":" in line:
                    k, rest = line.split(":", 1)
                    v = rest.strip().split()
                    if v and v[0].isdigit():
                        mem[k] = int(v[0])  # kB
        total = mem.get("MemTotal", 0)
        avail = mem.get("MemAvailable", 0)
        used = max(0, total - avail)
        return used // 1024, total // 1024
    except Exception:
        return 0, 0

# CPU% without doing an extra sleep inside (keeps previous sample)
_prev_idle = None
_prev_total = None
def get_cpu_percent():
    global _prev_idle, _prev_total
    try:
        parts = open("/proc/stat").readline().split()[1:]
        nums = list(map(int, parts))
        idle = nums[3] + nums[4]  # idle + iowait
        total = sum(nums)
        if _prev_idle is None:
            _prev_idle, _prev_total = idle, total
            return "N/A"  # first sample has no delta yet
        didle = idle - _prev_idle
        dtotal = total - _prev_total
        _prev_idle, _prev_total = idle, total
        if dtotal <= 0:
            return "N/A"
        return round(100.0 * (1.0 - (didle / dtotal)), 1)
    except Exception:
        return "N/A"

def get_battery():
    # 1) Termux:API (best)
    out = sh("termux-battery-status")
    if out.startswith("{"):
        try:
            j = json.loads(out)
            # temperature is °C in termux-battery-status
            return {
                "capacity": str(j.get("percentage", "N/A")),
                "status": str(j.get("status", "N/A")),
                "voltage": str(j.get("voltage", "N/A")),
                "temp_c": str(j.get("temperature", "N/A")),
                "source": "termux-battery-status",
            }
        except Exception:
            pass

    # 2) dumpsys battery (usually works even without Termux:API app)
    ds = sh("dumpsys battery")
    if ds:
        # very simple parse
        def grab(key):
            for line in ds.splitlines():
                line = line.strip()
                if line.lower().startswith(key.lower() + ":"):
                    return line.split(":",1)[1].strip()
            return "N/A"
        temp = grab("temperature")  # often in tenths of °C
        temp_c = "N/A"
        if temp.isdigit():
            temp_c = f"{int(temp)/10:.1f}"
        return {
            "capacity": grab("level"),
            "status": grab("status"),
            "voltage": grab("voltage"),
            "temp_c": temp_c,
            "source": "dumpsys battery",
        }

    # 3) sysfs fallback (some devices allow it)
    for base in ("/sys/class/power_supply/battery", "/sys/class/power_supply/BAT0", "/sys/class/power_supply/BAT1"):
        if os.path.exists(base):
            def rf(p):
                try: return open(p).read().strip()
                except: return ""
            cap = rf(f"{base}/capacity") or "N/A"
            stat = rf(f"{base}/status") or "N/A"
            vraw = rf(f"{base}/voltage_now")
            traw = rf(f"{base}/temp")
            volt = f"{int(vraw)/1_000_000:.3f}" if vraw.isdigit() else "N/A"
            temp_c = f"{int(traw)/10:.1f}" if traw.isdigit() else "N/A"
            return {"capacity": cap, "status": stat, "voltage": volt, "temp_c": temp_c, "source": base}

    return {"capacity":"N/A","status":"N/A","voltage":"N/A","temp_c":"N/A","source":"none"}

prev_used = None
print("=== IIAB Android Monitor (Ctrl+C to stop) ===\n")

while True:
    used, total = get_ram_mb()
    cpu = get_cpu_percent()
    bat = get_battery()

    delta = ""
    if prev_used is not None:
        d = used - prev_used
        delta = f" ({'+' if d >= 0 else ''}{d} MB)"
    prev_used = used

    icon = {"Charging":"⬆","Discharging":"⬇","Full":"✓"}.get(bat["status"], "?")

    print(f"[{time.strftime('%H:%M:%S')}]")
    print(f"  RAM  : {used} / {total} MB{delta}")
    print(f"  CPU  : {cpu}%")
    print(f"  Bat  : {bat['capacity']}% | {bat['voltage']} {icon} {bat['status']}  [{bat['source']}]")
    print(f"  Temp : {bat['temp_c']} °C")
    print("-" * 35)
    time.sleep(3)
