import os, sys, time
pid, out = int(sys.argv[1]), sys.argv[2]
tck = os.sysconf("SC_CLK_TCK")


def read():
    with open("/proc/%d/stat" % pid) as f:
        p = f.read().rsplit(")", 1)[1].split()
    cpu = (int(p[11]) + int(p[12])) / float(tck)
    rss = 0.0
    with open("/proc/%d/status" % pid) as f:
        for line in f:
            if line.startswith("VmRSS"):
                rss = int(line.split()[1]) / 1024.0
    return cpu, rss


with open(out, "w") as o:
    o.write("time,cpu_pct,rss_mb\n")
    try:
        c0, _ = read()
        t0 = time.time()
        while True:
            time.sleep(1)
            c1, rss = read()
            t1 = time.time()
            o.write("%.2f,%.1f,%.1f\n" % (t1, 100.0 * (c1 - c0) / (t1 - t0), rss))
            o.flush()
            c0, t0 = c1, t1
    except (FileNotFoundError, ProcessLookupError):
        pass
