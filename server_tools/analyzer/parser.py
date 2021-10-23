#!/usr/bin/env python3
import re
import os
import argparse
import json
import signal
import time
import math
import geopy
import geopy.distance
import numpy as np
import functools
from geopy.distance import distance as geo_distance
from datetime import datetime
from multiprocessing import Pool
from lib.logger import logger
from lib.gps import GPSParser
from lib.wpa_supplicant import WPAParser
from lib.roamingd import RMParser
from lib.tcpparser import TCPParser
from lib.scan_parser import ScanParser
from lib.link_parser import LinkParser
from lib.wpa_scan_parser import WPAScanParser
from lib.db_op import DBOperator, GPS, Experiment, APTCPInfo, ScanAP, Link, CarFiScanAP

parser = argparse.ArgumentParser()
parser.add_argument("-c", "--config", required=True, help="configuration file")
parser.add_argument("--tar_dir", required=True, help="the folder that contains tarballs which aren't analyzed yet")
parser.add_argument("--archive_dir", required=True, help="the folder that contains tarballs which are already analyzed")
parser.add_argument("--cpu", default=15, type=int, help="parallel degree")
parser.add_argument("--periodical", type=int, help="the time gap between two parsings (in sec). If it is not provided, it means oneshot mode (by default).")
args = parser.parse_args()

def _uncompress_func(args):
    _data_dir, exp_name = args
    exp_dir = os.path.join(_data_dir, exp_name)
    tarball = os.path.join(_data_dir, exp_name+".tar.gz")
    os.mkdir(exp_dir)
    os.system("tar -zxf {} -C {}".format(tarball, exp_dir))
    sub_dir = os.path.join(exp_dir, os.listdir(exp_dir)[0])
    os.system("mv {} {}".format(os.path.join(sub_dir, "*"), exp_dir))
    os.system("rm -rf {}".format(sub_dir))

class _DBInfo(object):

    def __init__(self, intfs, scan_ssid, db_user, db_psw, db_addr, db_port, db_name):
        self.intfs = intfs
        self.scan_ssid = scan_ssid
        self.db = DBOperator(db_user, db_psw, db_addr, db_port, db_name)

