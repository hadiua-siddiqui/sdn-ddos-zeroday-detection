import time
from ryu.app import simple_switch_13
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, DEAD_DISPATCHER, set_ev_cls
from ryu.lib import hub

LOG = "/home/hadiya/fyp/flow_stats_%s.csv" % time.strftime("%Y%m%d_%H%M%S")

class FlowMonitor(simple_switch_13.SimpleSwitch13):
    def __init__(self, *args, **kwargs):
        super(FlowMonitor, self).__init__(*args, **kwargs)
        self.datapaths = {}
        with open(LOG, "w") as f:
            f.write("time,dpid,in_port,eth_src,eth_dst,duration_s,packets,bytes\n")
        self.monitor_thread = hub.spawn(self._monitor)

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
            hub.sleep(1)

    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def _flow_stats_reply(self, ev):
        now = time.time()
        dpid = ev.msg.datapath.id
        rows = []
        for s in ev.msg.body:
            if s.priority == 0:
                continue
            m = s.match
            rows.append("%.1f,%d,%s,%s,%s,%d,%d,%d" % (
                now, dpid, m.get("in_port", "-"), m.get("eth_src", "-"),
                m.get("eth_dst", "-"), s.duration_sec, s.packet_count, s.byte_count))
        if rows:
            with open(LOG, "a") as f:
                f.write("\n".join(rows) + "\n")
            self.logger.info("dpid %016x: %d flows logged", dpid, len(rows))
