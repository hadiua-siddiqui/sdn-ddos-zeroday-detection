#!/bin/bash
MODE=${1:-full}
cd /home/hadiya/fyp
sudo -v || exit 1
export BLOCK=1
grep -q xgb_mininet4 predictor_server.py || { echo "predictor_server.py mein xgb_mininet4 nahi"; exit 1; }
sudo mn -c > /dev/null 2>&1
pkill -f predictor_server.py 2>/dev/null
pkill -f ryu-manager 2>/dev/null
sleep 1
RUN=demo_logs/$(date +%Y%m%d_%H%M%S)
mkdir -p $RUN
source fyp-env/bin/activate
python3 predictor_server.py > $RUN/predictor.log 2>&1 &
PRED=$!
deactivate
source ryu39-env/bin/activate
ryu-manager ryu_apps/auto_blocker.py > $RUN/ryu.log 2>&1 &
RYU=$!
deactivate
for i in $(seq 1 15); do
  python3 -c "import socket; s=socket.socket(); s.settimeout(0.5); s.connect(('127.0.0.1',5001))" 2>/dev/null && break
  sleep 1
done
sleep 4
if ! kill -0 $PRED 2>/dev/null; then echo "predictor start nahi hua:"; tail -n 10 $RUN/predictor.log; exit 1; fi
if ! kill -0 $RYU 2>/dev/null; then echo "Ryu start nahi hua:"; tail -n 15 $RUN/ryu.log; kill $PRED; exit 1; fi
EV=$(ls -t block_events_*.csv | head -1)
sudo /usr/bin/python3 -B run_demo.py $RUN $MODE $EV
kill $RYU $PRED 2>/dev/null
echo "logs: $RUN"
