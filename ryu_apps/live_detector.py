import time, json, urllib.request
from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.lib import hub

PREDICTOR = "http://127.0.0.1:5001"
WATCH_DPID = 2     # training data s2 (dpid 2) se bana tha
POLL_SEC = 1
LOG = "/home/hadiya/fyp/live_decisions_%s.csv" % time.strftime("%Y%m%d_%H%M%S")


class LiveDetector(simple_switch_13.SimpleSwitch13):
    def __init__(self, *args, **kwargs):
        super(LiveDetector, self).__init__(*args, **kwargs)
        self.datapaths = {}
        self.prev = {}
        self.warned = False
        with open(LOG, "w") as f:
            f.write("time,in_port,eth_src,eth_dst,pkts_per_s,bytes_per_s,avg_pkt_size,prob,pred,rtt_ms\n")
        hub.spawn(self._monitor)

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
        n_att = 0
        with open(LOG, "a") as f:
            for key, r, p, y in zip(meta, rows, res["probs"], res["preds"]):
                f.write("%.2f,%s,%s,%s,%.1f,%.1f,%.1f,%.3f,%d,%.1f\n" % (
                    now, key[0], key[1], key[2], r[0], r[1], r[2], p, y, rtt))
                if y:
                    n_att += 1
                    self.logger.info("ATTACK? %s -> %s  %.0f pkt/s  prob=%.2f",
                                     key[1], key[2], r[0], p)
        self.logger.info("flows=%d flagged=%d predictor=%.1f ms", len(rows), n_att, rtt)
