#!/usr/bin/env python3

import re
import subprocess
import sys
import time

timestamp_re = re.compile('^\[(\d+\.\d+)\]')
icmp_seq_re = re.compile('icmp_seq=(\d+)')
received_re = re.compile('bytes from')
lost_re = re.compile('no answer')

def convert_time(t):
    return '{:2.0f}\'{:2.0f}"'.format(t // 60, round(t % 60))

def print_status(status, total, connected):
    print('{:16s}total time {} / connected {} / disconnected {}'
          .format(status, convert_time(total), convert_time(connected),
                  convert_time(max(0, total - connected))))

connected_time = 0
start_time = time.monotonic()
ping = subprocess.Popen(['ping', '-D', '-i 0.1', '-n', '-O'] + sys.argv[1:],
                        bufsize=1, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        universal_newlines=True)

try:
    connected = True
    last_second = []

    while True:
        line = ping.stdout.readline()
        if not line:
            # EOF
            break

        m = timestamp_re.search(line)
        if not m:
            # ignore lines without timestamp
            continue
        ts = float(m.group(1))

        if received_re.search(line):
            last_second.append(True)
        elif lost_re.search(line):
            last_second.append(False)
        else:
            # huh?
            continue
        if len(last_second) > 10:
            del last_second[0]

        status = None
        if connected and last_second.count(False) > 5:
            connected = False
            status = 'Disconnected'
        elif not connected and last_second.count(False) <= 5:
            connected = True
            status = 'Connected'

        if connected:
            connected_time += 0.1
        if status:
            print_status(status, time.monotonic() - start_time, connected_time)

except KeyboardInterrupt:
    # print ping stats
    (out, _) = ping.communicate()
    if out:
        print(out)

print_status('Finished', time.monotonic() - start_time, connected_time)
