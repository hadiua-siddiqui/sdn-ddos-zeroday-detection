#!/bin/bash
cd /home/hadiya/fyp
sudo -v || exit 1
for i in 1 2 3 4 5; do
  echo "=== round $i: blocker ==="
  ./measure.sh blocker
  echo "=== round $i: baseline ==="
  ./measure.sh baseline
done
