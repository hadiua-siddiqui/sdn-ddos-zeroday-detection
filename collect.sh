#!/bin/bash
SET=$1
cd /home/hadiya/fyp
sudo mn -c > /dev/null 2>&1
source ryu39-env/bin/activate
ryu-manager ryu_apps/flow_monitor.py > /tmp/ryu_collect.log 2>&1 &
RYU=$!
deactivate
sleep 6
if ! kill -0 $RYU 2>/dev/null; then
  echo "Ryu start nahi hua:"; tail -n 15 /tmp/ryu_collect.log; exit 1
fi
sudo /usr/bin/python3 -B run_scenarios5.py $SET
kill $RYU 2>/dev/null
sleep 2
source fyp-env/bin/activate
f=$(ls -t flow_stats_2*.csv | head -1); d=$(ls -t runlogs | head -1)
echo "flows: $f | run: $d"
python3 build_dataset2.py $f runlogs/$d/phases.csv
