import json
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

sessions = {
    "Baseline (idle)":       "session_base.json",
    "Chrome only":           "session_chrome.json",
    "Wikipedia (no images)": "session_iiab_nopic.json",
    "Wikipedia (images)":    "session_iiab_pic.json",
    "Maps":                  "session_map.json",
}

colors = ["#2196F3", "#4CAF50", "#FF5722", "#9C27B0", "#FF9800"]
styles = ["-", "-", "-", "-", "-"]

fig, axes = plt.subplots(2, 1, figsize=(13, 9))
plt.subplots_adjust(hspace=0.42, left=0.09, right=0.97, top=0.96, bottom=0.14)

panels = [
    (axes[0], "cpu_percent", "CPU Usage (%)",  "Time (s)", "%"),
    (axes[1], "ram.used_mb", "RAM Usage (MB)", "Time (s)", "MB"),
]

for ax, field, title, xlabel, ylabel in panels:
    for i, (label, filepath) in enumerate(sessions.items()):
        try:
            with open(filepath) as f:
                data = json.load(f)
        except:
            continue

        timestamps = [d["timestamp_s"] for d in data]
        keys = field.split(".")
        values = []
        for d in data:
            val = d
            for k in keys:
                val = val.get(k, None)
                if val is None:
                    break
            values.append(val)

        if any(v is None for v in values):
            continue

        ax.plot(timestamps, values, label=label,
                color=colors[i], linestyle=styles[i], linewidth=2)

    ax.set_title(title, fontsize=17, fontweight="bold")
    ax.set_xlabel(xlabel, fontsize=16, color="#555")
    ax.set_ylabel(ylabel, fontsize=16, color="#555")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#ccc")
    ax.spines["bottom"].set_color("#ccc")
    ax.grid(axis="y", color="#e5e5e5", linewidth=0.8)
    ax.set_facecolor("white")

    if field == "ram.used_mb":
        ax.set_ylim(1500, 3000)
    else:
        y_vals = [line.get_ydata() for line in ax.get_lines()]
        all_vals = [v for ys in y_vals for v in ys]
        if all_vals:
            padding = (max(all_vals) - min(all_vals)) * 0.3 or 1
            ax.set_ylim(min(all_vals) - padding, max(all_vals) + padding)

    ax.yaxis.set_major_locator(ticker.MaxNLocator(nbins=6))
    ax.tick_params(colors="#555", labelsize=15)

handles, labels = axes[0].get_legend_handles_labels()
fig.legend(handles, labels, loc="lower center", ncol=5,
           fontsize=14, framealpha=0, bbox_to_anchor=(0.5, 0.01))

fig.patch.set_facecolor("white")
plt.savefig("session_compare.png", dpi=150, facecolor="white")
print("Saved: session_compare.png")
