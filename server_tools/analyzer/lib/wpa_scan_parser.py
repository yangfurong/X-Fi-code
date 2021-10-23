#!/usr/bin/env python3

import re, sys
from enum import Enum
from .logger import logger
from .scan_parser import WiFiVersion

class WPAScanObj(object):

    def __init__(self, time, intf, mac, ssid, level, freq, g, n, ac):
        self.time = time
        self.intf = intf
        self.mac = mac
        self.ssid = ssid 
        self.level = level
        self.freq = freq
        if ac:
            self.wifi_type = WiFiVersion.AC
        elif n:
            self.wifi_type = WiFiVersion.N
        elif g:
            self.wifi_type = WiFiVersion.G
        else:
            self.wifi_type = WiFiVersion.O

    def __str__(self):
        return "{} {} {} {} {} {} {}".format(self.time, self.intf, self.mac, self.ssid, self.level, self.freq, self.wifi_type)

class WPAScanParser(object):

    def __init__(self, wpa_log, intf_list):
        self._wpa_log = wpa_log
        self._intf_list = intf_list

    def parse(self):
        with open(self._wpa_log, "r") as f:
            logger.info("[WPA Scan] Parsing {}".format(self._wpa_log))
            scan_ap_re = re.compile(r"^([\.0-9]+):\s*([a-zA-Z0-9_]+):\s*\d+:\s*([a-zA-Z0-9:]+)\s*ssid='([^']*)'.*level=([-0-9]+).*freq=(\d+).*11g=([a-z]+).*11n=([a-z]+).*11ac=([a-z]+).*$")
            end_tag = re.compile(r"^([\.0-9]+):\s*([a-zA-Z0-9_]+):\s*\*\*\*\*\*\*\*\*\*\*\*\*\*\s*$")
            scan_ap_dict = {intf:[] for intf in self._intf_list}
            f_lines = f.readlines()
            for idx, row in enumerate(f_lines):
                match = scan_ap_re.match(row)
                if match != None:
                    if idx+1 < len(f_lines):
                        end_tag_m = end_tag.match(f_lines[idx+1])
                        #a end tag, skip it
                        if end_tag_m != None:
                            continue
                    time, intf, mac, ssid, level, freq, g, n, ac = match.groups()
                    scan_ap_dict[intf].append(WPAScanObj(time, intf, mac, ssid, level, freq, g, n, ac))
        return scan_ap_dict
                

if __name__ == "__main__":
    wpa = WPAScanParser(sys.argv[1], ["wlp4s0"])
    for k, y in wpa.parse().items():
        for blk in y:
            print (k, ":", blk)

