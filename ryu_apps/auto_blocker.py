import os, time, json, urllib.request
from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.lib import hub

PREDICTOR = "http://127.0.0.1:5001"
WATCH_DPID = 2            # attacker aur victim s2 (dpid 2) par hain
POLL_SEC = 1
BLOCK_ENABLED = os.environ.get("BLOCK", "1") == "1"
CONSEC = 3                # itne lagatar second attack nikle to block
BLOCK_SEC = 15            # block itni der rahe, phir khud khul jaye
BLOCK_PRIORITY = 100
PROTECTED = {"00:00:00:00:00:05"}    # victim h5 kabhi block nahi hoga
STAMP = time.strftime("%Y%m%d_%H%M%S")
LOG = "/home/hadiya/fyp/live_decisions_%s.csv" % STAMP
EVENTS = "/home/hadiya/fyp/block_events_%s.csv" % STAMP


class AutoBlocker(simple_switch_13.SimpleSwitch13):
    def __init__(self, *args, **kwargs):
        super(AutoBlocker, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.prev = {}
        self.streak = {}
        self.blocked = {}
        self.dropped = {}
        self.warned = False
        with open(LOG, "w") as f:
            f.write("time,in_port,eth_src,eth_dst,pkts_per_s,bytes_per_s,avg_pkt_size,prob,pred,rtt_ms\n")
        with open(EVENTS, "w") as f:
            f.write("time,event,src,detail\n")
        hub.spawn(self._monitor)

    def _event(self, now, name, src, detail):
        with open(EVENTS, "a") as f:
            f.write("%.2f,%s,%s,%s\n" % (now, name, src, detail))

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def _state_change(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
        elif ev.state == DEAD_DISPATCHER:
            self.datapaths.pop(dp.id, None)

    def _monitor(self):
        while True:
            for dp in list(self.datapaths.values()):
                dp.send_msg(dp.ofproto_parser.OFPFlowStatsRequest(dp))
            hub.sleep(POLL_SEC)

    def _predict(self, rows):
        req = urllib.request.Request(
            PREDICTOR, data=json.dumps({"rows": rows}).encode(),
            headers={"Content-Type": "application/json"})
        return json.loads(urllib.request.urlopen(req, timeout=1).read())

    def _block(self, src, now):
        for dp in (list(self.datapaths.values()) if BLOCK_ENABLED else []):
            parser = dp.ofproto_parser
            match = parser.OFPMatch(eth_src=src)
            dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=BLOCK_PRIORITY,
                                          match=match, instructions=[],
                                          hard_timeout=BLOCK_SEC))
        self.blocked[src] = now + BLOCK_SEC
        self._event(now, "BLOCK" if BLOCK_ENABLED else "WOULD_BLOCK", src, "streak=%d" % self.streak.get(src, 0))
        self.logger.warning("BLOCKED %s for %d s", src, BLOCK_SEC)

    def _update(self, flagged, now):
        for src in list(self.blocked):
            if now >= self.blocked[src] + POLL_SEC:
                n = self.dropped.get(src, 0)
                self._event(now, "UNBLOCK", src, "dropped=%d" % n)
                self.logger.info("UNBLOCK %s (dropped %d packets)", src, n)
                del self.blocked[src]
                self.dropped.pop(src, None)
                self.streak[src] = 0
        for src in flagged:
            if src in self.blocked:
                continue
            self.streak[src] = self.streak.get(src, 0) + 1
            if self.streak[src] >= CONSEC:
                self._block(src, now)
        for src in list(self.streak):
            if src not in flagged and src not in self.blocked:
                self.streak[src] = 0

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply(self, ev):
        dp = ev.msg.datapath
        if dp.id != WATCH_DPID:
            return
        now = time.time()
        rows, meta = [], []
        for s in ev.msg.body:
            if s.priority == 0:
                continue
            m = s.match
            if s.priority >= BLOCK_PRIORITY:
                self.dropped[m.get("eth_src")] = s.packet_count
                continue
            key = (m.get("in_port"), m.get("eth_src"), m.get("eth_dst"))
            old = self.prev.get(key)
            self.prev[key] = (now, s.packet_count, s.byte_count)
            if old is None:
                continue
            dt = now - old[0]
            dpk = s.packet_count - old[1]
            dby = s.byte_count - old[2]
            if dt <= 0 or dpk <= 0 or dby < 0:
                continue
            rows.append([dpk / dt, dby / dt, dby / float(dpk)])
            meta.append(key)
        if not rows:
            self._update(set(), now)
            return
        t0 = time.time()
        try:
            res = self._predict(rows)
        except Exception as e:
            if not self.warned:
                self.logger.warning("predictor se jawab nahi aaya: %s", e)
                self.warned = True
            return
        self.warned = False
        rtt = (time.time() - t0) * 1000.0
        flagged = set()
        with open(LOG, "a") as f:
            for key, r, p, y in zip(meta, rows, res["probs"], res["preds"]):
                f.write("%.2f,%s,%s,%s,%.1f,%.1f,%.1f,%.3f,%d,%.1f\n" % (
                    now, key[0], key[1], key[2], r[0], r[1], r[2], p, y, rtt))
                if y and key[1] not in PROTECTED:
                    flagged.add(key[1])
        self._update(flagged, now)
        self.logger.info("flows=%d flagged_src=%s blocked=%s",
                         len(rows), sorted(flagged), sorted(self.blocked))
