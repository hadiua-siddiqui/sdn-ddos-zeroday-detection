import time
from functools import partial
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from topo_fyp import FypTopo

def bg(h, cmd):
    h.cmd(cmd + " > /dev/null 2>&1 &")

net = Mininet(topo=FypTopo(), controller=None, autoSetMacs=True,
              switch=partial(OVSSwitch, protocols="OpenFlow13"))
net.addController("c0", controller=RemoteController, ip="127.0.0.1", port=6653)
net.start()
h1, h2, h3, h4, h5 = [net.get(n) for n in ("h1", "h2", "h3", "h4", "h5")]
try:
    for tool in ("iperf", "hping3"):
        if not h1.cmd("which " + tool).strip():
            raise SystemExit("%s install nahi hai: sudo apt install %s -y" % (tool, tool))
    net.pingAll()
    bg(h5, "python3 -m http.server 80")
    bg(h5, "iperf -s")
    bg(h5, "iperf -s -u")
    time.sleep(2)
    V = "10.0.0.5"   # victim: sirf Mininet ka h5, kabhi bahar ka IP nahi
    phases = [
        ("normal ping", [(h1, "ping -i 0.2 -c 100 " + V), (h2, "ping -i 0.2 -c 100 " + V),
                         (h3, "ping -i 0.2 -c 100 " + V)], 25),
        ("normal TCP", [(h1, "iperf -c " + V + " -t 15"), (h2, "iperf -c " + V + " -t 15")], 20),
        ("normal UDP", [(h3, "iperf -c " + V + " -u -b 1M -t 15")], 20),
        ("SYN flood 1000/s", [(h4, "hping3 -q -S -p 80 -i u1000 -c 15000 " + V)], 20),
        ("SYN flood 200/s", [(h4, "hping3 -q -S -p 80 -i u5000 -c 3000 " + V)], 20),
        ("UDP flood", [(h4, "hping3 -q --udp -p 80 -d 100 -i u1000 -c 15000 " + V)], 20),
        ("mixed TCP + SYN flood", [(h1, "iperf -c " + V + " -t 15"),
                                   (h4, "hping3 -q -S -p 80 -i u1000 -c 15000 " + V)], 25),
    ]
    for name, jobs, wait in phases:
        print(">>", name)
        for h, c in jobs:
            bg(h, c)
        time.sleep(wait)
    time.sleep(5)
finally:
    net.stop()
