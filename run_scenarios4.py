import os, sys, random, time
from functools import partial
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from topo_fyp import FypTopo

STAMP = time.strftime("%Y%m%d_%H%M%S")
BASE = "/home/hadiya/fyp/runlogs"
SET = sys.argv[1] if len(sys.argv) > 1 else "A"
if SET not in ("A", "B"):
    raise SystemExit("A ya B likho")
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
        return int(x * random.uniform(0.7, 1.4))

    def hp(args, iv):
        return "timeout -s INT %d hping3 -q %s -i u%d %s" % (D, args, iv, V)

    web = "timeout -s INT %d python3 /home/hadiya/fyp/webclient.py %s 0.1" % (D, V)
    PHASES_A = [
        ("n_ping_tiny", "normal", [(h, "ping -s 0 -i 0.1 -w %d %s" % (D, V), h.name) for h in (h1, h2, h3)]),
        ("n_ping_small_fast", "normal", [(h1, "ping -s 20 -i 0.05 -w %d %s" % (D, V), "h1"),
                                         (h2, "ping -s 56 -i 0.02 -w %d %s" % (D, V), "h2")]),
        ("n_voip", "normal", [(h3, "iperf -c %s -u -l 160 -b %dk -i 1 -t %d" % (V, J(64), D), "h3")]),
        ("n_web", "normal", [(h1, web, "h1"), (h2, web, "h2")]),
        ("n_tcp_p2", "normal", [(h1, "iperf -c %s -P 2 -i 1 -t %d" % (V, D), "h1")]),
        ("n_udp_100k", "normal", [(h2, "iperf -c %s -u -l 100 -b %dk -i 1 -t %d" % (V, J(100), D), "h2")]),
        ("a_syn", "attack", [(h4, hp("-S -p 80", J(1250)), "h4")]),
        ("a_icmp", "attack", [(h4, hp("--icmp", J(1000)), "h4")]),
        ("a_udp", "attack", [(h4, hp("--udp -p 80 -d 200", J(2000)), "h4")]),
        ("a_mixed_web", "attack", [(h1, web, "h1"), (h4, hp("-S -p 80", J(1000)), "h4")]),
    ]
    PHASES_B = [
        ("n_ping_52b", "normal", [(h1, "ping -s 10 -i 0.03 -w %d %s" % (D, V), "h1")]),
        ("n_voip_80", "normal", [(h3, "iperf -c %s -u -l 80 -b 40k -i 1 -t %d" % (V, D), "h3")]),
        ("n_web_tcp3", "normal", [(h1, web, "h1"), (h3, "iperf -c %s -P 3 -i 1 -t %d" % (V, D), "h3")]),
        ("n_udp_150k", "normal", [(h2, "iperf -c %s -u -l 120 -b 150k -i 1 -t %d" % (V, D), "h2")]),
        ("a_syn_1500", "attack", [(h4, hp("-S -p 80", 670), "h4")]),
        ("a_icmp_2000", "attack", [(h4, hp("--icmp -d 100", 500), "h4")]),
        ("a_udp_big", "attack", [(h4, hp("--udp -p 80 -d 800", 1500), "h4")]),
        ("a_mixed_voip", "attack", [(h3, "iperf -c %s -u -l 160 -b 64k -i 1 -t %d" % (V, D), "h3"),
                                    (h4, hp("--icmp", 1000), "h4")]),
    ]
    phases = PHASES_A if SET == "A" else PHASES_B
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
