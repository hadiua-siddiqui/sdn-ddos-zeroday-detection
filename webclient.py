import sys, time, urllib.request
host, gap = sys.argv[1], float(sys.argv[2])
while True:
    try:
        urllib.request.urlopen("http://%s/" % host, timeout=2).read()
    except Exception:
        pass
    time.sleep(gap)
