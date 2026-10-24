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
    phases = [
        ("normal_ping", "normal", [(h1, ping, "h1"), (h2, ping, "h2"), (h3, ping, "h3")]),
        ("normal_tcp", "normal", [(h1, tcp, "h1"), (h2, tcp, "h2")]),
        ("normal_udp", "normal", [(h3, "iperf -c %s -u -b 1M -i 1 -t %d" % (V, D), "h3")]),
        ("normal_h4_ping", "normal", [(h4, ping, "h4")]),
        ("syn_1000", "attack", [(h4, syn, "h4")]),
        ("syn_200", "attack", [(h4, "timeout -s INT %d hping3 -q -S -p 80 -i u5000 %s" % (D, V), "h4")]),
        ("udp_flood", "attack", [(h4, "timeout -s INT %d hping3 -q --udp -p 80 -d 100 -i u1000 %s" % (D, V), "h4")]),
        ("mixed", "attack", [(h1, tcp, "h1"), (h4, syn, "h4")]),
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
