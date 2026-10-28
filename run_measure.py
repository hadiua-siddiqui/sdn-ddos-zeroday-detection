import os, sys, time
from functools import partial
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from topo_fyp import FypTopo

OUT = sys.argv[1]
V = "10.0.0.5"          # sirf Mininet ka h5, kabhi bahar ka IP nahi
D = 15
COOLDOWN = 22


def bg(h, cmd, name):
    open(OUT + "/commands.txt", "a").write("%s | %s | %s\n" % (name, h.name, cmd))
    h.cmd("%s > %s/%s.txt 2>&1 &" % (cmd, OUT, name))


def rx(h):
    for line in h.cmd("cat /proc/net/dev").splitlines():
        line = line.strip()
        if line.startswith(h.name + "-eth0:"):
            f = line.split(":", 1)[1].split()
            return int(f[1]), int(f[0])      # packets, bytes
    return 0, 0


net = Mininet(topo=FypTopo(), controller=None, autoSetMacs=True,
              switch=partial(OVSSwitch, protocols="OpenFlow13"))
net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
net.start()
h1, h2, h3, h4, h5 = [net.get(n) for n in ("h1", "h2", "h3", "h4", "h5")]
ph = open(OUT + "/phases.csv", "w")
ph.write("phase,kind,start,end,h5_rx_pkts,h5_rx_bytes\n")
try:
    for tool in ("iperf", "hping3", "timeout"):
        if not h1.cmd("which " + tool).strip():
            raise SystemExit("%s install nahi hai" % tool)
    net.pingAll()
    bg(h5, "python3 -m http.server 80", "server_http")
    bg(h5, "iperf -s", "server_iperf_tcp")
    time.sleep(3)
    tcp = "iperf -c %s -i 1 -t %d" % (V, D)

    def hp(args, iv):
        return "timeout -s INT %d hping3 -q %s -i u%d %s" % (D, args, iv, V)

    phases = [
        ("ref_tcp", "normal", [(h1, tcp, "h1")]),
        ("syn", "attack", [(h4, hp("-S -p 80", 1000), "h4")]),
        ("icmp", "attack", [(h4, hp("--icmp -d 50", 2000), "h4")]),
        ("udp400", "attack", [(h4, hp("--udp -p 80 -d 400", 1500), "h4")]),
        ("mixed_syn", "attack", [(h1, tcp, "h1"), (h4, hp("-S -p 80", 1000), "h4")]),
        ("mixed_udp700", "attack", [(h1, tcp, "h1"), (h4, hp("--udp -p 80 -d 700", 2000), "h4")]),
    ]
    for name, kind, jobs in phases:
        print(">>", name, flush=True)
        p0, b0 = rx(h5)
        t0 = time.time()
        for h, cmd, tag in jobs:
            bg(h, cmd, "%s_%s" % (name, tag))
        time.sleep(D + 3)
        p1, b1 = rx(h5)
        ph.write("%s,%s,%.2f,%.2f,%d,%d\n" % (name, kind, t0, t0 + D, p1 - p0, b1 - b0))
        ph.flush()
        time.sleep(COOLDOWN)
finally:
    ph.close()
    net.stop()
    os.system("chown -R hadiya:hadiya " + OUT)
