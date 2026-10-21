import sys, glob, os
import pandas as pd

if len(sys.argv) > 1:
    path = os.path.expanduser(sys.argv[1])
else:
    path = sorted(glob.glob(os.path.expanduser("~/fyp/flow_stats_*.csv")))[-1]
print("reading", path)

df = pd.read_csv(path)
df = df[df["dpid"] == 2].sort_values("time")
key = ["dpid", "in_port", "eth_src", "eth_dst"]
g = df.groupby(key)
df["dt"] = g["time"].diff()
df["d_packets"] = g["packets"].diff()
df["d_bytes"] = g["bytes"].diff()
df = df.dropna(subset=["dt"])
df = df[(df["dt"] > 0) & (df["d_packets"] > 0) & (df["d_bytes"] >= 0)].copy()

df["pkts_per_s"] = df["d_packets"] / df["dt"]
df["bytes_per_s"] = df["d_bytes"] / df["dt"]
df["avg_pkt_size"] = df["d_bytes"] / df["d_packets"]

ATT = "00:00:00:00:00:04"
df["label"] = ((df["eth_src"] == ATT) | (df["eth_dst"] == ATT)).map(
    {True: "attack", False: "normal"})

feat = ["pkts_per_s", "bytes_per_s", "avg_pkt_size"]
print(df["label"].value_counts())
print(df.groupby("label")[feat].median().round(1))

out = os.path.expanduser("~/fyp/mininet_dataset.csv")
df[["time"] + key + feat + ["label"]].to_csv(out, index=False)
print("saved", out, len(df), "rows")
