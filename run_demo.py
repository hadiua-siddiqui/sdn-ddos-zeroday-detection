import os, re, sys, time
from functools import partial
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from topo_fyp import FypTopo

OUT, MODE, EVF = sys.argv[1], sys.argv[2], sys.argv[3]
V = "10.0.0.5"          # sirf Mininet ka h5, kabhi bahar ka IP nahi
G, R, Y, B, N = "\033[92m", "\033[91m", "\033[93m", "\033[1m", "\033[0m"
NAMES = {"00:00:00:00:00:0%d" % i: "h%d" % i for i in range(1, 6)}
S = {"prev_rx": 0, "prev_rep": 0, "t0": 0.0, "atk": 0.0, "attacking": False,
     "blocked": False, "seen": 0}
EVENTS = []
LAT = {}


def bg(h, cmd, name):
    h.cmd("%s > %s/%s.txt 2>&1 &" % (cmd, OUT, name))


def rx(h):
    for line in h.cmd("cat /proc/net/dev").splitlines():
        line = line.strip()
        if line.startswith(h.name + "-eth0:"):
            return int(line.split(":", 1)[1].split()[1])
    return 0


def replies():
    try:
        return open(OUT + "/ping_h1.txt").read().count("bytes from")
    except FileNotFoundError:
        return 0


def new_events():
    try:
        lines = open(EVF).read().splitlines()[1:]
    except FileNotFoundError:
        return []
    out = []
    for l in lines[S["seen"]:]:
        p = l.split(",", 3)
        try:
            out.append((float(p[0]), p[1], p[2], p[3] if len(p) > 3 else ""))
        except (ValueError, IndexError):
            pass
    S["seen"] = len(lines)
    return out


def tick(seconds):
    for _ in range(int(seconds)):
        time.sleep(1)
        cur, rp = rx(h5), replies()
        d_rx, d_rp = cur - S["prev_rx"], rp - S["prev_rep"]
        S["prev_rx"], S["prev_rep"] = cur, rp
        for ts, ev, src, det in new_events():
            EVENTS.append((ts, ev, src, det))
            who = NAMES.get(src, src)
            if ev == "BLOCK":
                S["blocked"] = True
                lat = "%.1f s after attack start" % (ts - S["atk"]) if S["atk"] else ""
                print("%s%s>>> CONTROLLER: attack detected -> BLOCK %s (%s)%s" % (R, B, who, lat, N), flush=True)
            elif ev == "UNBLOCK":
                S["blocked"] = False
                print("%s>>> CONTROLLER: UNBLOCK %s (%s)%s" % (
                    Y, who, det.replace("dropped=", "dropped packets: "), N), flush=True)
        if S["attacking"]:
            txt, col = ("ATTACK + BLOCKED" if S["blocked"] else "ATTACK"), R
        elif S["blocked"]:
            txt, col = "BLOCK ACTIVE", Y
        else:
            txt, col = "normal", G
        print("[%3ds] %s%-17s%s | victim receives %5d pkt/s | normal ping replies %2d/s" % (
            time.time() - S["t0"], col, txt, N, d_rx, d_rp), flush=True)


def attack(title, cmd, tag):
    print("\n%s%s>>> ATTACK: %s%s" % (R, B, title, N), flush=True)
    S["atk"] = time.time()
    S["attacking"] = True
    bg(h4, cmd, "attack_" + tag)
    tick(14)
    S["attacking"] = False
    waited = 0
    while waited < 25 and not any(e[1] == "UNBLOCK" and e[0] > S["atk"] for e in EVENTS):
        tick(1)
        waited += 1
    tick(3)
    blocks = [e for e in EVENTS if e[1] == "BLOCK" and e[0] >= S["atk"]]
    LAT[tag] = (blocks[0][0] - S["atk"]) if blocks else None


net = Mininet(topo=FypTopo(), controller=None, autoSetMacs=True,
              switch=partial(OVSSwitch, protocols="OpenFlow13"))
net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
net.start()
h1, h2, h3, h4, h5 = [net.get(n) for n in ("h1", "h2", "h3", "h4", "h5")]
try:
    for tool in ("hping3", "timeout"):
        if not h1.cmd("which " + tool).strip():
            raise SystemExit("%s install nahi hai" % tool)
    print("\n%s=== SDN DDoS demo: XGBoost detector + Ryu auto-block ===%s" % (B, N))
    print("h1, h2, h3 = normal users | h4 = attacker | h5 = victim server (10.0.0.5)\n", flush=True)
    net.pingAll()
    bg(h5, "python3 -m http.server 80", "server_http")
    time.sleep(2)
    bg(h1, "ping -i 0.1 -w 600 " + V, "ping_h1")
    bg(h2, "python3 /home/hadiya/fyp/webclient.py %s 0.1" % V, "web_h2")
    time.sleep(1)
    print("\n>>> Normal traffic running: h1 ping (10/s) and h2 web requests (10/s)", flush=True)
    S["t0"] = time.time()
    S["prev_rx"], S["prev_rep"] = rx(h5), replies()
    tick(6)
    atks = [
        ("SYN flood from h4 to h5 (about 900 packets/s)",
         "timeout -s INT 14 hping3 -q -S -p 80 -i u1000 " + V, "syn"),
        ("ICMP flood from h4 (about 500 packets/s)",
         "timeout -s INT 14 hping3 -q --icmp -d 50 -i u2000 " + V, "icmp"),
        ("UDP flood from h4, 400-byte payload (about 650 packets/s)",
         "timeout -s INT 14 hping3 -q --udp -p 80 -d 400 -i u1500 " + V, "udp400"),
    ]
    if MODE == "quick":
        atks = atks[:1]
    for t, c, g in atks:
        attack(t, c, g)
    tick(3)
    h1.cmd("pkill -INT ping")
    time.sleep(1.5)
    txt = open(OUT + "/ping_h1.txt").read()
    m = re.search(r"(\d+) packets transmitted, (\d+) received.*?([\d.]+)% packet loss", txt)
    print("\n%s=== SUMMARY ===%s" % (B, N))
    for tag, lat in LAT.items():
        print("  %-8s blocked after %s" % (tag, ("%.1f s" % lat) if lat is not None else "NOT BLOCKED"))
    who = sorted(set(NAMES.get(e[2], e[2]) for e in EVENTS if e[1] == "BLOCK"))
    print("  hosts blocked by the controller:", ", ".join(who) or "none")
    if m:
        print("  normal ping h1->h5: %s sent, %s received, %s%% loss" % m.groups())
finally:
    h2.cmd("pkill -f webclient.py")
    net.stop()
    os.system("chown -R hadiya:hadiya " + OUT)
