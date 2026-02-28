#!/usr/bin/env python3
import os, glob, json, subprocess, re

def sh(cmd):
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        return (p.stdout or "").strip()
    except Exception:
        return ""

def read(path):
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

def norm_temp(val_str):
    try:
        v = float(val_str.strip())
        # many kernels report millidegree C
        return v / 1000.0 if v > 1000 else v
    except Exception:
        return None

def add(out, label, c, source):
    if c is None:
        return
    out.append((label, c, source))

def scan_thermal_zones_sysclass(out):
    base = "/sys/class/thermal"
    if not os.path.isdir(base):
        return
    try:
        zones = sorted(glob.glob(os.path.join(base, "thermal_zone*")))
    except Exception:
        return
    for z in zones:
        ttype = read(os.path.join(z, "type")) or os.path.basename(z)
        tval  = read(os.path.join(z, "temp"))
        c = norm_temp(tval) if tval else None
        add(out, ttype, c, os.path.join(z, "temp"))

def scan_thermal_zones_virtual(out):
    base = "/sys/devices/virtual/thermal"
    if not os.path.isdir(base):
        return
    for z in sorted(glob.glob(os.path.join(base, "thermal_zone*"))):
        ttype = read(os.path.join(z, "type")) or os.path.basename(z)
        tval  = read(os.path.join(z, "temp"))
        c = norm_temp(tval) if tval else None
        add(out, f"(virtual) {ttype}", c, os.path.join(z, "temp"))

def scan_hwmon(out):
    base = "/sys/class/hwmon"
    if not os.path.isdir(base):
        return
    for hw in sorted(glob.glob(os.path.join(base, "hwmon*"))):
        chip = read(os.path.join(hw, "name")) or os.path.basename(hw)
        # temp*_input files (millidegree C typical)
        for tpath in sorted(glob.glob(os.path.join(hw, "temp*_input"))):
            raw = read(tpath)
            c = norm_temp(raw) if raw else None
            label = f"hwmon:{chip}:{os.path.basename(tpath)}"
            add(out, label, c, tpath)

def dumpsys_thermal(out):
    txt = sh("dumpsys thermalservice 2>/dev/null")
    if not txt:
        return
    # pull any lines with something like "Temperature{mValue=.., mType=.., mName=..}"
    # keep it simple: find numbers that look like temps + some nearby label
    lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
    for ln in lines:
        # capture common formats: "value: 42.0" or "mValue=42.0"
        m = re.search(r"(mValue=|value[:=]\s*)(-?\d+(\.\d+)?)", ln, re.IGNORECASE)
        if not m:
            continue
        c = float(m.group(2))
        # try to extract a name
        name = None
        m2 = re.search(r"(mName=|name[:=]\s*)([^,}\]]+)", ln, re.IGNORECASE)
        if m2:
            name = m2.group(2).strip().strip('"')
        label = f"dumpsys:{name}" if name else "dumpsys:thermal"
        add(out, label, c, "dumpsys thermalservice")

def termux_battery(out):
    txt = sh("termux-battery-status 2>/dev/null")
    if not txt:
        return
    try:
        jb = json.loads(txt)
        c = jb.get("temperature", None)
        if c is not None:
            add(out, "battery", float(c), "termux-battery-status")
    except Exception:
        pass

def main():
    temps = []
    termux_battery(temps)
    scan_thermal_zones_sysclass(temps)
    scan_thermal_zones_virtual(temps)
    scan_hwmon(temps)
    dumpsys_thermal(temps)

    if not temps:
        print("No temperature sources readable here.")
        return

    # sort hottest first
    temps.sort(key=lambda x: x[1], reverse=True)

    print("TEMPERATURES (°C)")
    print("-" * 60)
    for label, c, src in temps:
        print(f"{c:6.1f}  {label}   [{src}]")

if __name__ == "__main__":
    main()
