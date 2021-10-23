#!/usr/bin/env python3

import argparse
import functools
import os, re
from multiprocessing import Pool
from .logger import logger
from datetime import datetime
from enum import Enum

class Link(object):

    def __init__(self, time=None, intf=None, signal=None):
        self.time = time
        self.intf = intf
        self.signal = signal

    def is_complete(self):
        return self.time != None and self.intf != None and self.signal != None

    def to_list(self):
        return [self.time, self.intf, self.signal]

    def __str__(self):
        return str(self.to_list())

class LinkParser(object):

    def __init__(self, log_file, intfs):
        self._log_file = log_file
        self._intfs = intfs

    def parse(self):
        logger.info("LinkParser: {} started".format(self._log_file))
        if_re = re.compile(r"^([0-9.]+)\s+(\w+)\s+IEEE\s+[0-9a-zA-Z.]+\s+ESSID:.*$")
        ss_re = re.compile(r"^([0-9.]+)\s+Link\s+Quality=\d+/\d+\s+Signal\s+level=([-0-9.]+)\s+dBm.*$")
        with open(self._log_file, "r") as log_f:
            link = Link()
            links = {intf:[] for intf in self._intfs}
            for log_line in log_f:
                m = if_re.match(log_line)
                if m:
                    ts, intf = m.group(1, 2)
                    link.time = float(ts)
                    link.intf = intf
                else:
                    m = ss_re.match(log_line)
                    if m:
                        ts, signal = m.group(1, 2)
                        signal = float(signal)
                        link.signal = signal
                        links[link.intf].append(link)
                        link = Link()
            return links

if __name__ == "__main__":
    import sys
    parser = LinkParser(sys.argv[1])
    link_list = parser.parse()
    for ap in link_list:
        print(ap)
