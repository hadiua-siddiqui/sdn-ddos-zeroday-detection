import glob, os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CUT = "20261028_1900"
base = os.path.expanduser("~/fyp/measure/")
runs = [r for r in sorted(glob.glob(base + "2026*_*"))
        if os.path.basename(r) >= CUT and os.path.exists(r + "/summary.csv")]
print(len(runs), "runs (pilot ke baghair)")

frames, extra = [], []
for r in runs:
    s = pd.read_csv(r + "/summary.csv")
    ref = s.loc[s["phase"] == "ref_tcp", "tcp_mbps"].iloc[0]
    s["tcp_ratio"] = s["tcp_mbps"] / ref
    s["victim_frac"] = np.where(s["phase"] == "udp400",
                                s["h5_rx_pkts"] / s["sent"], s["replies"] / s["sent"])
    s.loc[s["phase"].isin(["ref_tcp", "mixed_udp700"]), "victim_frac"] = np.nan
    frames.append(s)
    ld = pd.read_csv(glob.glob(r + "/live_decisions_*.csv")[0])
    extra.append([s["mode"].iloc[0], ld["rtt_ms"].median(), ld["rtt_ms"].quantile(0.95),
                  pd.read_csv(r + "/cpu_ryu.csv")["rss_mb"].max(),
                  pd.read_csv(r + "/cpu_predictor.csv")["rss_mb"].max()])
df = pd.concat(frames)
exd = pd.DataFrame(extra, columns=["mode", "rtt_median_ms", "rtt_p95_ms",
                                   "ryu_rss_mb", "pred_rss_mb"])
df.to_csv(base + "all_runs.csv", index=False)

bl = df[df["mode"] == "blocker"]
print("\nDetection latency (s), blocker:")
print(bl[bl["kind"] == "attack"].groupby("phase")["detect_s"]
      .agg(["mean", "std", "min", "max"]).round(2))

a = df[df["phase"].isin(["syn", "icmp", "udp400"])]
m = a.groupby(["phase", "mode"])["h5_rx_pkts"].agg(["mean", "std"]).unstack()
print("\nPackets reaching victim h5 (15 s):")
print(m.round(0))
print("Kam hone ka %:")
print(((1 - m[("mean", "blocker")] / m[("mean", "baseline")]) * 100).round(1))

t = df[df["phase"].isin(["mixed_syn", "mixed_udp700"])]
print("\nNormal TCP (attack ke dauran) / reference:")
print(t.groupby(["phase", "mode"])["tcp_ratio"].agg(["mean", "std"]).round(3))

print("\nCPU % (mean):")
print(df.groupby("mode")[["ryu_cpu", "pred_cpu"]].mean().round(1))
print("\nPredictor round trip aur RAM:")
print(exd.groupby("mode").mean().round(1))

fig, ax = plt.subplots(figsize=(7, 4))
ph = ["syn", "icmp", "udp400"]
x = np.arange(len(ph))
for i, mode in enumerate(["baseline", "blocker"]):
    mu = [m.loc[p, ("mean", mode)] for p in ph]
    sd = [m.loc[p, ("std", mode)] for p in ph]
    ax.bar(x + (i - 0.5) * 0.35, mu, 0.35, yerr=sd, capsize=3, label=mode)
ax.set_xticks(x)
ax.set_xticklabels(["SYN flood", "ICMP flood", "UDP flood (400 B)"])
ax.set_ylabel("Packets reaching victim h5 (15 s)")
ax.set_title("Attack traffic reaching the victim (mean +/- std, 5 runs)")
ax.legend()
plt.tight_layout()
plt.savefig(base + "fig_victim_packets.png", dpi=200)

d = bl[bl["kind"] == "attack"].groupby("phase")["detect_s"].agg(["mean", "std"])
fig, ax = plt.subplots(figsize=(7, 4))
ax.bar(range(len(d)), d["mean"], yerr=d["std"], capsize=3)
ax.set_xticks(range(len(d)))
ax.set_xticklabels(d.index, rotation=20)
ax.set_ylabel("Detection latency (s)")
ax.set_title("Time from attack start to block (mean +/- std, 5 runs)")
plt.tight_layout()
plt.savefig(base + "fig_detection_latency.png", dpi=200)
print("\nsaved all_runs.csv aur 2 charts in", base)
