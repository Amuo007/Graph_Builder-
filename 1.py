#!/usr/bin/env python3
"""
termux_cpu_snapshot.py
One-time CPU snapshot (no loop). Designed for Termux (no root).
Grabs:
- /proc/cpuinfo summary + raw
- CPU online/present/possible
- per-core cpufreq (cur/min/max), governor, available freqs/governors
- per-core topology (package/core ids) when available
- android getprop SoC/ABI info
- some scheduler/cpuset hints (if accessible)
- optional: top cpu processes (may be restricted)

Run:
  python termux_cpu_snapshot.py
"""

import os
import json
import platform
import subprocess
from datetime import datetime

def run(cmd: str) -> str:
    try:
        p = subprocess.run(cmd, shell=True, text=True, capture_output=True)
        out = (p.stdout or "").strip()
        return out
    except Exception:
        return ""

def read_file(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read().strip()
    except Exception:
        return ""

def exists(path: str) -> bool:
    try:
        return os.path.exists(path)
    except Exception:
        return False

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
        # sometimes contains newline or spaces
        return int(float(s))
    except Exception:
        return None

def khz_to_mhz(khz: int) -> float:
    return khz / 1000.0

def parse_cpuinfo(raw: str):
    """
    Parses /proc/cpuinfo into:
    - per_cpu: list of dict blocks
    - common: dict of most common keys (Hardware/model/Features/etc.)
    """
    if not raw:
        return [], {}

    blocks = []
    cur = {}
    for line in raw.splitlines():
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = {}
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            cur[k.strip()] = v.strip()
    if cur:
        blocks.append(cur)

    common_keys = [
        "Hardware", "model name", "Processor", "CPU implementer",
        "CPU part", "CPU revision", "Features", "BogoMIPS", "Serial"
    ]
    common = {}
    for k in common_keys:
        # find first occurrence across blocks
        for b in blocks:
            if k in b:
                common[k] = b[k]
                break

    # also count processors
    common["cpu_blocks"] = len(blocks)
    return blocks, common

def get_android_props():
    props = [
        "ro.product.manufacturer",
        "ro.product.model",
        "ro.build.version.release",
        "ro.build.version.sdk",
        "ro.product.cpu.abi",
        "ro.product.cpu.abilist",
        "ro.soc.manufacturer",
        "ro.soc.model",
        "ro.hardware",
        "ro.boot.hardware",
        "ro.board.platform",
    ]
    out = {}
    for p in props:
        v = run(f"getprop {p}")
        if v:
            out[p] = v
    return out

def cpu_paths():
    base = "/sys/devices/system/cpu"
    cpus = []
    for name in listdir_safe(base):
        if name.startswith("cpu") and name[3:].isdigit():
            cpus.append(name)
    return base, cpus

def read_cpufreq(cpu_base: str, cpu: str):
    # Many devices restrict parts of this; read what we can.
    d = {"cpu": cpu}

    cpufreq = os.path.join(cpu_base, cpu, "cpufreq")
    if not exists(cpufreq):
        d["cpufreq_available"] = False
        return d
    d["cpufreq_available"] = True

    cur = int_or_none(read_file(os.path.join(cpufreq, "scaling_cur_freq")))
    mi  = int_or_none(read_file(os.path.join(cpufreq, "scaling_min_freq")))
    ma  = int_or_none(read_file(os.path.join(cpufreq, "scaling_max_freq")))
    gov = read_file(os.path.join(cpufreq, "scaling_governor"))

    d["scaling_governor"] = gov or None
    d["scaling_cur_freq_khz"] = cur
    d["scaling_min_freq_khz"] = mi
    d["scaling_max_freq_khz"] = ma
    if cur is not None:
        d["scaling_cur_freq_mhz"] = round(khz_to_mhz(cur), 1)
    if mi is not None:
        d["scaling_min_freq_mhz"] = round(khz_to_mhz(mi), 1)
    if ma is not None:
        d["scaling_max_freq_mhz"] = round(khz_to_mhz(ma), 1)

    # Optional extras
    d["cpuinfo_cur_freq_khz"] = int_or_none(read_file(os.path.join(cpufreq, "cpuinfo_cur_freq")))
    d["cpuinfo_min_freq_khz"] = int_or_none(read_file(os.path.join(cpufreq, "cpuinfo_min_freq")))
    d["cpuinfo_max_freq_khz"] = int_or_none(read_file(os.path.join(cpufreq, "cpuinfo_max_freq")))

    d["available_frequencies_khz"] = read_file(os.path.join(cpufreq, "scaling_available_frequencies")) or None
    d["available_governors"] = read_file(os.path.join(cpufreq, "scaling_available_governors")) or None

    # Some kernels expose "related_cpus"
    d["related_cpus"] = read_file(os.path.join(cpufreq, "related_cpus")) or None

    return d

def read_topology(cpu_base: str, cpu: str):
    topo = os.path.join(cpu_base, cpu, "topology")
    d = {"cpu": cpu}
    if not exists(topo):
        d["topology_available"] = False
        return d
    d["topology_available"] = True

    # Common topology files (may be missing)
    d["physical_package_id"] = int_or_none(read_file(os.path.join(topo, "physical_package_id")))
    d["core_id"] = int_or_none(read_file(os.path.join(topo, "core_id")))
    d["cluster_id"] = int_or_none(read_file(os.path.join(topo, "cluster_id")))  # rare
    d["thread_siblings_list"] = read_file(os.path.join(topo, "thread_siblings_list")) or None
    d["core_siblings_list"] = read_file(os.path.join(topo, "core_siblings_list")) or None
    return d

def read_cpu_online_present_possible():
    base = "/sys/devices/system/cpu"
    return {
        "present": read_file(os.path.join(base, "present")) or None,
        "online": read_file(os.path.join(base, "online")) or None,
        "possible": read_file(os.path.join(base, "possible")) or None,
        "offline": read_file(os.path.join(base, "offline")) or None,
    }

def read_cpuset_info():
    # May be restricted on some devices
    paths = {
        "cpuset_root_cpus": "/dev/cpuset/cpus",
        "cpuset_root_mems": "/dev/cpuset/mems",
        "cpuset_top_app_cpus": "/dev/cpuset/top-app/cpus",
        "cpuset_foreground_cpus": "/dev/cpuset/foreground/cpus",
        "cpuset_background_cpus": "/dev/cpuset/background/cpus",
        "cpuset_system_background_cpus": "/dev/cpuset/system-background/cpus",
    }
    out = {}
    for k, p in paths.items():
        v = read_file(p)
        if v:
            out[k] = v
    return out

def get_process_cpu_snapshot():
    # Might be restricted; try a few commands
    cmds = [
        "ps -A -o PID,NAME,CPU%,RSS --sort=-CPU% | head -n 15",
        "ps -eo pid,comm,%cpu,rss --sort=-%cpu | head -n 15",
        "top -b -n 1 | head -n 25",
    ]
    for c in cmds:
        out = run(c)
        if out:
            return {"cmd": c, "output": out}
    return {}

def main():
    snapshot = {
        "time": datetime.now().isoformat(timespec="seconds"),
        "kernel_release": platform.release(),
        "machine": platform.machine(),
        "platform": platform.platform(),
        "android_props": get_android_props(),
        "cpu_online_present_possible": read_cpu_online_present_possible(),
        "cpuset": read_cpuset_info(),
    }

    raw_cpuinfo = read_file("/proc/cpuinfo")
    blocks, common = parse_cpuinfo(raw_cpuinfo)
    snapshot["proc_cpuinfo_common"] = common
    snapshot["proc_cpuinfo_per_cpu_blocks"] = blocks  # can be long
    snapshot["proc_cpuinfo_raw"] = raw_cpuinfo  # can be long

    cpu_base, cpus = cpu_paths()
    snapshot["sys_cpu_count_detected"] = len(cpus)
    snapshot["sys_cpus"] = cpus

    per_core = []
    per_topo = []
    for cpu in cpus:
        per_core.append(read_cpufreq(cpu_base, cpu))
        per_topo.append(read_topology(cpu_base, cpu))
    snapshot["cpufreq_per_core"] = per_core
    snapshot["topology_per_core"] = per_topo

    # Optional: load avg (helps interpret CPU behavior)
    snapshot["proc_loadavg"] = read_file("/proc/loadavg") or None

    # Optional: top CPU processes
    snapshot["top_processes"] = get_process_cpu_snapshot()

    # ---------- Pretty Print ----------
    print("=" * 70)
    print("TERMUX CPU SNAPSHOT")
    print("Time:", snapshot["time"])
    print("=" * 70)

    print("\n[ANDROID / DEVICE]")
    for k, v in snapshot["android_props"].items():
        print(f"{k}: {v}")

    print("\n[CPU PRESENCE]")
    for k, v in snapshot["cpu_online_present_possible"].items():
        if v:
            print(f"{k}: {v}")

    print("\n[/proc/cpuinfo SUMMARY]")
    for k, v in snapshot["proc_cpuinfo_common"].items():
        print(f"{k}: {v}")

    print("\n[CPUFREQ PER CORE] (what Android allows)")
    for d in snapshot["cpufreq_per_core"]:
        cpu = d["cpu"]
        if not d.get("cpufreq_available"):
            print(f"{cpu}: cpufreq not available")
            continue
        cur = d.get("scaling_cur_freq_mhz")
        mi = d.get("scaling_min_freq_mhz")
        ma = d.get("scaling_max_freq_mhz")
        gov = d.get("scaling_governor")
        print(f"{cpu}: cur={cur}MHz min={mi}MHz max={ma}MHz gov={gov}")

    print("\n[TOPOLOGY PER CORE] (if exposed)")
    any_topo = False
    for t in snapshot["topology_per_core"]:
        if t.get("topology_available") and (t.get("core_id") is not None or t.get("physical_package_id") is not None):
            any_topo = True
            print(f"{t['cpu']}: package={t.get('physical_package_id')} core={t.get('core_id')} thread_siblings={t.get('thread_siblings_list')}")
    if not any_topo:
        print("Topology not exposed (common on locked-down devices).")

    if snapshot.get("cpuset"):
        print("\n[CPUSET / SCHEDULER HINTS] (app foreground vs background cores)")
        for k, v in snapshot["cpuset"].items():
            print(f"{k}: {v}")

    if snapshot.get("proc_loadavg"):
        print("\n[LOADAVG]")
        print(snapshot["proc_loadavg"])

    if snapshot.get("top_processes"):
        print("\n[TOP PROCESSES]")
        print(f"$ {snapshot['top_processes'].get('cmd')}")
        print(snapshot["top_processes"].get("output"))

    print("\n[JSON DUMP] (copy/paste this if you want)")
    print(json.dumps(snapshot, indent=2))

if __name__ == "__main__":
    main()
