#!/usr/bin/env python3

import re, sys
from .logger import logger
from enum import Enum

class _InfoBlk(object):

    def __init__(self, T_dhcp_s, T_dhcp_e, T_ip_s, T_ip_e, ip, ip_prefix, gw, intf, dhcp_server=None, dns_servers=None):
        """
        @T_dhcp_s: the time when carfi gets carrier and starts DHCP procedure.
        @T_dhcp_e: the time when carfi finishes the DHCP procedure.
        @T_ip_s: the time when carfi get address for the interface. It equals to T_dhcp_e
        @I_ip_e: the time when carfi lose address and carrier.
        """
        self.T_dhcp_s = T_dhcp_s
        self.T_dhcp_e = T_dhcp_e
        self.T_ip_s = T_ip_s
        self.T_ip_e = T_ip_e
        self.ip = ip
        self.ip_prefix = ip_prefix
        self.gw = gw
        self.intf = intf
        self.dhcp_server = dhcp_server
        self.dns_servers = dns_servers

    def to_list(self):
        return [self.intf, self.ip, self.ip_prefix, self.gw, self.T_dhcp_s, self.T_dhcp_e, self.T_ip_s, self.T_ip_e, self.dhcp_server, self.dns_servers]

    def __str__(self):
        return str(self.to_list())

class _RMState(Enum):
    GAINED_CARRIER = 0
    GET_IP = 1
    LOST_CARRIER = 2

class RMParser(object):

    def __init__(self, rm_log, intf_list):
        self._rm_log = rm_log
        self._intf_list = intf_list

    def parse(self):
        """
        @rm_log: the path of roamingd.log
        @intf_list: the interfaces used by roamingd
        """
        with open(self._rm_log, "r") as f:
            logger.info("[RMParser]: open {} roamingd log".format(self._rm_log))
            #ts, nic
            dhcp_start_re = re.compile(r"^([\.0-9]+):\s*([0-9a-zA-Z_]+):\s*Acquiring\s*DHCPv4\s*lease\s*$")
            #ts, nic, ip, gw
            ip_get_re = re.compile(r"^([\.0-9]+):\s*([0-9a-zA-Z_]+):\s*DHCPv4\s*address\s*([\.0-9]+)/(\d+)\s*via\s*([\.0-9]+)\s*$")
            #dhcp server
            dhcp_server_re = re.compile(r"^([\.0-9]+):\s*([0-9a-zA-Z_]+):\s*DHCPv4\s*Server:\s*([.0-9]+)\s*$")
            #dns server
            dns_server_re = re.compile(r"^([\.0-9]+):\s*([0-9a-zA-Z_]+):\s*DNSv4\s*Server\s+\d+:\s*([\.0-9]+)\s*$")
            #ts, nic
            ip_lost_re = re.compile(r"^([\.0-9]+):\s*([0-9a-zA-Z_]+):\s*Lost\s*carrier\s*$")
            intf_results = {intf:{"state":_RMState.LOST_CARRIER, "info_blk_list":[], "info_blk":{}} for intf in self._intf_list}
            for row in f:
                dhcp_match = dhcp_start_re.match(row)
                if dhcp_match:
                    ts = float(dhcp_match.group(1))
                    intf = dhcp_match.group(2)
                    #ignore unrelated data
                    if intf not in self._intf_list:
                        continue
                    assert intf_results[intf]["state"] == _RMState.LOST_CARRIER
                    intf_results[intf]["state"] = _RMState.GAINED_CARRIER
                    intf_results[intf]["info_blk"]["T_dhcp_s"] = ts
                else:
                    ip_match = ip_get_re.match(row)
                    if ip_match:
                        ts = float(ip_match.group(1))
                        intf = ip_match.group(2)
                        if intf not in self._intf_list:
                            continue
                        assert intf_results[intf]["state"] == _RMState.GAINED_CARRIER
                        intf_results[intf]["state"] = _RMState.GET_IP
                        intf_results[intf]["info_blk"]["T_dhcp_e"] = ts
                        intf_results[intf]["info_blk"]["T_ip_s"] = ts
                        intf_results[intf]["info_blk"]["ip"] = ip_match.group(3)
                        intf_results[intf]["info_blk"]["ip_prefix"] = ip_match.group(4)
                        intf_results[intf]["info_blk"]["gw"] = ip_match.group(5)
                    else:
                        ip_lost_match = ip_lost_re.match(row)
                        if ip_lost_match:
                            ts = float(ip_lost_match.group(1))
                            intf = ip_lost_match.group(2)
                            if intf not in self._intf_list:
                                continue
                            intf_results[intf]["info_blk"]["T_ip_e"] = ts
                            intf_results[intf]["info_blk"]["intf"] = intf

                            #If CarFi could not be assigned with an IP address within the L2 connected period,
                            #we set the non-existing fields of this item with 0 to mark it as an outlier.
                            if intf_results[intf]["state"] != _RMState.GET_IP:
                                #logger.debug(intf_results[intf]["info_blk"])
                                intf_results[intf]["info_blk"]["T_dhcp_e"] = None
                                intf_results[intf]["info_blk"]["T_ip_s"] = None
                                intf_results[intf]["info_blk"]["ip"] = None
                                intf_results[intf]["info_blk"]["ip_prefix"] = None
                                intf_results[intf]["info_blk"]["gw"] = None

                            intf_results[intf]["info_blk_list"].append(_InfoBlk(**intf_results[intf]["info_blk"]))
                            intf_results[intf]["info_blk"] = {}
                            intf_results[intf]["state"] = _RMState.LOST_CARRIER
                        else:
                            dhcp_server_m = dhcp_server_re.match(row)
                            if dhcp_server_m:
                                ts, intf, server_ip = dhcp_server_m.group(1, 2, 3)
                                ts = float(ts)
                                if intf not in self._intf_list:
                                    continue
                                intf_results[intf]["info_blk"]["dhcp_server"] = server_ip
                            else:
                                dns_server_m = dns_server_re.match(row)
                                if dns_server_m:
                                    ts, intf, dns_ip = dns_server_m.group(1, 2, 3)
                                    ts = float(ts)
                                    if intf not in self._intf_list:
                                        continue
                                    if "dns_servers" in intf_results[intf]["info_blk"]:
                                        intf_results[intf]["info_blk"]["dns_servers"].append(dns_ip)
                                    else:
                                        intf_results[intf]["info_blk"]["dns_servers"] = [dns_ip]



            intf_results = {intf:v["info_blk_list"] for intf, v in intf_results.items()}
            logger.info("[RMParser]: #{} results are extracted".format(sum([len(v) for k, v in intf_results.items()])))
            return intf_results

if __name__ == "__main__":
    parser = RMParser(sys.argv[1], ["wlp4s0"])
    for k, v in parser.parse().items():
        for e in v:
            print("{}: {}".format(k, e))
