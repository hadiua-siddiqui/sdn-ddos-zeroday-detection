import os, sys, random, time
from functools import partial
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from topo_fyp import FypTopo

STAMP = time.strftime("%Y%m%d_%H%M%S")
BASE = "/home/hadiya/fyp/runlogs"
SET = sys.argv[1] if len(sys.argv) > 1 else "C"
if SET not in ("C", "D"):
    raise SystemExit("C ya D likho")
OUT = BASE + "/" + STAMP + "_" + SET
os.makedirs(OUT, exist_ok=True)
V = "10.0.0.5"        # sirf Mininet ka h5, kabhi bahar ka IP nahi
D = 15                # har phase ka waqt (second)
COOLDOWN = 20         # block (15 s) ke baad bhi agla phase saaf shuru ho


def bg(h, cmd, name):
    open(OUT + "/commands.txt", "a").write("%s | %s | %s\n" % (name, h.name, cmd))
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
    def J(x):
        return int(x * random.uniform(0.85, 1.2))

    def hp(args, iv):
        return "timeout -s INT %d hping3 -q %s -i u%d %s" % (D, args, iv, V)

    def web(gap):
        return "timeout -s INT %d python3 /home/hadiya/fyp/webclient.py %s %s" % (D, V, gap)

    def png(sz, iv):
        return "ping -s %d -i %s -w %d %s" % (sz, iv, D, V)

    def udp(l, b):
        return "iperf -c %s -u -l %d -b %s -i 1 -t %d" % (V, l, b, D)

    def tcp(p):
        return "iperf -c %s -P %d -i 1 -t %d" % (V, p, D)

    PHASES_C = [
        ("n_ping_s0_20pps", "normal", [(h1, png(0, 0.05), "h1"), (h2, png(30, 0.03), "h2")]),
        ("n_ping_s6_50pps", "normal", [(h3, png(6, 0.02), "h3")]),
        ("n_ping_big_slow", "normal", [(h1, png(200, 0.2), "h1"), (h2, png(1000, 0.1), "h2")]),
        ("n_voip_small", "normal", [(h3, udp(100, "%dk" % J(60)), "h3")]),
        ("n_dns_like", "normal", [(h2, udp(60, "%dk" % J(48)), "h2")]),
        ("n_web_fast", "normal", [(h1, web(0.05), "h1"), (h2, web(0.1), "h2")]),
        ("n_tcp_p1_p3", "normal", [(h1, tcp(1), "h1"), (h2, tcp(3), "h2")]),
        ("n_udp_bulk_3m", "normal", [(h3, udp(1470, "3M"), "h3")]),
        ("a_syn_300", "attack", [(h4, hp("-S -p 80", J(3300)), "h4")]),
        ("a_syn_800", "attack", [(h4, hp("-S -p 80", J(1250)), "h4")]),
        ("a_icmp_500", "attack", [(h4, hp("--icmp -d 50", J(2000)), "h4")]),
        ("a_udp_400", "attack", [(h4, hp("--udp -p 80 -d 400", J(1500)), "h4")]),
        ("a_udp_1200", "attack", [(h4, hp("--udp -p 80 -d 1200", J(1000)), "h4")]),
        ("a_mixed_web", "attack", [(h1, web(0.1), "h1"), (h4, hp("-S -p 80", J(1000)), "h4")]),
        ("a_mixed_udp", "attack", [(h3, udp(1470, "2M"), "h3"), (h4, hp("--udp -p 80 -d 600", J(1200)), "h4")]),
    ]
    PHASES_D = [
        ("n_ping_58b_25pps", "normal", [(h1, png(16, 0.04), "h1")]),
        ("n_ping_142b_100pps", "normal", [(h2, png(100, 0.01), "h2")]),
        ("n_voip_120", "normal", [(h3, udp(120, "80k"), "h3")]),
        ("n_web_slow", "normal", [(h1, web(0.2), "h1"), (h3, web(0.15), "h3")]),
        ("n_tcp_p5", "normal", [(h1, tcp(5), "h1")]),
        ("n_udp_bulk_8m", "normal", [(h2, udp(1470, "8M"), "h2")]),
        ("a_syn_400", "attack", [(h4, hp("-S -p 80", 2500), "h4")]),
        ("a_syn_1700", "attack", [(h4, hp("-S -p 80", 600), "h4")]),
        ("a_icmp_big", "attack", [(h4, hp("--icmp -d 300", 1000), "h4")]),
        ("a_udp_700", "attack", [(h4, hp("--udp -p 80 -d 700", 2000), "h4")]),
        ("a_udp_1400", "attack", [(h4, hp("--udp -p 80 -d 1400", 800), "h4")]),
        ("a_mixed_tcp5", "attack", [(h1, tcp(5), "h1"), (h4, hp("-S -p 80", 1000), "h4")]),
    ]
    phases = PHASES_C if SET == "C" else PHASES_D
    print("set", SET, flush=True)
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
