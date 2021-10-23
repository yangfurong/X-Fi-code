#!/usr/bin/env python3
import os, sys
import dpkt
import dpkt.tcp
import socket
import math, struct
import subprocess, csv
import pandas as pd
from io import StringIO
from multiprocessing import Pool
from enum import Enum
from .logger import logger

class FlowType(Enum):
    UPLOAD = "upload"
    DOWNLOAD = "download"

def _pool_func(path):
    tcp_parser = _TCPSingleParser(path)
    res = tcp_parser.parse()
    return tcp_parser if res else None

class TCPParser(object):

    #@path: the path of tester.data
    def __init__(self, path, intfs, cpu):
        self.path = path
        self.intfs = intfs
        self._cpu = cpu

    def parse(self):
        results = {}
        mp = Pool(self._cpu)
        logger.info("TCP Parser is working...")
        for intf in self.intfs:
            intf_subdir = os.path.join(self.path, intf)
            assert os.path.isdir(intf_subdir)
            test_path_list = (os.path.join(intf_subdir, test) for test in os.listdir(intf_subdir))
            results[intf] = mp.map(_pool_func, test_path_list, 1)
            results[intf] = list(filter(lambda x:x != None, results[intf]))
            #sort by starting time
            results[intf].sort(key=lambda x:x.T_s_app)
        mp.close()
        mp.join()
        logger.info("TCP Parser has finished jobs.")
        return results

class _FlowStat(object):

    def __init__(self):
        self.acked_bytes = 0
        self.first_seq = None
        self.last_ack = None
        self.last_ts = None

