#!/usr/bin/env python3
import os
import subprocess
from datetime import datetime

def run(cmd: str) -> str:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        return ((p.stdout or "") + (p.stderr or "")).strip()
    except Exception:
        return ""

def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

def listdir_safe(path: str):
    try:
        return sorted(os.listdir(path))
    except Exception:
        return []

def int_or_none(s: str):
    s = (s or "").strip()
    if s.isdigit():
        return int(s)
    try:
        return int(float(s))
    except Exception:
        return None

def khz_to_mhz(khz: int) -> float:
    return khz / 1000.0

def cpu_list():
    base = "/sys/devices/system/cpu"
    cpus = []
    for name in listdir_safe(base):
        if name.startswith("cpu") and name[3:].isdigit():
            cpus.append(name)
    return base, cpus

def read_cpufreq(cpu_base: str, cpu: str):
    cpufreq = os.path.join(cpu_base, cpu, "cpufreq")
    cur = int_or_none(read_file(os.path.join(cpufreq, "scaling_cur_freq")))
    mi  = int_or_none(read_file(os.path.join(cpufreq, "scaling_min_freq")))
    ma  = int_or_none(read_file(os.path.join(cpufreq, "scaling_max_freq")))
    return cur, mi, ma

def top_processes():
    cmds = [
        "ps -eo pid,comm,%cpu,rss --sort=-%cpu | head -n 15",
        "ps -A -o PID,NAME,CPU%,RSS --sort=-CPU% | head -n 15",
        "top -b -n 1 | head -n 25",
    ]
    for c in cmds:
        out = run(c)
        if out:
            return c, out
    return "", "(no ps/top output available)"

def main():
    print("=" * 60)
    print("IIAB PERF SNAPSHOT (CPU FREQ + TOP PROCESSES)")
    print("Time:", datetime.now().isoformat(timespec="seconds"))
    print("=" * 60)

    # 1) CPU frequencies
    print("\n[CPUFREQ PER CORE]")
    cpu_base, cpus = cpu_list()
    if not cpus:
        print("(no cpu entries found)")
    else:
        for cpu in cpus:
            cur, mi, ma = read_cpufreq(cpu_base, cpu)
            if cur is None and mi is None and ma is None:
                print(f"{cpu}: (cpufreq not readable)")
                continue
            def fmt(x): return f"{khz_to_mhz(x):.0f}MHz" if x is not None else "?"
            print(f"{cpu}: cur={fmt(cur)} min={fmt(mi)} max={fmt(ma)}")

    # 2) Top processes
    print("\n[TOP PROCESSES]")
    cmd, out = top_processes()
    if cmd:
        print(f"$ {cmd}")
    print(out)

if __name__ == "__main__":
    main()
