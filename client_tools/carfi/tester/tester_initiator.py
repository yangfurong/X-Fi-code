#!/usr/bin/env python3
import argparse, json
import os, sys
import netifaces
import logging
import signal, time, random
import shlex
from subprocess import Popen, STDOUT
from multiprocessing import Process
from enum import Enum

logging.basicConfig(level=logging.INFO)
POLLING_INTERVAL = 0.01 #s
TCPDUMP_WAIT = 0.0001

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", required=True, help="a configuration file for initiator")
parser.add_argument("-b", "--bin_dir", required=True, help="the folder where the tester binaries are located in")
parser.add_argument("-d", "--data_dir", required=True, help="path of the folder to keep all data generated by this program")
parser.add_argument("-i", "--interval", default=POLLING_INTERVAL, help="the gap between two successive pollings on an interface")
args = parser.parse_args()

class _FlowType(Enum):
    UPLOAD = 0
    DOWNLOAD = 1

class _IntfPolling(Process):

    def __init__(self, intf, tcp_args, data_dir, bin_dir, p_interval):
        super().__init__()
        self._intf = intf
        self._data_dir = os.path.join(data_dir, self._intf)
        self._stop_polling = False
        self._p_interval = p_interval
        self._bin_dir = bin_dir

        assert os.path.isdir(self._bin_dir)
        assert not os.path.isdir(self._data_dir)

        self._tcp_args = tcp_args
        self._tcp_tester = None
        self._tcp_dumper = None
        self._tcp_test_id = 0
        self._tcp_bin = os.path.join(self._bin_dir, self._tcp_args["bin_name"])

    def _sig_handler(self, sig, frm):
        self._stop_polling = True
        #Do NOT use logging inside signal handler to avoid reentrant runtime error
        #logging.info("[Interface Polling on {}]: received signal {}. Polling on {} will stop soon.".format(self._intf, sig, self._intf))
        self._stop_tcp_tester()
        #logging.info("[Interface Polling on {}]: polling stoped".format(self._intf))
        exit(0)

    def _launch_tcp_tester(self):
        if not self._tcp_tester:
            data_dir = os.path.join(self._data_dir, "{}".format(self._tcp_test_id))
            self._tcp_test_id += 1

            server = random.choice(self._tcp_args["servers"])
            flow_type = random.choice([_FlowType.UPLOAD, _FlowType.DOWNLOAD])
            port_base = self._tcp_args["ul_port_base"] if flow_type == _FlowType.UPLOAD else self._tcp_args["dl_port_base"]
            cc_idx = random.randrange(len(self._tcp_args["cc_types"]))
            port = port_base + cc_idx
            concurrency = random.choice(self._tcp_args["concurrency"])

            #adjust tc configuration according to cc type
            #by default, the wireless network card is multiqueue NIC
            if self._tcp_args["cc_types"][cc_idx] == "bbr":
                #use fq
                os.system("sysctl -w net.core.default_qdisc=fq; tc qdisc replace dev {} root pfifo_fast; tc qdisc replace dev {} root mq".format(self._intf, self._intf))
            else:
                #use pfifo_fast
                os.system("sysctl -w net.core.default_qdisc=pfifo_fast; tc qdisc replace dev {} root pfifo_fast; tc qdisc replace dev {} root mq".format(self._intf, self._intf))

            #Currently, we launch tcpdump only when the tester is about to start.
            #Hence, we can not assure that tcpdump is started before tester.
            #If tcpdump starts later, we will lose some pkts.
            tester_cmd = shlex.split("{} -s {} -p {} -t {} -c {} -n {} -d {} -i {}".format(self._tcp_bin, server, port, flow_type.value, self._tcp_args["cc_types"][cc_idx], concurrency, data_dir, self._intf))
            dump_cmd = shlex.split("tcpdump -i {} -s 128 -w {} host {} and tcp port {}".format(self._intf, os.path.join(data_dir, "flows.pcap"), server, port))

            os.mkdir(data_dir)
            tcp_tester_log = open(os.path.join(data_dir, "tcp_tester.log"), "w")
            tcp_dumper_log = open(os.path.join(data_dir, "tcp_dumper.log"), "w")

            self._tcp_dumper = Popen(dump_cmd, stdout=tcp_dumper_log, stderr=STDOUT)
            logging.info(dump_cmd)
            time.sleep(TCPDUMP_WAIT)
            self._tcp_tester = Popen(tester_cmd, stdout=tcp_tester_log, stderr=STDOUT)
            logging.info(tester_cmd)

            tcp_tester_log.close()
            tcp_tester_log.close()


    def _stop_tcp_tester(self):
        if self._tcp_tester:
            self._tcp_tester.terminate()
            #to avoid racing condition
            tmp_tcp_tester = self._tcp_tester
            self._tcp_tester = None
            tmp_tcp_tester.wait()
            logging.info("[Interface Polling on {}]: tcp tester stopped".format(self._intf))

        if self._tcp_dumper:
            self._tcp_dumper.terminate()
            tmp_tcp_dumper = self._tcp_dumper
            self._tcp_dumper = None
            tmp_tcp_dumper.wait()
            logging.info("[Interface Polling on {}]: tcpdump stopped".format(self._intf))


    def _intf_has_ip(self):
        intf_ips = netifaces.ifaddresses(self._intf)
        return netifaces.AF_INET in intf_ips

    def run(self):
        signal.signal(signal.SIGINT, self._sig_handler)
        signal.signal(signal.SIGTERM, self._sig_handler)
        os.mkdir(self._data_dir)
        logging.info("[Interface Polling on {}]: polling started".format(self._intf))
        while not self._stop_polling:
            #check interface status
            if self._intf_has_ip():
                self._launch_tcp_tester()
            else:
                self._stop_tcp_tester()
            time.sleep(self._p_interval)

class Initiator(object):

    def __init__(self, conf_file, data_dir, bin_dir, p_interval):
        self._conf_file = conf_file
        self._data_dir = data_dir
        self._bin_dir = bin_dir
        self._load_conf(self._conf_file)
        self._intf_polling = []
        self._p_interval = p_interval

    def _load_conf(self, conf_file):
        with open(conf_file, "r") as f:
            conf = json.load(f)
            self._ifaces = conf["ifaces"]
            self._tcp_args = conf["tcp_args"]
            logging.info("[Initiator]: loading configuration file finished")

    def _sig_handler(self, sig, frm):
        #logging.info("[Initiator]: received singal {}. Process will stop soon.".format(sig))
        #Don't need to send SIGTERM.
        #for inst in self._intf_polling:
        #    inst.terminate()
        pass

    def start(self):
        signal.signal(signal.SIGINT, self._sig_handler)
        signal.signal(signal.SIGTERM, self._sig_handler)
        for intf in self._ifaces:
            polling = _IntfPolling(intf, self._tcp_args, self._data_dir, self._bin_dir, self._p_interval)
            self._intf_polling.append(polling)
            polling.start()
        logging.info("[Initiator]: all polling processes are started")
        for inst in self._intf_polling:
            inst.join()
        logging.info("[Initiator]: all polling processes are stopped")

if __name__ == "__main__":
    initor = Initiator(args.config, args.data_dir, args.bin_dir, args.interval)
    initor.start()