class _TCPSingleParser(object):

    def __init__(self, path):
        self._profile = os.path.join(path, "tcp_tester.profile")
        self._pcap = os.path.join(path, "flows.pcap")
        self.local_id = int(os.path.split(path)[1])

    def _parsing_profile(self):
        with open(self._profile, "r") as f:
            self.T_s_app = float(f.readline().strip())
            self.T_e_app = float(f.readline().strip())
            self.type = FlowType(f.readline().strip())
            self.cc = f.readline().strip()
            self.total_bytes_app = int(f.readline().strip())
            #Mbits/sec
            self.gp_app = float(self.total_bytes_app) * 8 / (self.T_e_app - self.T_s_app) / 1e6
            self.flow_nb = int(f.readline().strip())
            self.flows = {}
            for i in range(self.flow_nb):
                #cip, cport, sip, sport
                cip, cport, sip, sport = tuple(f.readline().strip().split(" "))
                cport = int(cport)
                sport = int(sport)
                cip = socket.inet_aton(cip)
                sip = socket.inet_aton(sip)
                #0 = c->s, 1 = s->c
                self.flows[(cip, cport, sip, sport)] = (_FlowStat(), _FlowStat())

    def _parsing_pcap(self):
        self.total_bytes_pcap = None
        self.T_s_pcap = None
        self.T_e_pcap = None
        tcptrace_p = subprocess.Popen("tcptrace -nl --csv {}".format(self._pcap), shell=True, stdout=subprocess.PIPE)
        tcptrace_out = tcptrace_p.stdout.read()
        tcptrace_io = StringIO()
        tcptrace_io.write(tcptrace_out.decode("utf-8"))
        tcptrace_io.seek(0)
        pkt_total = 0
        pkt_retrans = 0
        try:
            tcptrace_csv = pd.read_csv(tcptrace_io, skiprows=list(range(0, 8))+[9])
            data = tcptrace_csv[["host_a", "host_b", "port_a", "port_b", "total_packets_a2b", "total_packets_b2a", "actual_data_pkts_a2b", "actual_data_pkts_b2a", "rexmt_data_pkts_a2b", "rexmt_data_pkts_b2a"]]
            for row_id in range(0, len(data.index)):
                row = data.loc[row_id]
                direct = None
                #check if the row is in self.flows
                for flow in self.flows.keys():
                    cip, cport, sip, sport = flow
                    cip = socket.inet_ntoa(cip)
                    sip = socket.inet_ntoa(sip)
                    #a:client b:server
                    if row["host_a"] == cip and row["host_b"] == sip and row["port_a"] == cport and row["port_b"] == sport:
                        if self.type == FlowType.UPLOAD:
                            direct = "a2b"
                        else:
                            direct = "b2a"
                        break
                    #a:server b:client
                    elif row["host_a"] == sip and row["host_b"] == cip and row["port_a"] == sport and row["port_b"] == cport:
                        if self.type == FlowType.UPLOAD:
                            direct = "b2a"
                        else:
                            direct = "a2b"
                        break
                if direct != None:
                    pkt_total += row["actual_data_pkts_"+direct]
                    pkt_retrans += row["rexmt_data_pkts_"+direct]
        except:
            logger.info("{} is an empty pcap.")
        
        self.pkt_total = float(pkt_total)
        self.pkt_rxmt = float(pkt_retrans)
        if self.pkt_total == 0:
            self.pkt_loss_rate = None
        else:
            self.pkt_loss_rate = self.pkt_rxmt / self.pkt_total
        with open(self._pcap, "rb") as f:
            pcap = dpkt.pcap.Reader(f)
            pkt_id = 0
            for ts, buf in pcap:
                eth = dpkt.ethernet.Ethernet(buf)
                ip = eth.data
                tcp = ip.data
                pkt_id += 1
                #skip pkts whose ACK flag is not set
                if not isinstance(tcp, dpkt.tcp.TCP):
                    logger.info("{} {} {}".format(type(tcp), pkt_id, ts))
                    logger.info(self._pcap)
                    continue
                if (tcp.flags & dpkt.tcp.TH_ACK) == 0:
                    continue

                #client to server direction
                flow_key1 = (ip.src, tcp.sport, ip.dst, tcp.dport)
                #server to client direction
                flow_key2 = (ip.dst, tcp.dport, ip.src, tcp.sport)
                from_dir = None
                to_dir = None
                flow_stat = None

                if flow_key1 in self.flows:
                    from_dir = 0
                    to_dir = 1
                    flow_stat = self.flows[flow_key1]
                    #first non-SYN packet from client
                    if self.T_s_pcap == None and (tcp.flags & dpkt.tcp.TH_SYN) == 0:
                        self.T_s_pcap = ts
                elif flow_key2 in self.flows:
                    from_dir = 1
                    to_dir = 0
                    flow_stat = self.flows[flow_key2]
                    #first ack packet from server
                    if self.T_s_pcap == None:
                        self.T_s_pcap = ts
                else:
                    #skip unknown pkts
                    logger.debug("an unknown flow appears {}/{}".format(flow_key1, flow_key2))
                    continue

                self.T_e_pcap = ts

                if flow_stat[from_dir].first_seq == None:
                    flow_stat[from_dir].first_seq = tcp.seq
                    flow_stat[from_dir].acked_bytes = 0
                    flow_stat[to_dir].last_ack = tcp.ack
                else:
                    #to avoid sequence number to get wrapped
                    ack_gap = (tcp.ack - flow_stat[to_dir].last_ack + (1<<32)) & 0xffffffff
                    if ack_gap != 0:
                        #it should not be very large, otherwise it is a disordered ack and we just discard it
                        #we use 2GB here
                        if ack_gap < 0x80000000:
                            flow_stat[to_dir].last_ack = tcp.ack
                            flow_stat[to_dir].acked_bytes += ack_gap
                        else:
                            logger.debug("a disordered ack is found: last_ack ({}), tcp.ack ({})".format(flow_stat[to_dir].last_ack, tcp.ack))
        selector = None
        if self.type == FlowType.UPLOAD:
            selector = 0
        else:
            selector = 1
        self.total_bytes_pcap = 0
        for k, v in self.flows.items():
            self.total_bytes_pcap += v[selector].acked_bytes
        self.gp_pcap = float(self.total_bytes_pcap) * 8 / (self.T_e_app - self.T_s_app) / 1e6
        #_FlowStats are no more useful
        _flows = []
        for flow in self.flows.keys():
            _flows.append((socket.inet_ntoa(flow[0]), flow[1], socket.inet_ntoa(flow[2]), flow[3]))
        self.flows = _flows

    def _to_list(self):
        return [self.T_s_app, self.T_e_app, self.type, self.cc, self.flow_nb, self.flows, self.total_bytes_app, self.total_bytes_pcap, self.gp_app, self.gp_pcap, self.local_id, self.T_s_pcap, self.T_e_pcap, self.pkt_total, self.pkt_rxmt, self.pkt_loss_rate]

    def __repr__(self):
        return "{} {} {} {} {} {} {} {} {} {} {} {} {} {} {} {}".format(*self._to_list())

    def parse(self):
        if not os.path.isfile(self._profile) or not os.path.isfile(self._pcap):
            return False
        self._parsing_profile()
        self._parsing_pcap()
        return True

if __name__ == '__main__':
    parser = TCPParser(sys.argv[1], ["wlp4s0"], 16)
    for k, v in parser.parse().items():
        for elem in v:
            print(k, " : ", elem)
