import sys, re, glob
import pandas as pd

run = sys.argv[1].rstrip("/")
mode = open(run + "/mode.txt").read().strip()
ph = pd.read_csv(run + "/phases.csv")
ev = pd.read_csv(glob.glob(run + "/block_events_*.csv")[0])
ev = ev[ev["event"].isin(["BLOCK", "WOULD_BLOCK"])]


def iperf_mbps(path):
    best = None
    try:
        for line in open(path):
            m = re.search(r"([\d.]+)\s+([KMG])bits/sec", line)
            if m:
                best = float(m.group(1)) * {"K": 0.001, "M": 1, "G": 1000}[m.group(2)]
    except FileNotFoundError:
        pass
    return None if best is None else round(best, 1)


def hping(path):
    try:
        m = re.search(r"(\d+) packets transmitted, (\d+) packets received", open(path).read())
        if m:
            return int(m.group(1)), int(m.group(2))
    except FileNotFoundError:
        pass
    return None, None


def cpu_mean(path, s, e):
    try:
        d = pd.read_csv(path)
        d = d[(d["time"] >= s) & (d["time"] <= e)]
        return round(d["cpu_pct"].mean(), 1) if len(d) else None
    except Exception:
        return None


rows = []
for _, r in ph.iterrows():
    lat = None
    if r["kind"] == "attack":
        e = ev[(ev["time"] >= r["start"]) & (ev["time"] <= r["end"] + 10)]
        if len(e):
            lat = round(e["time"].iloc[0] - r["start"], 1)
    sent, rec = hping("%s/%s_h4.txt" % (run, r["phase"]))
    rows.append([mode, r["phase"], r["kind"], lat, sent, rec, int(r["h5_rx_pkts"]),
                 iperf_mbps("%s/%s_h1.txt" % (run, r["phase"])),
                 cpu_mean(run + "/cpu_ryu.csv", r["start"], r["end"]),
                 cpu_mean(run + "/cpu_predictor.csv", r["start"], r["end"])])
df = pd.DataFrame(rows, columns=["mode", "phase", "kind", "detect_s", "sent", "replies",
                                 "h5_rx_pkts", "tcp_mbps", "ryu_cpu", "pred_cpu"])
df.to_csv(run + "/summary.csv", index=False)
print(df.to_string(index=False))
ld = pd.read_csv(glob.glob(run + "/live_decisions_*.csv")[0])
print("\npredictor round trip ms: median %.1f | p95 %.1f" % (
    ld["rtt_ms"].median(), ld["rtt_ms"].quantile(0.95)))
for n in ("ryu", "predictor"):
    try:
        print(n, "peak RAM MB:", pd.read_csv("%s/cpu_%s.csv" % (run, n))["rss_mb"].max())
    except Exception:
        pass
