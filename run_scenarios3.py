import os, time
from functools import partial
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from topo_fyp import FypTopo

STAMP = time.strftime("%Y%m%d_%H%M%S")
BASE = "/home/hadiya/fyp/runlogs"
OUT = BASE + "/" + STAMP
os.makedirs(OUT, exist_ok=True)
V = "10.0.0.5"        # sirf Mininet ka h5, kabhi bahar ka IP nahi
D = 15                # har phase ka waqt (second)
COOLDOWN = 20         # block (15 s) ke baad bhi agla phase saaf shuru ho


def bg(h, cmd, name):
    h.cmd("%s > %s/%s.txt 2>&1 &" % (cmd, OUT, name))


net = Mininet(topo=FypTopo(), controller=None, autoSetMacs=True,
              switch=partial(OVSSwitch, protocols="OpenFlow13"))
net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
net.start()
h1, h2, h3, h4, h5 = [net.get(n) for n in ("h1", "h2", "h3", "h4", "h5")]
ph = open(OUT + "/phases.csv", "w")
ph.write("phase,kind,start,end\n")
try:
    for tool in ("iperf", "hping3", "timeout"):
        if not h1.cmd("which " + tool).strip():
            raise SystemExit("%s install nahi hai" % tool)
    net.pingAll()
    bg(h5, "python3 -m http.server 80", "server_http")
    bg(h5, "iperf -s", "server_iperf_tcp")
    bg(h5, "iperf -s -u", "server_iperf_udp")
    time.sleep(2)
    ping = "ping -i 0.2 -w %d %s" % (D, V)
    tcp = "iperf -c %s -i 1 -t %d" % (V, D)
    syn = "timeout -s INT %d hping3 -q -S -p 80 -i u1000 %s" % (D, V)
    ping_n = "ping -i 0.5 -w %d %s" % (D, V)
    ping_s = "ping -s 20 -i 0.05 -w %d %s" % (D, V)
    tcp4 = "iperf -c %s -P 4 -i 1 -t %d" % (V, D)
    syn500 = "timeout -s INT %d hping3 -q -S -p 80 -i u2000 %s" % (D, V)
    syn2000 = "timeout -s INT %d hping3 -q -S -p 80 -i u500 %s" % (D, V)
    udp300 = "timeout -s INT %d hping3 -q --udp -p 80 -d 400 -i u3000 %s" % (D, V)
    phases = [
        ("normal_ping_slow", "normal", [(h1, ping_n, "h1"), (h2, ping_n, "h2"), (h3, ping_n, "h3")]),
        ("normal_ping_fast_small", "normal", [(h1, ping_s, "h1")]),
        ("normal_tcp_p4", "normal", [(h1, tcp4, "h1")]),
        ("normal_udp_5m", "normal", [(h3, "iperf -c %s -u -b 5M -i 1 -t %d" % (V, D), "h3")]),
        ("normal_udp_200k", "normal", [(h2, "iperf -c %s -u -b 200k -i 1 -t %d" % (V, D), "h2")]),
        ("syn_500", "attack", [(h4, syn500, "h4")]),
        ("syn_2000", "attack", [(h4, syn2000, "h4")]),
        ("udp_300_big", "attack", [(h4, udp300, "h4")]),
        ("mixed_udp", "attack", [(h3, "iperf -c %s -u -b 2M -i 1 -t %d" % (V, D), "h3"), (h4, syn500, "h4")]),
    ]
    for name, kind, jobs in phases:
        print(">>", name, flush=True)
        t0 = time.time()
        for h, cmd, tag in jobs:
            bg(h, cmd, "%s_%s" % (name, tag))
        ph.write("%s,%s,%.2f,%.2f\n" % (name, kind, t0, t0 + D))
        ph.flush()
        time.sleep(D + 2 + COOLDOWN)
finally:
    ph.close()
    net.stop()
    os.system("chown -R hadiya:hadiya " + BASE)