class Parser(object):

    def __init__(self, conf, data_dir, archive_dir, cpu):
        config = None
        with open(conf, "r") as f:
            config = json.load(f)
        assert config
        assert os.path.isdir(data_dir)
        assert os.path.isdir(archive_dir)
        self._data_dir = data_dir
        self._archive_dir = archive_dir
        self._cpu = cpu
        self._dbinfo = {}
        for loc, conf_item in config.items():
            intfs = conf_item["interfaces"]
            scan_ssid = conf_item["scan_ssid"]
            db_user = conf_item["db_info"]["user"]
            db_psw = conf_item["db_info"]["passwd"]
            db_addr = conf_item["db_info"]["host"]
            db_port = conf_item["db_info"]["port"]
            db_name = conf_item["db_info"]["name"]
            self._dbinfo[loc] = _DBInfo(intfs, scan_ssid, db_user, db_psw, db_addr, db_port, db_name)
            if not os.path.isdir(os.path.join(archive_dir, loc)):
                os.mkdir(os.path.join(archive_dir, loc))

    def _update_exp_list(self):
        self._exp_list = []
        for d in os.listdir(self._data_dir):
            if d.endswith(".tar.gz"):
                self._exp_list.append(d[:-7])
            else:
                #make sure that there are no undeleted dirs from last parsing
                os.system("rm -rf {}".format(os.path.join(self._data_dir, d)))

    def _uncompress(self):
        logger.info("[Parser] uncompress tarballs from {}".format(self._data_dir))
        mp = Pool(self._cpu)
        mp.map(_uncompress_func, zip([self._data_dir]*len(self._exp_list), self._exp_list), 1)
        mp.close()
        mp.join()

    #never use it if you are not me
    def _parse_wpa_scan(self, exp):
        loc_marker, exp_start_time, exp_end_time = exp.split("-")
        #Get dbinfo
        dbinfo = self._dbinfo[loc_marker]

        exp_dir = os.path.join(self._data_dir, exp)
        tarball = exp_dir + ".tar.gz"
        session = dbinfo.db.get_session()
        wpa_log = os.path.join(exp_dir, "wpa_supplicant.log")

        wpa_scan_dict = WPAScanParser(wpa_log, dbinfo.intfs).parse()
        carfi_scan_infos = []
        for intf in dbinfo.intfs:
            for scan_obj in wpa_scan_dict[intf]:
                carfi_scan_infos.append(CarFiScanAP(time=scan_obj.time, ssid=scan_obj.ssid, bssid=scan_obj.mac, freq=scan_obj.freq, signal=scan_obj.level, interface=scan_obj.intf, wifi_version=scan_obj.wifi_type))

        os.system("rm -rf {}".format(exp_dir))
        #Push into database
        dbinfo.db.save([], [], [], [], [], carfi_scan_infos)
        #archive analyzed tarball
        os.system("mv {} {}".format(tarball, os.path.join(self._archive_dir, loc_marker)))

    def _parse_exp(self, exp):
        loc_marker, exp_start_time, exp_end_time = exp.split("-")
        #Get dbinfo
        dbinfo = self._dbinfo[loc_marker]

        #Get Experiment info
        exp_start_time = datetime.strptime(exp_start_time, "%Y_%m_%d_%Hh%Mm%Ss%z").timestamp()
        exp_end_time = datetime.strptime(exp_end_time, "%Y_%m_%d_%Hh%Mm%Ss%z").timestamp()
        exp_infos = [Experiment(start_time=exp_start_time, end_time=exp_end_time)]

        exp_dir = os.path.join(self._data_dir, exp)
        tarball = exp_dir + ".tar.gz"

        #DO NOT store data into DB if the experiment already exists in DB
        session = dbinfo.db.get_session()
        is_exp_existed = session.query(Experiment).filter(Experiment.start_time == exp_start_time, Experiment.end_time == exp_end_time).count()
        if is_exp_existed > 0:
            logger.info("duplicated experiment {}".format(exp))
            os.system("rm -rf {}".format(exp_dir))
            os.system("mv {} {}".format(tarball, os.path.join(self._archive_dir, loc_marker)))
            return

        gps_log = os.path.join(exp_dir, "gps.log")
        wpa_log = os.path.join(exp_dir, "wpa_supplicant.log")
        roamingd_log = os.path.join(exp_dir, "roamingd.log")
        tester_data_dir = os.path.join(exp_dir, "tester.data")
        scan_log_dir = os.path.join(exp_dir, "scanner.log")
        link_log = os.path.join(exp_dir, "linkmon.log")

        #Call Scan Parser
        scan_infos = []
        #only processing when there is a scan_log_dir
        if os.path.exists(scan_log_dir):
            scan_ap_list = ScanParser(scan_log_dir, dbinfo.scan_ssid).parse()
            scan_infos = [ScanAP(time=x.time, ssid=x.ssid, channel=x.channel, freq=x.freq, bssid=x.bssid, rates=x.rates, e_rates=x.e_rates, signal=x.signal, wifi_version=x.wifi_version) for x in scan_ap_list]
            del scan_ap_list

        link_infos = {intf:[] for intf in dbinfo.intfs}
        if os.path.exists(link_log):
            link_infos = LinkParser(link_log, dbinfo.intfs).parse()

        #Call GPS Parser
        gps_coords = GPSParser(gps_log).parse()
        gps_infos = [GPS(latitude=coord.latitude, longitude=coord.longitude, elevation=coord.elevation, time=coord.utc_ts) for coord in gps_coords]
        #release memory
        del gps_coords

        wpa_scan_infos = WPAScanParser(wpa_log, dbinfo.intfs).parse()
        #Call WPA Parser
        l2_infos = WPAParser(wpa_log, dbinfo.intfs).parse()
        #Call Roamingd Parser
        l3_infos = RMParser(roamingd_log, dbinfo.intfs).parse()
        #Call TCP Parser
        tcp_infos = TCPParser(tester_data_dir, dbinfo.intfs, self._cpu).parse()

        ap_tcp_infos = []
        #Link all data
        #all lists here are already ordered by time
        for intf in dbinfo.intfs:
            l3_idx, tcp_idx = 0, 0
            gps_idx = 0
            link_idx = 0
            for l2_info in l2_infos[intf]:
                ap_tcp_info = APTCPInfo(interface=intf, l2_essid=l2_info.essid, l2_bssid=l2_info.bssid, l2_freq=l2_info.freq, l2_signal_lv=l2_info.level, l2_assoc_type=l2_info.type, l2_auth_t_s=l2_info.T_auth_s, l2_auth_t_e=l2_info.T_auth_e, l2_assoc_t_s=l2_info.T_assoc_s, l2_assoc_t_e=l2_info.T_assoc_e, l2_hs_t_s=l2_info.T_hs_s, l2_hs_t_e=l2_info.T_hs_e, l2_conn_t_s=l2_info.T_conn_s, l2_conn_t_e=l2_info.T_conn_e)
                ap_tcp_infos.append(ap_tcp_info)

                #skip incomplete associations
                if ap_tcp_info.l2_conn_t_e == None:
                    continue

                #calculate average and standard error of SS
                link_signals = []
                while link_idx < len(link_infos[intf]) and link_infos[intf][link_idx].time < ap_tcp_info.l2_conn_t_s:
                    link_idx += 1
                while link_idx < len(link_infos[intf]) and link_infos[intf][link_idx].time <= ap_tcp_info.l2_conn_t_e:
                    link_signals.append(link_infos[intf][link_idx].signal)
                    link_idx += 1
                if len(link_signals) > 0:
                    avg_signal = np.average(link_signals)
                    stderr_signal = np.std(link_signals)
                    ap_tcp_info.l2_avg_signal = avg_signal.item()
                    ap_tcp_info.l2_stderr_signal = stderr_signal.item()

                #calculate the average driving speed for each AP
                gps_distance = None
                gps_pts = 0
                while gps_idx < len(gps_infos) and gps_infos[gps_idx].time < ap_tcp_info.l2_conn_t_s:
                    gps_idx += 1
                while gps_idx < len(gps_infos) and gps_infos[gps_idx].time <= ap_tcp_info.l2_conn_t_e:
                    gps_pts += 1
                    if gps_pts == 2:
                        gps_distance = 0
                    if gps_pts >= 2:
                        gps_distance += geo_distance((gps_infos[gps_idx].latitude, gps_infos[gps_idx].longitude), (gps_infos[gps_idx-1].latitude, gps_infos[gps_idx-1].longitude)).km
                    gps_idx += 1
                if gps_distance == None:
                    logger.info("AP without any associated GPS points appeared.")
                else:
                    ap_tcp_info.avg_speed = gps_distance / ((ap_tcp_info.l2_conn_t_e - ap_tcp_info.l2_conn_t_s) / 3600)
                    ap_tcp_info.dist_km = gps_distance

                #skip l3_infos without any possible associated l2_info
                while l3_idx < len(l3_infos[intf]) and l3_infos[intf][l3_idx].T_dhcp_s < l2_info.T_conn_s:
                    l3_idx += 1
                if l3_idx < len(l3_infos[intf]) and (l3_infos[intf][l3_idx].T_dhcp_s <= l2_info.T_conn_e):
                    #find the right one to associate with
                    ap_tcp_info.l3_dhcp_t_s = l3_infos[intf][l3_idx].T_dhcp_s
                    ap_tcp_info.l3_dhcp_t_e = l3_infos[intf][l3_idx].T_dhcp_e
                    ap_tcp_info.l3_ip_t_s = l3_infos[intf][l3_idx].T_ip_s
                    ap_tcp_info.l3_ip_t_e = l3_infos[intf][l3_idx].T_ip_e
                    ap_tcp_info.l3_ip = l3_infos[intf][l3_idx].ip
                    ap_tcp_info.l3_ip_prefix = l3_infos[intf][l3_idx].ip_prefix
                    ap_tcp_info.l3_gw = l3_infos[intf][l3_idx].gw
                    ap_tcp_info.l3_dhcp_server = l3_infos[intf][l3_idx].dhcp_server
                    ap_tcp_info.l3_dns_servers = l3_infos[intf][l3_idx].dns_servers
                    l3_idx += 1

                while tcp_idx < len(tcp_infos[intf]) and tcp_infos[intf][tcp_idx].T_s_app < l2_info.T_conn_s:
                    tcp_idx += 1
                if tcp_idx < len(tcp_infos[intf]) and (tcp_infos[intf][tcp_idx].T_s_app <= l2_info.T_conn_e):
                    ap_tcp_info.tcp_t_s = tcp_infos[intf][tcp_idx].T_s_app
                    ap_tcp_info.tcp_t_e = tcp_infos[intf][tcp_idx].T_e_app
                    ap_tcp_info.tcp_t_s_pcap = tcp_infos[intf][tcp_idx].T_s_pcap
                    ap_tcp_info.tcp_t_e_pcap = tcp_infos[intf][tcp_idx].T_e_pcap
                    ap_tcp_info.tcp_direction = tcp_infos[intf][tcp_idx].type
                    ap_tcp_info.tcp_cc = tcp_infos[intf][tcp_idx].cc
                    ap_tcp_info.tcp_flow_nb = tcp_infos[intf][tcp_idx].flow_nb
                    ap_tcp_info.tcp_flows = tcp_infos[intf][tcp_idx].flows
                    ap_tcp_info.tcp_total_bytes_app = tcp_infos[intf][tcp_idx].total_bytes_app
                    ap_tcp_info.tcp_total_bytes_pcap = tcp_infos[intf][tcp_idx].total_bytes_pcap
                    ap_tcp_info.tcp_goodput_app = tcp_infos[intf][tcp_idx].gp_app
                    ap_tcp_info.tcp_goodput_pcap = tcp_infos[intf][tcp_idx].gp_pcap
                    ap_tcp_info.tcp_test_local_id = tcp_infos[intf][tcp_idx].local_id
                    ap_tcp_info.tcp_total_pkts = tcp_infos[intf][tcp_idx].pkt_total
                    ap_tcp_info.tcp_rxmt_pkts = tcp_infos[intf][tcp_idx].pkt_rxmt
                    ap_tcp_info.tcp_loss_rate = tcp_infos[intf][tcp_idx].pkt_loss_rate
                    tcp_idx += 1

        del l2_infos
        del l3_infos
        del tcp_infos
        os.system("rm -rf {}".format(exp_dir))

        link_list = functools.reduce(lambda x,y: x+y, [v for v in link_infos.values()])
        link_infos = [Link(time=x.time, signal=x.signal, interface=x.intf) for x in link_list]
        #Push into database
        dbinfo.db.save(exp_infos, gps_infos, ap_tcp_infos, scan_infos, link_infos)
        #archive analyzed tarball
        os.system("mv {} {}".format(tarball, os.path.join(self._archive_dir, loc_marker)))

    def _parse_wpa_scan_only(self):
        for exp in self._exp_list:
            self._parse_wpa_scan(exp)

    def _parse_all(self):
        for exp in self._exp_list:
            self._parse_exp(exp)

    def parse(self):
        self._update_exp_list()
        self._uncompress()
        self._parse_all()
        #self._parse_wpa_scan_only()

def sig_handler(sig, frm):
    exit(0)

def oneshot_parsing():
    data_parser = Parser(args.config, args.tar_dir, args.archive_dir, args.cpu)
    data_parser.parse()

def periodical_parsing():
    data_parser = Parser(args.config, args.tar_dir, args.archive_dir, args.cpu)
    while True:
        data_parser.parse()
        time.sleep(args.periodical)

def main():
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)

    if not os.path.isdir(args.tar_dir):
        os.system("mkdir -p {}".format(args.tar_dir))

    if not os.path.isdir(args.archive_dir):
        os.system("mkdir -p {}".format(args.archive_dir))

    if args.periodical:
        periodical_parsing()
    else:
        oneshot_parsing()

if __name__ == "__main__":
    main()
