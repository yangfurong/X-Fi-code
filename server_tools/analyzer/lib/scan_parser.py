#!/usr/bin/env python3

import argparse
import functools
import os, re
from multiprocessing import Pool
from .logger import logger
from datetime import datetime
from enum import Enum

#import logging
#logging.basicConfig(level=logging.INFO)


TIME_FMT = "%Y-%m-%dT%H:%M:%S.%f%z"

class WiFiVersion(Enum):
    G = "802.11g"
    N = "802.11n"
    AC = "802.11ac"
    O = "others"

class AP(object):

    def __init__(self, time=None, ssid=None, channel=None, freq=None, bssid=None, rates=None, e_rates=None, signal=None, wifi_version=None):
        self.time = time
        self.ssid = ssid
        self.bssid = bssid
        self.channel = channel
        self.freq = freq
        self.rates = rates
        self.e_rates = e_rates
        self.signal = signal
        self.ht = None
        self.vht = None
        self.wifi_version = wifi_version

    def is_complete(self):
        return self.time != None and self.ssid and self.bssid and self.channel and self.freq and self.rates and self.signal

    def to_list(self):
        return [self.time, self.ssid, self.channel, self.freq, self.bssid, self.rates, self.e_rates, self.signal, self.wifi_version]

    def __str__(self):
        return str(self.to_list())

class ScanParser(object):

    def __init__(self, log_dir, ssid):
        self._log_dir = log_dir
        self._ssid = ssid

    def process_one(self, scan_log):
        bss_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+BSS\s+([a-zA-Z0-9]{2}(:[a-zA-Z0-9]{2}){5}).*$")
        freq_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+freq:\s+(\d+).*$")
        ssid_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+SSID:\s(.*)$")
        channel_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+DS\sParameter\sset:\s+channel\s+(\d+).*$")
        signal_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+signal:\s+([-0-9.]+).*$")
        rates_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+Supported\srates:\s+([\s0-9*.]+).*$")
        e_rates_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+Extended\ssupported\srates:\s+([\s0-9*.]+).*$")
        ht_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+HT\scapabilities:.*$")
        vht_re = re.compile(r"^([^\s]+)\s+[^:]+:\s+VHT\scapabilities:.*$")
        ap_list = []
        ap = None
        logger.info("{} {} started".format(scan_log, self._ssid))
        with open(scan_log, "r") as log_f:
            for str_line in log_f:
                m = bss_re.match(str_line)
                if m:
                    if ap and ap.is_complete():
                        if ap.vht:
                            ap.wifi_version = WiFiVersion.AC
                        elif ap.ht:
                            ap.wifi_version = WiFiVersion.N
                        else:
                            ap.wifi_version = WiFiVersion.O
                        if self._ssid == ap.ssid:
                            ap_list.append(ap)
                    ap = AP()
                    ts, mac = m.group(1, 2)
                    ap.time = datetime.strptime(ts, TIME_FMT).timestamp()
                    ap.bssid = mac
                else:
                    m = freq_re.match(str_line)
                    if m:
                        ts, freq = m.group(1, 2)
                        if ap:
                            ap.freq = int(freq)
                    else:
                        m = ssid_re.match(str_line)
                        if m:
                            ts, ssid = m.group(1, 2)
                            if ap:
                                ap.ssid = ssid
                        else:
                            m = channel_re.match(str_line)
                            if m:
                                ts, ch = m.group(1, 2)
                                if ap:
                                    ap.channel = int(ch)
                            else:
                                m = signal_re.match(str_line)
                                if m:
                                    ts, sig = m.group(1, 2)
                                    if ap:
                                        ap.signal = float(sig)
                                else:
                                    m = rates_re.match(str_line)
                                    if m:
                                        ts, rates = m.group(1, 2)
                                        if ap:
                                            ap.rates = [float(x.rstrip("*")) for x in rates.split()]
                                    else:
                                        m = e_rates_re.match(str_line)
                                        if m:
                                            ts, e_rates = m.group(1, 2)
                                            if ap:
                                                ap.e_rates = [float(x.rstrip("*")) for x in e_rates.split()]
                                        else:
                                            m = ht_re.match(str_line)
                                            if m:
                                                if ap:
                                                    ap.ht = True
                                            else:
                                                m = vht_re.match(str_line)
                                                if m:
                                                    if ap:
                                                        ap.vht = True
            # don't use the last one, as you never know if the log is complete or not
            #if ap and ap.is_complete():
            #    if ap.vht:
            #        ap.wifi_version = WiFiVersion.AC
            #    elif ap.ht:
            #        ap.wifi_version = WiFiVersion.N
            #    else:
            #        ap.wifi_version = WiFiVersion.O
            #    if self._ssid == ap.ssid:
            #        ap_list.append(ap)

            logger.info("{} {} finished".format(scan_log, self._ssid))
            return ap_list

    def parse(self):
        logger.info("ScanParser: {} {} started".format(self._log_dir, self._ssid))
        scan_dir = self._log_dir
        arg_list = [os.path.join(scan_dir, x) for x in os.listdir(scan_dir)]
        mp = Pool()
        ap_lists = mp.map(self.process_one, arg_list, 1)
        mp.close()
        mp.join()
        ap_list = functools.reduce(lambda x, y: x+y, ap_lists)
        return ap_list

if __name__ == "__main__":
    import sys
    parser = ScanParser(sys.argv[1], sys.argv[2])
    ap_list = parser.parse()
    for ap in ap_list:
        print(ap)
