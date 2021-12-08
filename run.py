import os
import time

join_request = 'xterm -hold -title "Peer 15" -e "python3 p2p.py join 15 4 30"'
wait_time = 40

os.system('./init_python.sh')
time.sleep(wait_time)
os.system(join_request)

