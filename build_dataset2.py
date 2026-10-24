import sys, os
import pandas as pd

flow_path, phases_path = [os.path.expanduser(a) for a in sys.argv[1:3]]
ATT = "00:00:00:00:00:04"
SLACK = 1.0
ph = pd.read_csv(phases_path)

df = pd.read_csv(flow_path)
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
df["t0"] = df["time"] - df["dt"]
involves = (df["eth_src"] == ATT) | (df["eth_dst"] == ATT)

df["phase"] = "idle"
df["label"] = "normal"
ambiguous = pd.Series(False, index=df.index)
for _, r in ph.iterrows():
    s, e = r["start"], r["end"] + SLACK
    inside = (df["t0"] >= s) & (df["time"] <= e)
    overlap = (df["time"] > s) & (df["t0"] < e)
    df.loc[inside, "phase"] = r["phase"]
    if r["kind"] == "attack":
        df.loc[inside & involves, "label"] = "attack"
        ambiguous |= (overlap & ~inside & involves)
df = df[~ambiguous].copy()

feat = ["pkts_per_s", "bytes_per_s", "avg_pkt_size"]
print(df.groupby(["phase", "label"]).size())
out = os.path.expanduser("~/fyp/ds2_" + os.path.basename(flow_path))
df[["time", "phase"] + key + feat + ["label"]].to_csv(out, index=False)
print("saved", out, len(df), "rows")
